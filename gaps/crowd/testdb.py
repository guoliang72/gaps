import numpy as np
from pymongo import MongoClient
import time
import datetime
import json

round_id = 443
mongo_ip = "162.105.89.130"
mongo_port = 27017

def cvt_to_secs(formatted_date):
	tmp = formatted_date.split()
	year, month, day = map(lambda x: int(x), tmp[0].split('-'))
	hour, minute, second, ms = map(lambda x:int(x), tmp[1].split(':'))
	dt = datetime.datetime(year, month, day, hour, minute, second)
	ms = time.mktime(dt.timetuple()) * 1000 + ms
	return ms

class MongoWrapper(object):
	def __init__(self):
		self.client =  MongoClient(mongo_ip, mongo_port)
		self.db = self.client.CrowdJigsaw

	def edges_documents(self):
		return self.db['rounds'].find_one({'round_id': round_id})['edges_saved']

	def shapes_documents(self):
		return self.db['rounds'].find_one({'round_id': round_id})['shapeArray']

	def cogs_documents(self, start_timestamp, end_timestamp):
		""" get actions documents in-between start_time and end_time """
		return self.db['cogs'].find({'round_id': round_id, \
											'time':{'$gt':start_timestamp, '$lte':end_timestamp}})

	def get_round_start_secs(self):
		formatted_date = self.db['rounds'].find_one({'round_id': round_id})['start_time']
		return cvt_to_secs(formatted_date)

	def get_round_end_secs(self):
		formatted_date = self.db['rounds'].find_one({'round_id': round_id})['end_time']
		return cvt_to_secs(formatted_date)

	def is_finished(self):
		if self.db.rounds.find_one({'round_id': round_id})['end_time'] == '-1':
			return False
		else:
			return True

	def get_round_winner_time_milisecs(self):
		formatted_date = self.db['rounds'].find_one({'round_id': round_id})['winner_time']
		hour, minute, second = formatted_date.split(':')
		miliseconds = (int(hour) * 3600 + int(minute) * 60 + int(second)) * 1000
		return miliseconds
	
	def __del__(self):
		self.client.close()

# singleton
mongodb = MongoWrapper()

print(mongodb.db['rounds'].find_one({'round_id': round_id})['players_num'])
start_time = mongodb.get_round_start_secs()
print(time.time() * 1000 - start_time)

roundCOG = mongodb.db['rounds'].find_one({'round_id': round_id})['COG']
roundCOGdict = {}
for cog in roundCOG:
	roundCOGdict[cog['time']] = cog

edges = mongodb.edges_documents()
print(len(edges))
for e in edges:
    edge = edges[e]
    first_piece_id = edge['x']
    if edge['tag'] == 'L-R':
        orient = 'LR'
    else:
        orient = 'TD'
    second_piece_id = edge['y']
    wp = edge['weight']
    confidence = edge['confidence']
    if confidence > 0:
    	wn = wp / confidence - wp + 0.0
    else:
    	wn = 0.0
    	opposers = edge['opposers']
    	for o in opposers:
    		wn += opposers[o]
    measure = wn - wp
    #print(wn, wp, measure)

cogs = list(mongodb.cogs_documents(start_timestamp=0, end_timestamp=10000000))
for cog in cogs:
	edges = cog['edges_changed']
	for e in edges:
		first_piece_id, second_piece_id = int(e.split('-')[0][:-1]), int(e.split('-')[1][1:])
		if e.split('-')[0][-1] == 'L':
			orient = 'LR'
		else:
			orient = 'TD'
		key = str(first_piece_id)+orient+str(second_piece_id)
		edge = edges[e]
		measure = float(edge['wn']) - float(edge['wp'])

print(mongodb.get_round_winner_time_milisecs())

measure_dict = {}

shapes = json.loads(mongodb.shapes_documents())
for first_piece_id in range(len(shapes)):
	for second_piece_id in range(len(shapes)):
		#print(shapes[first_piece_id], shapes[second_piece_id])
		if(shapes[first_piece_id]['rightTab'] + shapes[second_piece_id]['leftTab'] != 0):
			key = str(first_piece_id) + 'LR' + str(second_piece_id)
			measure_dict[key] = 100
		if(shapes[first_piece_id]['bottomTab'] + shapes[second_piece_id]['topTab'] != 0):
			key = str(first_piece_id) + 'TD' + str(second_piece_id)
			measure_dict[key] = 100
