from pymongo import MongoClient
from gaps.config import Config

class MongoWrapper(object):
	def __init__(self):
		self.client =  MongoClient("localhost", 27017)
		self.db = self.client.CrowdJigsaw

	def nodes_documents(self):
		yield from self.db['nodes'].find({'round_id': Config.round_id})

	def write_elites(self, *args):
		for v in args:
			self.db.ga.insert_one(v)

	def write_solution(self, solution_doc, start_time, end_time):
		solution_doc['start_time'] = start_time
		solution_doc['end_time'] = end_time
		solution_doc['used_time'] = end_time - start_time
		self.db.ga.insert_one(solution_doc)

	def is_finished(self):
		if self.db.rounds.find_one({'round_id': Config.round_id})['end_time'] == '-1':
			return False
		else:
			return True

# singleton
mongo_wrapper = MongoWrapper()