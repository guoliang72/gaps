"""Selects fittest individuals from given population."""

import random
import bisect
from gaps.config import Config

try:
    xrange          # Python 2
except NameError:
    xrange = range  # Python 3


def roulette_selection(population, elites=4):
    """Roulette wheel selection.

    Each individual is selected to reproduce, with probability directly
    proportional to its fitness score.

    :params population: Collection of the individuals for selecting.
    :params elite: Number of elite individuals passed to next generation.

    Usage::

        >>> from gaps.selection import roulette_selection
        >>> selected_parents = roulette_selection(population, 10)

    """
    fitness_values = [individual.fitness for individual in population]
    probability_intervals = [sum(fitness_values[:i + 1]) for i in range(len(fitness_values))]

    if Config.roulette_alt:
        # select two individuals(parents) in each round of roulette.
        def select_parents():
            """Selects random individual from population based on fitess value"""
            random_select = random.uniform(0, probability_intervals[-1])
            selected_index_first = bisect.bisect_left(probability_intervals, random_select)
            random_select = (random_select + probability_intervals[-1] / 2) % probability_intervals[-1]
            selected_index_second = bisect.bisect_left(probability_intervals, random_select)
            return population[selected_index_first], population[selected_index_second]
    else:
        # select one individual in each round of roulette.
        def select_parents():
            """Selects random individual from population based on fitess value"""
            random_select = random.uniform(0, probability_intervals[-1])
            selected_index_first = bisect.bisect_left(probability_intervals, random_select)
            random_select = random.uniform(0, probability_intervals[-1])
            selected_index_second = bisect.bisect_left(probability_intervals, random_select)
            return population[selected_index_first], population[selected_index_second]

    selected = []
    for i in xrange(len(population) - elites):
        first, second = select_parents()
        selected.append((first, second))

    return selected
