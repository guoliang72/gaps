from pymongo import MongoClient
from gaps.config import Config
from gaps.utils import cvt_to_milisecs
import datetime
import os
import json
import time
import sys

class MongoWrapper(object):
	def __init__(self):
		self.client =  MongoClient(Config.mongodb_ip, Config.mongodb_port)
		self.db = self.client.CrowdJigsaw
		# authentication
		if Config.authentication:
			self.db.authenticate(Config.username, Config.password)
		self.winner_time = 0
		self.shapeArray = None

	def edges_documents(self):
		return self.db['rounds'].find_one({'round_id': Config.round_id})['edges_saved']

	def shapes_documents(self):
		if not self.shapeArray:
			self.shapeArray = json.loads(self.db['rounds'].find_one({'round_id': Config.round_id})['shapeArray'])
		return self.shapeArray

	def cogs_documents(self, timestamp):
		""" get actions documents in-between start_time and end_time """
		return self.db['cogs'].find({'round_id': Config.round_id, \
											'time':{'$gt':0, '$lte':timestamp}})

	def get_round_start_milisecs(self):
		formatted_date = self.db['rounds'].find_one({'round_id': Config.round_id})['start_time']
		return cvt_to_milisecs(formatted_date)

	def get_round_winner_time_milisecs(self):
		if Config.cli_args.online:
			return 0
		if self.winner_time > 0:
			return self.winner_time
		formatted_date = self.db['rounds'].find_one({'round_id': Config.round_id})['winner_time']
		hour, minute, second = formatted_date.split(':')
		self.winner_time = (int(hour) * 3600 + int(minute) * 60 + int(second)) * 1000
		return self.winner_time

	def is_finished(self):
		if self.db.rounds.find_one({'round_id': Config.round_id})['end_time'] == '-1':
			return False
		else:
			return True
	
	def __del__(self):
		self.client.close()

# singleton
mongo_wrapper = MongoWrapper()

class JsonDB(object):
	DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),\
		                  './JsonDB')
	def __init__(self, collection_name, doc_name):
		self.collection_path = os.path.join(JsonDB.DB_DIR, collection_name)
		if not os.path.exists(self.collection_path):
			os.mkdir(self.collection_path)
		self.doc_path = os.path.join(self.collection_path, doc_name+'.json')
		self.json_data = []
		# if the file already exists, add a prefix.
		if os.path.exists(self.doc_path):
			for i in range(1, sys.maxsize):
				self.doc_path = os.path.join(self.collection_path, doc_name+'_'+str(i)+'.json')
				if not os.path.exists(self.doc_path):
					break
		# create a new file.
		with open(self.doc_path, 'w') as f:
			pass

	def add(self, v):
		v['added_time'] = time.time()
		self.json_data.append(v)
		if len(self.json_data) % 50 == 0:
			self.save()

	def save(self):
		with open(self.doc_path, 'w') as f:
			json.dump(self.json_data, f)

	def add_solution_info(self):
		for item in self.json_data:
			if item['is_solution']:
				solution_found = True
				timespent = item['added_time'] - item['start_time']
				timespent = str(datetime.timedelta(seconds=timespent))
				break
		else:
			item = self.json_data[-1]
			timespent = item['added_time'] - item['start_time']
			timespent = str(datetime.timedelta(seconds=timespent))
			solution_found = False
		self.json_data.append({'solution_found':solution_found, 'timespent':timespent})

	def __del__(self):
		self.add_solution_info()
		self.save()

