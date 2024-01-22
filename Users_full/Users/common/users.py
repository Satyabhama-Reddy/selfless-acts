from flask import Flask, jsonify, request
from flask_restful import Resource, Api,abort
import datetime
import base64
import json
import os

count = 0
with open("/common/count.txt","r") as f:
	count=int(f.read())

class CustomApi(Api):
	def handle_error(self, e):
		global count
		if(e.code==405):
			#print(request.headers)
			#print("Here") #put global here
			count += 1
			savecount(count)
		if(e.code==404):
			#print(request.headers)
			count += 1
			savecount(count)
		abort(e.code, str(e))

app = Flask(__name__)
api = CustomApi(app,catch_all_404s=True)
#api = Api(app)


Users = json.load(open('/common/users.json','r'))

def saveDictionary():
	json.dump(Users, open('/common/users.json','w'))

def savecount(cnt):
	with open("/common/count.txt","w") as f:
		f.write(str(cnt))

class userAdd(Resource):
	def post(self):
		global count
		count += 1
		savecount(count)
		params = request.get_json()
		response = jsonify({})
		try:
			if len(params.keys())!=2:
				response.status_code = 400
				return response
			#Check for Validity of Username
			if params["username"] in Users.keys():
				response.status_code = 400
				return response
	
			#Check for Validity of Password
			if len(params["password"])!=40:
				response.status_code = 400
				return response
			for a in params["password"]:
				if a not in "1234567890abcdef":
					response.status_code = 400
					return response

			#Add Name
			Users[params["username"]] = [params["password"], 0]
			saveDictionary()
	
			response.status_code = 201
			return response
		except:
			response.status_code = 400
			return response

	def get(self):
		global count
		count += 1
		savecount(count)
		userlist = []
		for a in Users.keys():
			userlist.append(a)
		
		response = jsonify(userlist)
		if len(userlist)==0:
			response.status_code = 204
		else:
			response.status_code = 200
		print(response)
		return response

api.add_resource(userAdd, "/api/v1/users")


class userDelete(Resource):
	def delete(self, username):
		global count
		count += 1
		savecount(count)
		response = jsonify({})

		#Check if Username exists
		if username not in Users.keys():
			response.status_code = 400
			return response

		#Remove User
		Users.pop(username, None)

		saveDictionary()

		response.status_code = 200
		return response

api.add_resource(userDelete, "/api/v1/users/<string:username>")

class userExist(Resource):
	def get(self):
		# Input in body {"username":"..", "password":"..."}
		params = request.get_json()
		response = jsonify({})

		if params["username"] in Users.keys() and Users[params["username"]][0]==params["password"]:
			response.status_code = 200
			return response
		
		response.status_code = 400
		return response

api.add_resource(userExist, "/api/v1/userexist/")
			
class countRequests(Resource):
	def get(self):
		global count
		num = []
		num.append(count)
		response = jsonify(num)
		response.status_code = 200
		return response

	def delete(self):
		global count
		count = 0
		savecount(count)
		response = jsonify({})
		response.status_code = 200
		return response
	def post(self):
		response = jsonify({})
		response.status_code = 405
		return response

api.add_resource(countRequests, "/api/v1/_count")

class hc(Resource):
	def get(self):
		response = jsonify({})
		response.status_code = 200
		return response
api.add_resource(hc, "/healthcheck")

if __name__ == '__main__':
	app.run(host="0.0.0.0",debug=True)
