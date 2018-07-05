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
from gaps.crowd.image_analysis import ImageAnalysis
from gaps.crowd.fitness import db_update
from gaps.crowd.dbaccess import JsonDB, mongo_wrapper
from gaps.config import Config
from multiprocessing import Process, Queue

def worker(data_q, res_q):
    while True:
        best_match_table, parents = data_q.get(block=True)
        ImageAnalysis.best_match_table = best_match_table
        children = []
        for first_parent, second_parent in parents:
            crossover = Crossover(first_parent, second_parent)
            crossover.run()
            child = crossover.child()
            child.is_solution() # is_solution is a decorated function. calculate here.
            children.append(child)
        res_q.put(children, block=True)
    # return children, has_solution, solution

# Don't create two instantces for this class
class GeneticAlgorithm(object):

    TERMINATION_THRESHOLD = 10

    def __init__(self, image, piece_size, population_size, generations, r, c):
        self._image = image
        self._piece_size = piece_size
        self._generations = generations
        self._elite_size = Config.elite_size
        pieces, rows, columns = image_helpers.flatten_image(image, piece_size, indexed=True, r=r, c=c)
        self._population = [Individual(pieces, rows, columns) for _ in range(population_size)]
        self._pieces = pieces

    def start_evolution(self, verbose):
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
        '''
        termination_counter = 0
        '''

        # save elites of each generation.
        if not Config.cli_args.offline:
            # online
            elites_db = JsonDB(collection_name='elites', doc_name='round'+str(Config.round_id))
        else:
            # offline
            collection_name = 'elites_offline_mp' if Config.multiprocess else \
                'elites_offline_pixel' if Config.use_pixel else'elites_offline'
            elites_db = JsonDB(collection_name=collection_name, doc_name='round'+str(Config.round_id)\
                +'_'+Config.fitness_func_name+'_paper_'+str(Config.rank_based_MAX)+'_skiprecom_'\
                +str(Config.population)+'_'+str(Config.elite_percentage)\
                +('_SUS' if Config.roulette_alt == True else '')+('_{}'.format(Config.use_pixel_shred)\
                if Config.use_pixel else '')+'_'+str(Config.erase_edge)+'_debug')
       
        solution_found = False

        if Config.multiprocess:
            data_q = Queue()
            res_q = Queue()
            processes = []
            for i in range(Config.process_num):
                p = Process(target=worker, args=(data_q, res_q))
                p.start()
                processes.append(p)

        for generation in range(self._generations):
            
            if Config.cli_args.offline:
                print_progress(generation, self._generations - 1, prefix="=== Solving puzzle offline: ", start_time=start_time)
            

            ## In crowd-based algorithm, we need to access database to updata fintess measure
            ## at the beginning of each generation.
            # update fitness from database.

            if not Config.cli_args.offline:
                if mongo_wrapper.is_finished():
                    print("Round {} has finished. Exit GA.".format(Config.round_id))
                    elites_db.save()
                    exit(0)

            db_update()
            print("edge_count:{}/edge_prop:{}".format(db_update.crowd_edge_count, db_update.crowd_edge_count/Config.total_edges))
            # calculate dissimilarity and best_match_table.
            ImageAnalysis.analyze_image(self._pieces)
            # fitness of all individuals need to be re-calculated.
            for _individual in self._population:
                _individual._objective = None
                _individual._fitness = None

            new_population = []

            # random.shuffle(self._population)
            self._population.sort(key=attrgetter("objective"))
            # Elitism
            # elite = self._get_elite_individuals(elites=self._elite_size)
            elite = self._population[-self._elite_size:]
            new_population.extend(elite)
            
            if Config.fitness_func_name == 'rank-based':
                #!!! self._population needs to be sorted first
                # for rank, indiv in enumerate(self._population):
                #     indiv.calc_rank_fitness(rank)
                self.calc_rank_fitness()
            
            # write elites to Json
            for e in elite:
                elites_db.add(e.to_json_data(generation, start_time))

            if solution_found:
                print("GA found a solution for round {}!".format(Config.round_id))
                winner_time = mongo_wrapper.get_round_winner_time_milisecs() / 1000.0
                GA_time = time.time() - start_time + \
                    mongo_wrapper.get_round_winner_time_milisecs() * Config.offline_start_percent / 1000.0
                print("solved, winner time: %d, GA time: %d" % (winner_time, GA_time))
                if Config.multiprocess:
                    for p in processes:
                        p.terminate()
                exit(0)

            selected_parents = roulette_selection(self._population, elites=self._elite_size)

            if Config.multiprocess:
                # multiprocessing
                worker_args = []
                # assign equal amount of work to process_num-1 processes
                for i in range(Config.process_num-1):
                    worker_args.append(selected_parents[(len(selected_parents)//Config.process_num)*i \
                        : (len(selected_parents)//Config.process_num)*(i+1)])
                # assign the rest to the last process
                worker_args.append(selected_parents[(len(selected_parents)//Config.process_num)*(Config.process_num-1):len(selected_parents)])
                # t1 = time.time()
                # with Pool(processes=Config.process_num) as pool:
                #     t1 = time.time()
                #     results = pool.map(worker, worker_args)
                #     print('from mp:{}'.format(time.time()-t1))
                for i in range(Config.process_num):
                    data_q.put((ImageAnalysis.best_match_table, worker_args[i]),\
                        block=True)
                results = []
                for i in range(Config.process_num):
                    results.append(res_q.get(block=True))

            else:
                # non multiprocessing
                result = []
                for first_parent, second_parent in selected_parents:
                    crossover = Crossover(first_parent, second_parent)
                    crossover.run()
                    child = crossover.child()
                    result.append(child)
                    # if child.is_solution():
                    #     elites_db.add(child.to_json_data(generation+1, start_time))
                    #     elites_db.save()
                    #     solution_found = True
                    # new_population.append(child)
                results = [result]

            for result in results:
                new_population.extend(result)
                for child in result:
                    if child.is_solution():
                        solution_found = True
                        elites_db.add(child.to_json_data(generation+1, start_time))
                        elites_db.save()
                        break
                # time_count += result[3]
                # if result[1] and not solution_found: # has solution
                #     solution_found = True
                #     elites_db.add(result[2].to_json_data(generation+1, start_time))
                #     elites_db.save()
        

            fittest = self._best_individual()

            '''
            if fittest.fitness <= best_fitness_score:
                termination_counter += 1
            else:
                best_fitness_score = fittest.fitness

            if termination_counter == self.TERMINATION_THRESHOLD:
                print("\n\n=== GA terminated")
                print("=== There was no improvement for {} generations".format(self.TERMINATION_THRESHOLD))
                return fittest
            '''
            if fittest.fitness > best_fitness_score:
                best_fitness_score = fittest.fitness

            self._population = new_population
            
            if verbose:
                from gaps.plot import Plot
                plot.show_fittest(fittest.to_image(), "Generation: {} / {}".format(generation + 1, self._generations))

        elites_db.save()    
        return fittest
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
