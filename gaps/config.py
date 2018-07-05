import math

class ConfigClass:

	# round_id is set by command line arguments.
	round_id = None

	population = 200

	elite_percentage = 0.02

	elite_size = int(population * elite_percentage)

	generations = 10000000

	multiprocess = False

	# whether we use pixel informtion
	use_pixel = True
	use_pixel_shred = 0.2
	 # num of created edge / (n-1)m + n(m-1)

	# roulette_alt = False: select one individual in each round of roulette.
	# roulette_alt = True: select two individuals(parents) in each round of roulette.
	roulette_alt = True

	mongodb_ip = "162.105.89.130"
	mongodb_port = 27017

	# mongodb authentication.
	authentication = False
	# username = "username" # change it to your username.
	# password = "password" # change it to your password.

	# command line arguments. This is set by ./bin/gaps.
	cli_args = None

	# number of processes for multiprocessing on crossover operation.
	process_num = 4

	_total_edges = None

	erase_edge = 2

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
		return 1.0 / (1.0 + math.exp(-x/150.0))

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




