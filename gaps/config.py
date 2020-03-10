import math

class ConfigClass:

	# round_id is set by command line arguments.
	timestamp = None

	round_id = 458

	search_depth = 30000

	population = 400
	crowd_population = 25

	elite_percentage = 0.02

	elite_size = int(population * elite_percentage)

	generations = 10000000

	multiprocess = True

	# whether we use pixel informtion
	only_pixel = False
	use_pixel = True
	use_pixel_shred = 0
	 # num of created edge / (n-1)m + n(m-1)

	measure_weight = False

	shape_dissimilarity = 10000

	# roulette_alt = False: select one individual in each round of roulette.
	# roulette_alt = True: select two individuals(parents) in each round of roulette.
	roulette_alt = True

	data_server = "localhost"
	domain = "localhost"
	mongodb_port = 27017
	mongodb_database = "CrowdJigsaw"
	redis_port = 6379
	redis_auth="CISE:1726"
	redis_db=0

	# mongodb authentication.
	authentication = True
	username = "CISE" # change it to your username.
	password = "CISE:1726" # change it to your password.

	# command line arguments. This is set by ./bin/gaps.
	cli_args = None

	# number of processes for multiprocessing on crossover operation.
	process_num = 8

	_total_edges = None

	erase_edge = 2

	offline_start_percent = 0.0

	@property
	def total_edges(self):
		if self._total_edges is None:
			rows, cols = self.cli_args.rows, self.cli_args.cols
			self._total_edges = 2*rows*cols - rows - cols
		return self._total_edges
	
	_total_tiles = None

	@property
	def total_tiles(self):
		if self._total_tiles is None:
			rows, cols = self.cli_args.rows, self.cli_args.cols
			self._total_tiles = rows * cols
		return self._total_tiles

	# fitness function alternatives.
	# x = \sum{sup_num - opp_num}
	'''
	def get_sigmoid_func():
		roundinfo = mongo_wrapper.db.rounds.find_one({'round_id': Config.round_id})
		tile_num = roundinfo['tile_num']
		palyer_num = len(roundinfo['players'])
		k = tile_num * palyer_num / 2.0
		print(k)
		def sigmoid(x):
			return 1.0 / (1.0 + math.exp(-x/k))

		return sigmoid
	'''
	def sigmoid(x):
		if(-x > 100000):
			return 0.000000000000000000000000000001
		return 1.0 / (1.0 + math.exp(-x / 150.0))

	base = 1.1 
	def exponent(x):
		return 1.1 ** x

	_fitness_func_name = None
	_fitness_func = None

	rank_based_MAX = 1.9

	@property
	def fitness_func(self):
		if self._fitness_func is None:
			self._fitness_func = {
				'sigmoid': ConfigClass.sigmoid,
				'exponent': ConfigClass.exponent,
				'rank-based': None, # the implmentation of this fitness function is in GeneticAlgorithm
			}[self.fitness_func_name]
		return self._fitness_func

	@property
	def fitness_func_name(self):
		if self._fitness_func_name is None:
			self._fitness_func_name = self.cli_args.fitness
		return self._fitness_func_name

	def get_rank_fitness(self, r, total):
		return 2.0 - self.rank_based_MAX + 2.0 * (self.rank_based_MAX - 1.0) * r / (total - 1)

	'''
	def adjacent_fitness(self, x):
		return 3.0 ** x
	'''

Config = ConfigClass()




