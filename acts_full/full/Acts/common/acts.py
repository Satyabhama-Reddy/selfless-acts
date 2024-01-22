from flask import Flask, jsonify, request
import requests
from flask_restful import Resource, Api, abort
import datetime
import base64
import json
import os

#global variables for total requests to acts and crashing the container
count=0
fail = 0

#api to cath all the 404 errors for handeling
class CustomApi(Api):
	def handle_error(self, e):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			global count
			if(e.code==405):
				#print(request.headers)
				#print("Here") #put global here
				count += 1
			if(e.code==404):
				#print(request.headers)
				count += 1
			abort(e.code, str(e))

app = Flask(__name__)
api = CustomApi(app,catch_all_404s=True)
#api = Api(app)

#Utility functions:

#Used to validate the format of date uploaded in the act
def validate(date_text):
	try:
		datetime.datetime.strptime(date_text, '%d-%m-%Y:%S-%M-%H')
		return True
	except:
		return False

#check the format of the text or the caption
def checkbase(text):
	try:
		if(type(text)==type("blah")):
			text=bytes(text,'utf-8')
		if base64.b64encode(base64.b64decode(text))==text:
			return True
		else:
			return False
	except:
		#print("why am i here")
		return  (False)

# saving the data in the database
def saveimage(actid, text):
	with open("/.common/images/"+str(actid)+".jpg", "wb") as fh:
		fh.write(base64.b64decode(text))

def getimage(actid):
	with open("./common/images/"+str(actid)+".jpg", "rb") as fh:
		return base64.b64encode(fh.read())

def delimage(actid):
	if os.path.exists("./common/images/"+actid+".jpg"):
		os.remove("./common/images/"+actid+".jpg")

#importing the data from the database
Images = json.load(open('./common/images.json','r'))
Categories = json.load(open('./common/categories.json','r'))

#open
def openDictionary():
	global Images
	global Categories
	Images = json.load(open('./common/images.json','r'))
	Categories = json.load(open('./common/categories.json','r'))

#save
def saveDictionary():
	json.dump(Images, open('./common/images.json','w'))
	json.dump(Categories, open('./common/categories.json','w'))

#cehck if user exists
def checkuser(username):
	resp = requests.get('http://3.213.248.108:80/api/v1/users',headers={"Origin":"52.70.253.166","Content-Type":"application/json"})
	if resp.status_code==204:
		return False
	users = resp.json()
	if username in users:
		return True
	return False

class getCategories(Resource):
	#get all the categories present in the dataset
	def get(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			exact_cat = {}
			for a in Categories.keys():
				exact_cat[a] = len(Categories[a])
			response = jsonify(exact_cat)
			response.status_code = 200

			if len(exact_cat.keys())==0:
				response.status_code = 204

			return response

	#add new category to the dataset
	def post(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			response = jsonify({})
			try:			
				new_cat = request.get_json()[0]
				if len(request.get_json())!=1:
					response.status_code = 400
					return response
			except:
				response.status_code = 400
				return response
			
			if new_cat in Categories.keys():
				response.status_code = 400
				return response

			Categories[new_cat] = []
			saveDictionary()

			response.status_code = 201
			return response

api.add_resource(getCategories, "/api/v1/categories")



class getCategories2(Resource):
	#delete the category from the dataset
	def delete(self, category):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			response = jsonify({})

			#Check if it exists
			if category not in Categories.keys():
				response.status_code = 400
				return response

			for a in Categories[category]:
				Images.pop(str(a), None)
				delimage(str(a))
			Categories.pop(category, None)
			saveDictionary()
			response.status_code = 200

			return response
api.add_resource(getCategories2,"/api/v1/categories/<string:category>")


class getActs(Resource):
	#get all the acts in thr specified category
	def get(self, category):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			acts = []

			if len(request.args)!=0:
				try:
					if(category not in Categories.keys()):
						response = jsonify(acts)
						response.status_code = 400
						return response
					if int(request.args['start'])<1 or int(request.args['end'])>len(Categories[category]):
						response = jsonify(acts)
						response.status_code = 400
						return response
		
					if int(request.args['end'])-int(request.args['start'])+1>100:
						response = jsonify(acts)
						response.status_code = 413
						return response

					else:
						#for a in range(int(request.args["start"]), int(request.args["end"])+1):
						for a in Categories[category]:
							resp = {}
							resp['actId'] = int(a)
							resp['username'] = Images[str(a)][0]
							resp['timestamp'] = Images[str(a)][1]
							resp['caption'] = Images[str(a)][2]
							resp['upvotes'] = int(Images[str(a)][3])
							resp['imgB64'] = str(getimage(str(a)), 'utf-8')
							acts.append(resp)
						newlist = sorted(acts, key=lambda k: (datetime.datetime.strptime(k['timestamp'], '%d-%m-%Y:%S-%M-%H'),int(k['actId'])),reverse=True) 
						#print(newlist)
						newlist=newlist[int(request.args['start'])-1:int(request.args['end'])]
						response = jsonify(newlist)
						response.status_code = 200
						return response
				except:
					response = jsonify(acts)
					response.status_code = 400
					return response


			if(category not in Categories.keys()):
				response = jsonify(acts)
				response.status_code = 400
				return response

			if(len(Categories[category])>=100):
				response = jsonify(acts)
				response.status_code = 413
				return response

			if(len(Categories[category])==0):
				response = jsonify(acts)
				response.status_code = 204
				return response

			for a in Categories[category]:
				resp = {}
				resp['actId'] = int(a)
				resp['username'] = Images[str(a)][0]
				resp['timestamp'] = Images[str(a)][1]
				resp['caption'] = Images[str(a)][2]
				resp['upvotes'] = int(Images[str(a)][3])
				resp['imgB64'] = str(getimage(str(a)), 'utf-8')
				acts.append(resp)
			newlist = sorted(acts, key=lambda k: (datetime.datetime.strptime(k['timestamp'], '%d-%m-%Y:%S-%M-%H'),int(k['actId'])),reverse=True)
			response = jsonify(newlist)
			response.status_code = 200
			return response

api.add_resource(getActs,"/api/v1/categories/<string:category>/acts")



class upvote(Resource):
	#upvote the particular act
	def post(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			response = jsonify([])
			try:
		
				actid = str(request.get_json()[0])
		
				if actid not in Images.keys():
					response.status_code = 400
					return response
		
				Images[actid][-1]+=1
				saveDictionary()
				response.status_code = 200
				return response
			except:
				response.status_code = 400
				return response

api.add_resource(upvote, "/api/v1/acts/upvote")


class getNum(Resource):
	#get the totsl numver of acts in the specified category
	def get(self, categoryName):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			flag = 0
			num = []
			
			for key in Categories.keys():
				if(key==categoryName):
					flag=1
					num.append(len(Categories[key]))

			response = jsonify(num)
			#Checking for existance
			if(flag==0):
				response.status_code = 405

			#204 no content?
			elif(num[0] == 0):
				response.status_code = 204

			else:
				response.status_code = 200
			return response

api.add_resource(getNum, "/api/v1/categories/<string:categoryName>/acts/size")


class changeAct(Resource):	
	#change act name
	def post(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			response = jsonify({})
			try:
				params = request.get_json()
				#print(params)
				cu=checkuser(params["username"])
				if len(params.keys())!=6:
					print("Params Wrong")
					response.status_code = 400
					return response
		
				if str(params["actId"]) in Images.keys():
					print("Act format incorrect")
					response.status_code = 400
					return response
				if str(params["actId"]).isnumeric()==False:
					print("Act format incorrect")
					response.status_code = 400
					return response
		
				if validate(params["timestamp"])==False:
					print("Time format incorrect")
					response.status_code = 400
					return response

				if cu==False:
					print("Username format incorrect")
					response.status_code = 400
					return response
				
				if checkbase(params["imgB64"])==False:
					print("Image format incorrect")
					response.status_code = 400
					return response
					
				if params["categoryName"] not in Categories.keys():
					print("Category format incorrect")
					response.status_code = 400
					return response
		
				saveimage(params["actId"], params["imgB64"])
				Images[str(params["actId"])] = [params["username"], params["timestamp"], params["caption"], 0]
				Categories[params["categoryName"]].append(int(params["actId"]))
				saveDictionary()
				print(str(params["actId"]),(str(params["actId"]) in Images.keys()))
				response.status_code = 201
				return response
			except Exception as e:
				response.status_code = 400
				return response


api.add_resource(changeAct, "/api/v1/acts")

class changeAct2(Resource):
	#delete act from category
	def delete(self, actID):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			response = jsonify({})
			
			if str(actID)=='upvote':
				response.status_code = 405
				return response

			if str(actID) not in Images.keys():
				print(actID,type(actID),(str(actID) in Images.keys()))
				response.status_code = 400
				return response

			Images.pop(actID)
			saveDictionary()
			delimage(actID)
			for a in Categories.keys():
				for b in Categories[a]:
					if b==int(actID):
						Categories[a].remove(b)
						saveDictionary()
						response.status_code = 200
						return response

			response.status_code = 200
			return response

api.add_resource(changeAct2, "/api/v1/acts/<string:actID>")


class countRequests(Resource):
	#count the total number of requests made
	def get(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			num = []
			num.append(count)
			response = jsonify(num)
			response.status_code = 200
			return response

	#reset the counter
	def delete(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count = 0
			response = jsonify({})
			response.status_code = 200
			return response

	#not defined
	def post(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			response = jsonify({})
			response.status_code = 405
			return response


api.add_resource(countRequests, "/api/v1/_count")

class countActs(Resource):
	#increment the counter and resturn the total number of requests made to the cat container
	def get(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			openDictionary()
			global count
			count += 1
			resp = []
			totalActs=len(Images)
			resp.append(totalActs)
			response = jsonify(resp)
			response.status_code = 200
			return response

api.add_resource(countActs, "/api/v1/acts/count")

class hc(Resource):
	#health check api
	def get(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			response = jsonify({})
			response.status_code = 200
			return response
api.add_resource(hc, "/healthcheck")

class new_hc(Resource):
	#new health check api, returns 200 if api container works properly
	def get(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		else:
			response = jsonify({})
			response.status_code = 200
			return response

api.add_resource(new_hc, "/api/v1/_health")

class crash(Resource):
	#crashes the container, so that all the requests return 500
	def post(self):
		global fail
		if fail:
			response = jsonify({})
			response.status_code = 500
			return response
		fail = 1
		response = jsonify({})
		response.status_code = 200
		return response

api.add_resource(crash, "/api/v1/_crash")


if __name__ == '__main__':
	app.run(host="0.0.0.0", debug=True)
