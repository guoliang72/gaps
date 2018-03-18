from __future__ import print_function
import time
from operator import attrgetter
from gaps import image_helpers
from gaps.selection import roulette_selection
# from gaps.plot import Plot
from gaps.progress_bar import print_progress
from gaps.crowd.crossover import Crossover
from gaps.crowd.individual import Individual
from gaps.crowd.image_analysis import ImageAnalysis
from gaps.crowd.fitness import db_update
from gaps.crowd.mongodbaccess import mongo_wrapper
from gaps.config import Config


# Don't create two instantces for this class
class GeneticAlgorithm(object):

    TERMINATION_THRESHOLD = 10

    def __init__(self, image, piece_size, population_size, generations, r, c, elite_size=2):
        self._image = image
        self._piece_size = piece_size
        self._generations = generations
        self._elite_size = elite_size
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

        for generation in range(self._generations):
            '''
            print_progress(generation, self._generations - 1, prefix="=== Solving puzzle: ")
            '''

            ## In crowd-based algorithm, we need to access database to updata fintess measure
            ## at the beginning of each generation.
            # update fitness from database.

            if mongo_wrapper.is_finished():
                print("Round {} has finished. Exit GA.".format(Config.round_id))
                exit(0)

            db_update()
            # calculate dissimilarity and best_match_table.
            ImageAnalysis.analyze_image(self._pieces)
            # fitness of all individuals need to be re-calculated.
            for _individual in self._population:
                _individual._fitness = None

            new_population = []

            # Elitism
            elite = self._get_elite_individuals(elites=self._elite_size)
            new_population.extend(elite)
            # write elites to mongo database
            for e in elite:
                mongo_wrapper.write_elites(e.to_mongo_document(generation))

            selected_parents = roulette_selection(self._population, elites=self._elite_size)

            for first_parent, second_parent in selected_parents:
                crossover = Crossover(first_parent, second_parent)
                crossover.run()
                child = crossover.child()
                if child.is_solution():
                    end_time = time.time()
                    mongo_wrapper.write_solution(child.to_mongo_document(generation+1), start_time, end_time)

                    # send HTTP message to server
                    print("GA found a solution for round {}!".format(Config.round_id))
                    exit(0)
                new_population.append(child)

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
            
        return fittest

    def _get_elite_individuals(self, elites):
        """Returns first 'elite_count' fittest individuals from population"""
        return sorted(self._population, key=attrgetter("fitness"))[-elites:]

    def _best_individual(self):
        """Returns the fittest individual from population"""
        return max(self._population, key=attrgetter("fitness"))
