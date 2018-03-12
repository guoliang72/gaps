from pymongo import MongoClient
from gaps.config import Config

class MongoWrapper(object):
	def __init__(self):
		self.client =  MongoClient("localhost", 27017)

	def documents(self):
		db = self.client.CrowdJigsaw
		yield from db['nodes'].find({'round_id': Config.round_id})

	def __del__(self):
		self.client.close()