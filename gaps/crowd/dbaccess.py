from pymongo import MongoClient
from gaps.config import Config
import os
import json
import time

class MongoWrapper(object):
	def __init__(self):
		self.client =  MongoClient("localhost", 27017)
		self.db = self.client.CrowdJigsaw

	def nodes_documents(self):
		yield from self.db['nodes'].find({'round_id': Config.round_id})

	'''
	def write_elites(self, *args):
		for v in args:
			self.db.ga.insert_one(v)

	def write_solution(self, solution_doc, start_time, end_time):
		solution_doc['start_time'] = start_time
		solution_doc['end_time'] = end_time
		solution_doc['used_time'] = end_time - start_time
		self.db.ga.insert_one(solution_doc)
	'''

	def is_finished(self):
		if self.db.rounds.find_one({'round_id': Config.round_id})['end_time'] == '-1':
			return False
		else:
			return True

class JsonDB(object):
	DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),\
		                  './JsonDB')
	def __init__(self, collection_name, doc_name):
		self.collection_path = os.path.join(JsonDB.DB_DIR, collection_name)
		if not os.path.exists(self.collection_path):
			os.mkdir(self.collection_path)
		self.doc_path = os.path.join(self.collection_path, doc_name+'.json')
		self.json_data = []
		if os.path.exists(self.doc_path):
			with open(self.doc_path, 'r') as f:
				self.json_data = json.load(f)

	def add(self, v):
		v['added_time'] = time.time()
		self.json_data.append(v)

	def save(self):
		with open(self.doc_path, 'w') as f:
			json.dump(self.json_data, f)

# singleton
mongo_wrapper = MongoWrapper()
