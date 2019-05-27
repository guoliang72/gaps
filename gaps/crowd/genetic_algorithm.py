from __future__ import print_function
import time
import random
from operator import attrgetter
from gaps import image_helpers
from gaps.selection import roulette_selection
# from gaps.plot import Plot
from gaps.progress_bar import print_progress
from gaps.crowd.crossover import Crossover
from gaps.crowd.individual import Individual
from gaps.crowd.nodes import NodesAndHints
from gaps.crowd.crowd_individual import CrowdIndividual
from gaps.crowd.image_analysis import ImageAnalysis
from gaps.config import Config
from multiprocessing import Process, Queue
from gaps.crowd.fitness import db_update, dissimilarity_measure
from gaps.crowd.dbaccess import mongo_wrapper
import redis
import json
import numpy as np

redis_cli = redis.Redis(connection_pool=Config.pool)

def worker(pid, start_time, pieces, elite_size):
    def calc_rank_fitness(population):
        rank1 = 0
        while rank1 < len(population):
            fitness1 = Config.get_rank_fitness(rank1, len(population))
            indiv1 = population[rank1]
            rank2 = rank1 + 1
            for rank2 in range(rank1+1, len(population)):
                indiv2 = population[rank2]
                if abs(indiv1.objective-indiv2.objective) > 1e-6:
                    break
            fitness2 = Config.get_rank_fitness(rank2 - 1, len(population))
            for indiv in population[rank1: rank2]:
                indiv._fitness = (fitness1 + fitness2) / 2.0
            rank1 = rank2
    from gaps.crowd.fitness import db_update
    while True:
        redis_key = 'round:%d:dissimilarity' % Config.round_id
        dissimilarity_json = redis_cli.get(redis_key)
        if dissimilarity_json:
            dissimilarity_measure.measure_dict = json.loads(dissimilarity_json)
        else:
            continue
        refreshTimeStamp(start_time)
        #db_update()
        ImageAnalysis.analyze_image(pieces)
        redis_key = 'round:%d:parents' % (Config.round_id)
        parents_json = redis_cli.hget(redis_key, 'process:%d' % pid)
        parents = []
        elite = []
        if parents_json:
            parents_data = json.loads(parents_json)
            #print(pid, len(parents_data))
            if parents_data and len(parents_data) == 49:       
                parents = [(Individual([pieces[_] for _ in f], Config.cli_args.rows, Config.cli_args.cols, False), 
                    Individual([pieces[_] for _ in s], Config.cli_args.rows, Config.cli_args.cols, False))
                    for (f, s) in parents_data]
                #print('process %d get %d parents from redis' % (pid, len(parents)))
        if not parents:
            continue
        
        children = []
        for first_parent, second_parent in parents:
            crossover = Crossover(first_parent, second_parent)
            crossover.run()
            child = crossover.child()
            children.append(','.join([str(_) for _ in child.get_pieces_id_list()]))

        #print(len(children))
        #print('process %d put %d children' % (pid, len(children)))
        redis_key = 'round:%d:children' % (Config.round_id)
        children_data = json.dumps(children)
        redis_cli.hset(redis_key, 'process:%d' % pid, children_data)


def refreshTimeStamp(start_time):
    Config.timestamp = (time.time() - start_time) * 1000
    if not Config.cli_args.online:
        Config.timestamp += mongo_wrapper.get_round_winner_time_milisecs() * Config.offline_start_percent * 1.0

def compute_edges_match(individual, columns, edges):
    edges_match = 0.0
    confidence_edges_match = 0.0
    unconfidence_edges_match = 0.0
    correct_edges_match = 0.0
    confidence_edges = 0.0
    unconfidence_edges = 0.0
    correct_edges = 0.0
    for e in edges:
        edge = edges[e]
        first_piece_id, second_piece_id = int(e.split('-')[0][:-1]), int(e.split('-')[1][1:])
        edges_matched = False
        correct_edge = False
        if e.split('-')[0][-1] == 'L':
            if second_piece_id == first_piece_id + 1:
                correct_edge = True
                correct_edges += 1
            if individual.edge(first_piece_id, 'R') == second_piece_id:
                edges_matched = True
                edges_match += 1
                if correct_edge:
                    correct_edges_match += 1
        else:
            if second_piece_id == first_piece_id + columns:
                correct_edge = True
                correct_edges += 1
            if individual.edge(first_piece_id, 'D') == second_piece_id:
                edges_matched = True
                edges_match += 1
                if correct_edge:
                    correct_edges_match += 1
        
        wp = float(edge['wp'])
        wn = float(edge['wn'])
        confidence = wp * 1.0 / (wn + wp)
        if confidence >= 0.618:
            confidence_edges += 1
            if edges_matched:
                confidence_edges_match += 1
        else:
            unconfidence_edges += 1
            if edges_matched:
                unconfidence_edges_match += 1

    len_edges = len(edges)
    correct_edges = 1.0 if correct_edges == 0 else correct_edges
    unconfidence_edges = 1.0 if unconfidence_edges == 0 else unconfidence_edges
    confidence_edges = 1.0 if confidence_edges == 0 else confidence_edges
    len_edges = 1.0 if len_edges == 0 else len_edges

    return correct_edges_match / correct_edges, unconfidence_edges_match / unconfidence_edges, \
        confidence_edges_match / confidence_edges, edges_match / len_edges


# Don't create two instantces for this class
class GeneticAlgorithm(object):

    TERMINATION_THRESHOLD = 10

    def __init__(self, image, piece_size, population_size, generations, r, c):
        self._image = image
        self._piece_size = piece_size
        self._generations = generations
        self._elite_size = Config.elite_size
        pieces, rows, columns = image_helpers.flatten_image(image, piece_size, indexed=True, r=r, c=c)
        self.rows = rows
        self.columns = columns
        self._population = [Individual(pieces, rows, columns) for _ in range(population_size)]
        self._pieces = pieces
        self.common_edges = dict()

    def start_evolution(self, verbose):
        with open('result_file_%d.csv' % Config.round_id , 'w') as f:
            line = "%s,%s,%s,%s,%s,%s,%s\n" % ('time', 'cog_index', 'correct_in_db',
                'total_in_db', 'correct_in_GA', 'total_in_GA', 'precision')
            f.write(line)
        '''
        print("=== Pieces:      {}\n".format(len(self._pieces)))
        '''
        
        if verbose:
            from gaps.plot import Plot
            plot = Plot(self._image)

        #ImageAnalysis.analyze_image(self._pieces)

        start_time = time.time()

        fittest = None
        best_fitness_score = float("-inf")
       
        solution_found = False

        if Config.multiprocess:
            data_q = Queue()
            res_q = Queue()
            processes = []
            for pid in range(Config.process_num):
                p = Process(target=worker, args=(pid, start_time, self._pieces[:], 0))
                p.start()
                processes.append(p)
                redis_key = 'round:%d:parents' % (Config.round_id)
                redis_cli.hdel(redis_key, 'process:%d' % pid)
                redis_key = 'round:%d:children' % (Config.round_id)
                redis_cli.hdel(redis_key, 'process:%d' % pid)

        old_crowd_edge_count = 1
        for generation in range(self._generations):
            if not Config.cli_args.online and not Config.cli_args.hide_detail:
                print_progress(generation, self._generations - 1, prefix="=== Solving puzzle offline: ", start_time=start_time)
            
            refreshTimeStamp(start_time)

            ## In crowd-based algorithm, we need to access database to updata fintess measure
            ## at the beginning of each generation.
            # update fitness from database.
            
            generation_start_time = time.time()

            db_update()
            if not Config.cli_args.hide_detail:
                print("edge_count:{}/edge_prop:{}".format(db_update.crowd_edge_count, db_update.crowd_edge_count/Config.total_edges))
            
            redis_key = 'round:%d:dissimilarity' % Config.round_id
            dissimilarity_json = json.dumps(dissimilarity_measure.measure_dict)
            #print(dissimilarity_json)
            redis_cli.set(redis_key, dissimilarity_json)
            # calculate dissimilarity and best_match_table.
            ImageAnalysis.analyze_image(self._pieces)
            # fitness of all individuals need to be re-calculated.
            for _individual in self._population:
                _individual._objective = None
                _individual._fitness = None

            db_update_time = time.time()

            new_population = []

            # random.shuffle(self._population)
            self._population.sort(key=attrgetter("objective"))
            #print(','.join([str(ind.get_pieces_id_list()) for ind in self._population]))
            # Elitism
            # elite = self._get_elite_individuals(elites=self._elite_size)
            elite = self._population[-self._elite_size:]
            
            new_population.extend(elite)
            
            if Config.fitness_func_name == 'rank-based':
                #!!! self._population needs to be sorted first
                # for rank, indiv in enumerate(self._population):
                #     indiv.calc_rank_fitness(rank)
                self.calc_rank_fitness()

            select_elite_time = time.time()

            if solution_found:
                print("GA found a solution for round {}!".format(Config.round_id))
                if Config.cli_args.online:
                    GA_time = time.time() - (mongo_wrapper.get_round_start_milisecs() / 1000.0)
                    print("GA time: %.3f" % GA_time)
                else:
                    winner_time = mongo_wrapper.get_round_winner_time_milisecs() / 1000.0
                    GA_time = time.time() - start_time + \
                        mongo_wrapper.get_round_winner_time_milisecs() * Config.offline_start_percent / 1000.0
                    print("solved, winner time: %.3f, GA time: %.3f" % (winner_time, GA_time))
                if Config.multiprocess:
                    for p in processes:
                        p.terminate()
                exit(0)
            self._get_common_edges(elite[:4])

            selected_parents = roulette_selection(self._population, elites=self._elite_size)
            select_parent_time = time.time()
            result = []
            if Config.multiprocess:
                # multiprocessing
                worker_args = []
                # assign equal amount of work to process_num-1 processes
                redis_key = 'round:%d:parents' % (Config.round_id)
                redis_data = {}
                for pid in range(Config.process_num):
                    parents_data = json.dumps([(f_parent.get_pieces_id_list(), s_parent.get_pieces_id_list()) 
                        for (f_parent, s_parent) in selected_parents[(len(selected_parents)//Config.process_num)*pid \
                        : (len(selected_parents)//Config.process_num)*(pid+1)]])
                    redis_data['process:%d' % pid] = parents_data
                redis_cli.hmset(redis_key, redis_data)
                redis_key = 'round:%d:children' % (Config.round_id)
                for pid in range(Config.process_num):
                    while True:
                        children_json = redis_cli.hget(redis_key, 'process:%d' % pid)
                        if children_json:
                            children_data = json.loads(children_json)
                            if children_data:
                                if len(children_data) != 49:
                                    continue
               
                                redis_key = 'round:%d:parents' % (Config.round_id)
                                redis_cli.hdel(redis_key, 'process:%d' % pid)
                                
                                redis_key = 'round:%d:children' % (Config.round_id)
                                redis_cli.hdel(redis_key, 'process:%d' % pid)

                                result.extend(children_data)
                                break

            else:
                # non multiprocessing
                for first_parent, second_parent in selected_parents:
                    crossover = Crossover(first_parent, second_parent)
                    crossover.run()
                    child = crossover.child()
                    result.append(','.join([str(_) for _ in child.get_pieces_id_list()]))

            result = list(map(lambda x: [int(_) for _ in x.split(',')], result))
            result = [Individual([self._pieces[_] for _ in c], Config.cli_args.rows, Config.cli_args.cols, False) for c in result]
            
            new_population.extend(result)
            for child in new_population:
                if child.is_solution():
                    fittest = child
                    redis_key = 'round:' + str(Config.round_id) + ':GA_edges'
                    res = redis_cli.set(redis_key, json.dumps(list(child.edges_set())))
                    solution_found = True
                    break

            crossover_time = time.time()
            if not solution_found:
                fittest = self._best_individual()
                if fittest.fitness > best_fitness_score:
                    best_fitness_score = fittest.fitness

            self._population = new_population
        
            if verbose:
                from gaps.plot import Plot
                plot.show_fittest(fittest.to_image(), "Generation: {} / {}".format(generation + 1, self._generations))
            
            times = {
                'generation_time': time.time() - generation_start_time, 
                'db_update_time': db_update_time - generation_start_time, 
                'select_elite_time': select_elite_time - db_update_time, 
                'select_parent_time': select_parent_time - select_elite_time, 
                'crossover_time': crossover_time - select_parent_time
            }
            print(times)
        return fittest

    def _remove_unconfident_edges(self, edges_set):
        old_size = len(edges_set)
        for e in list(edges_set):
            if e in db_update.edges_confidence and db_update.edges_confidence[e] < 0.618:
                edges_set.remove(e)
        new_size = len(edges_set)
        if old_size != new_size:
            print('remove %d edges' % (old_size - new_size))

    def _merge_common_edges(self, old_edges_set, new_edges_set):
        links = {
            'L-R': {},
            'T-B': {}
        }
        for edges_set in [old_edges_set, new_edges_set]:
            for e in edges_set:
                left, right = e.split('-')
                x, tag, y = left[:-1], 'L-R' if left[-1] == 'L' else 'T-B', right[1:]
                links[tag][x] = y
        merged_set = set()
        for orient in links:
            for x, y in links[orient].items():
                merged_set.add(x + orient + y)
        return merged_set

    def _get_common_edges(self, individuals):
        confident_edges_sets, edges_sets = [], []
        for individual in individuals:
            edges_set = individual.edges_set()
            confident_edges_set = individual.confident_edges_set()
            edges_sets.append(edges_set)
            confident_edges_sets.append(confident_edges_set)
        
        confident_edges_set = confident_edges_sets[0]
        for i in range(1, len(confident_edges_sets)):
            confident_edges_set = confident_edges_set | confident_edges_sets[i]
        
        edges_set = edges_sets[0]
        for i in range(1, len(edges_sets)):
            edges_set = edges_set & edges_sets[i]

        correct_links = 0

        #self._remove_unconfident_edges(self.common_edges)
        old_common_edges = list(self.common_edges.items())
        for k, v in old_common_edges:
            if v < 1:
                del self.common_edges[k]
            else:
                self.common_edges[k] = v / 2

        new_common_edges = self._merge_common_edges(confident_edges_set, edges_set)
        new_common_edges = self._merge_common_edges(self.common_edges.keys(), new_common_edges)
        
        for e in new_common_edges:
            self.common_edges[e] = 32

        for e in new_common_edges:
            left, right = e.split('-')
            x = int(left[:-1])
            y = int(right[1:])
            if left[-1] == 'L':
                if x + 1 == y and y % Config.cli_args.rows != 0:
                    correct_links += 1
            else:
                if x + Config.cli_args.rows == y:
                    correct_links += 1
        
        with open('result_file_%d.csv' % Config.round_id , 'a') as f:
            line = "%d,%d,%d,%d,%d,%d,%.4f\n" % (Config.timestamp, db_update.cog_index, db_update.crowd_correct_edge,
                db_update.crowd_edge_count, correct_links, len(new_common_edges), 
                0 if len(new_common_edges) == 0 else float(correct_links) / float(len(new_common_edges)))
            f.write(line)
        
        redis_key = 'round:' + str(Config.round_id) + ':GA_edges'
        redis_cli.set(redis_key, json.dumps(list(new_common_edges)))
        
        print('\ntimestamp:', Config.timestamp, 'cog index:', db_update.cog_index, 
            '\ncorrect edges in db:', db_update.crowd_correct_edge, 'total edges in db:', db_update.crowd_edge_count, 
            '\ncorrect edges in GA:', correct_links, 'total edges in GA:', len(new_common_edges))
        
        return edges_set


    '''
    def _get_elite_individuals(self, elites):
        """Returns first 'elite_count' fittest individuals from population"""
        return sorted(self._population, key=attrgetter("fitness"))[-elites:]
    '''

    def _best_individual(self):
        """Returns the fittest individual from population"""
        return max(self._population, key=attrgetter("fitness"))

    def calc_rank_fitness(self):
        rank1 = 0
        while rank1 < len(self._population):
            fitness1 = Config.get_rank_fitness(rank1, len(self._population))
            indiv1 = self._population[rank1]
            rank2 = rank1 + 1
            for rank2 in range(rank1+1, len(self._population)):
                indiv2 = self._population[rank2]
                if abs(indiv1.objective-indiv2.objective) > 1e-6:
                    break
            fitness2 = Config.get_rank_fitness(rank2 - 1, len(self._population))
            for indiv in self._population[rank1: rank2]:
                indiv._fitness = (fitness1 + fitness2) / 2.0
            rank1 = rank2
