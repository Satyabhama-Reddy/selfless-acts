from flask import Flask, jsonify, request, Response
import requests
from flask_restful import Resource, Api
import json
import os
import subprocess
import threading
from time import sleep

#orchestrator class:
class LOADBALANCER:
	def __init__(self, image,volume_at, interval=120, first_port=8000, max_containers=20, min_containers=1, threshold=20, health_check_time=1, port=6900):
		#initialization of different parameters taken from the user for generic implementation
		'''Parameters of the class:
			-image to be used to make containers
			-volume on which the container must be mounted
			-the time interval between subsequent checks on the request volume and whether a change in the number of containers must be initiated
			-value of the port number assigned to the first container. All subsequent containers are assigned consecutive port numbers
			-maximum number of containers running at any point of time
			-minimum number of containers running at any point of time
			-threshold on the maximum number of requests that one container can handle. If this threshold is crossed, a new container must be introduced.
			-the time interval between subsequent checks on the health of the running containers
			-the port number at which the orchestrator must run
		'''
		self.image = image
		self.interval = interval
		self.first_port = first_port
		self.max_containers = max_containers
		self.min_containers = min_containers
		self.threshold = threshold
		self.health_check_time = health_check_time
		self.volume_at = volume_at
		self.port = port
		

		#initialization of other utility variables
		self.current_port = -1
		#container is a dictionary: 
		#container_number => [container_port, name, number_of_current_requests, state(active/crashed)]
		self.containers = {}
		self.valid_containers = 0
		self.total_number_of_requests = 0
		self.app = Flask(__name__)
		self.max_port = self.first_port
		self.run_threads = False

		#case when the request is not meant for acts container
		@self.app.route('/', defaults={'path': ''},methods=['GET','POST','DELETE'])
		def root(*args, **kwargs):
			response = jsonify({})
			response.status_code = 200
			return response

		# case when the request is for acts container
		@self.app.route('/<path:path>',methods=['GET','POST','DELETE'])
		def proxy(*args, **kwargs):
			self.run_threads = True
			self.current_port = (self.current_port+1)%self.valid_containers
			#loop until you get an active container in the list
			while self.containers[self.current_port][3]==False:
				self.current_port = (self.current_port+1)%self.valid_containers
			#increase the numver of requests being handled by the container
			self.containers[self.current_port][2]+=1
			#if normal requests increase the total request counter
			if "_health" not in request.url and "_trash" not in request.url:
				self.total_number_of_requests+=1
			print("Container Serving Request:", self.containers[self.current_port][1])
			#call the respective api
			resp = requests.request(
					method=request.method,
					url=request.url.replace(request.host_url, 'http://127.0.0.1:'+str(self.containers[self.current_port][0])+'/'),
					headers={key: value for (key, value) in request.headers if key != 'Host'},
					data=request.get_data(),
					cookies=request.cookies,
					allow_redirects=False)
			#after the request has been catered
			self.containers[self.current_port][2]-=1
			excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
			headers = [(name, value) for (name, value) in resp.raw.headers.items()
					   if name.lower() not in excluded_headers]

			#if the request was unsuccessful
			while(resp.status_code==500):
				#disable and restart the container
				self.containers[self.current_port][3]=False
				res=threading.Thread(target=self.restart_container,args=(self.current_port,))
				res.daemon = True
				res.start()
				#and send the request to another container
				self.current_port = (self.current_port+1)%self.valid_containers
				#find a new container
				while self.containers[self.current_port][3]==False:
					self.current_port = (self.current_port+1)%self.valid_containers
				self.containers[self.current_port][2]+=1
				print("Container Serving Request:", self.containers[self.current_port][1])
				#send request to new container
				resp = requests.request(
						method=request.method,
						url=request.url.replace(request.host_url, 'http://127.0.0.1:'+str(self.containers[self.current_port][0])+'/'),
						headers={key: value for (key, value) in request.headers if key != 'Host'},
						data=request.get_data(),
						cookies=request.cookies,
						allow_redirects=False)
				self.containers[self.current_port][2]-=1
				excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
				headers = [(name, value) for (name, value) in resp.raw.headers.items()
						   if name.lower() not in excluded_headers]
			return Response(resp.content, resp.status_code, headers)

		self.set_up()

	def __enter__(self):
		while self.valid_containers!=self.min_containers:
			sleep(1)
		t2 = threading.Thread(target=self.health_check, args=())
		t2.daemon = True
		t2.start()
		t1 = threading.Thread(target=self.create_or_delete, args=())
		t1.daemon = True
		t1.start()
		self.app.run(host="0.0.0.0",port=str(self.port))

	def __exit__(self, exc_type, exc_value, exc_traceback):
		self.run_threads = False
		for a in range(self.max_port-self.first_port):
			if a not in self.containers.keys():
				continue
			subprocess.run(['docker', 'stop', self.containers[a][1]], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
			subprocess.run(['docker', 'container', "rm", "container"+str(self.containers[a][0])], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
			
		subprocess.run(['docker', 'stop', 'alpha_volume'], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
		subprocess.run(['docker', 'container', "rm", 'alpha_volume'], stdout = subprocess.DEVNULL, stderr = subprocess.DEVNULL)
	
#Utility Functions
	#utility for creation
	def create_util(self, mp):
		while True:
			result = subprocess.run(["docker", "ps", '--filter',  'NAME=container'+str(mp), "-q"], stdout = subprocess.PIPE)
			new_cont = result.stdout.decode("ascii")
			if new_cont!='':
				#updating the state of the container
				self.containers[mp-self.first_port][3] = True
				break
			sleep(1)
		self.valid_containers+=1
		#print("Created Container")
		return
	
	#creates a new container at the next available port number and names the container, container<port number>. Ex: container8000
	def create_container(self):
		self.containers[self.max_port-self.first_port] = [self.max_port, "container"+str(self.max_port), 0, False]
		#run process in the background
		subprocess.Popen(['docker', 'run', '-p', str(self.max_port)+':80','--volumes-from','alpha_volume', '--name', "container"+str(self.max_port), self.image], stdout = subprocess.DEVNULL)
		self.max_port+=1
		t1 = threading.Thread(target=self.create_util, args=(self.max_port-1, ))
		t1.daemon = True
		t1.start()

	#utility for deletion
	def del_util(self, id):
		while self.containers[id][2]!=0:
			sleep(0.05)
		subprocess.run(['docker', 'stop', self.containers[id][1]], stdout = subprocess.DEVNULL)
		subprocess.Popen(['docker', 'container', "rm", "container"+str(self.containers[id][0])], stdout = subprocess.DEVNULL)
		del self.containers[id]
		#print("Deleted Container")

	#deletes a container
	def delete_container(self):
		self.valid_containers-=1
		self.max_port-=1
		id = self.max_port-8000
		#change the state to inactive
		self.containers[id][3] = False
		t1 = threading.Thread(target=self.del_util, args=(id, ))
		t1.daemon = True
		t1.start()
	
	#create the minimum number of containers
	def set_up(self):
		self.create_volume()
		for a in range(self.min_containers):
			self.create_container()

	#for autoscaling:
	'''value  =  Number of Requests Received in Interval
			     Specified Threshold for Scaling
		If ‘value’ > current number of containers:
			Containers are created
		If ‘value’ < current number of containers:
			Containers are deleted
		If ‘value’ == current number of containers:
			No change'''
	def create_or_delete(self):
		while self.run_threads==False:
			"""
			Waste Time
			"""
		while self.run_threads==True:
			sleep(self.interval)
			must_be_running=(self.total_number_of_requests//self.threshold)+1
			if must_be_running<self.min_containers:
				must_be_running = self.min_containers
			if must_be_running>self.max_containers:
				must_be_running = self.max_containers
			
			to_cod = abs(self.valid_containers-must_be_running)
			if(self.valid_containers<must_be_running):
				#create
				while(to_cod):
					self.create_container()
					to_cod-=1
			elif(self.valid_containers>must_be_running):
				#delete
				while(to_cod):
					self.delete_container()
					to_cod-=1
			self.total_number_of_requests = 0
			
	#restart the container
	#first delete the container and then restart
	def restart_util(self, mp,flag):
		if(flag==0):
			while True:
				result = subprocess.run(["docker", "ps", '--filter',  'NAME=container'+str(mp), "-q"], stdout = subprocess.PIPE)
				new_cont = result.stdout.decode("ascii")
				if new_cont=='':
					break
			print("Deleted Container to restart")
		if(flag==1):
			while True:
				result = subprocess.run(["docker", "ps", '--filter',  'NAME=container'+str(mp), "-q"], stdout = subprocess.PIPE)
				new_cont = result.stdout.decode("ascii")
				if new_cont!='':
					self.containers[mp-self.first_port][3] = True
					break
				sleep(1)
			print("Container restarted")
		return
			
	# call restart util
	def restart_container(self,cp):
		name=self.containers[cp][1]
		port=self.containers[cp][0]
		subprocess.run(['docker', 'rm','-f',name], stdout = subprocess.DEVNULL)
		t1 = threading.Thread(target=self.restart_util, args=(port,0 ))
		t1.daemon = False
		t1.start()
		#assign appropriate attributes to the new container
		p2=subprocess.Popen(['docker', 'run', '-p', str(port)+':80','--volumes-from','alpha_volume', '--name', name, self.image], stdout = subprocess.DEVNULL)
		t2 = threading.Thread(target=self.restart_util, args=(port,1 ))
		t2.daemon = True
		t2.start()
		
	#perform health check application
	def health_check(self):
		#wait until threads are enabled
		while self.run_threads==False:
			"""
			Waste Time
			"""
		while self.run_threads==True:
			sleep(self.health_check_time)
			keys=list(self.containers.keys())
			for cp in keys:
				try:
					#call health check api for all the active containers
					if(self.containers[cp][3]==True):
						resp = requests.request(method='GET',url='http://127.0.0.1:'+str(self.containers[cp][0])+'/api/v1/_health')
						print(self.containers[cp][0])
						if(resp.status_code==500):
							self.containers[cp][3]=False
							#restart the specific container
							res=threading.Thread(target=self.restart_container,args=(cp,))
							res.daemon = True
							res.start()
				except:
					continue

	#create new volume
	def create_volume(self):
		subprocess.run(['docker', 'run', '-p', str(self.volume_at[0])+':80','-v',str(self.volume_at[1])+':'+str(self.volume_at[2]), '--name', "alpha_volume", self.image,"sh"], stdout = subprocess.DEVNULL)
		print("Volume Created")
		return


