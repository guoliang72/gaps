import numpy as np
from gaps.crowd.mongodbaccess import mongo_wrapper

def static_vars(**kwargs):
    """ Decorator for initializing static function variables. """
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

@static_vars(mongodb=mongo_wrapper)
def db_update():
    """ Update dissimilarity_measure.measure_didct from mongo database. """
    dissimilarity_measure.measure_dict.clear()
    for d in db_update.mongodb.nodes_documents():
        first_piece_id = d['index']
        for orient, orientation in zip(['right', 'bottom'], ['LR', 'TD']):
            for link in d[orient]:
                second_piece_id = link['index']
                # In crowd-based algorithm, dissimilarity measure = -(opp_num - sup_num)
                measure = link['opp_num'] - link['sup_num']
                dissimilarity_measure.measure_dict[str(first_piece_id)+orientation+str(second_piece_id)] = measure

@static_vars(measure_dict=dict())
def dissimilarity_measure(first_piece, second_piece, orientation="LR"):
    """

    :params first_piece:  First input piece for calculation.
    :params second_piece: Second input piece for calculation.
    :params orientation:  How input pieces are oriented.

                          LR => 'Left - Right'
                          TD => 'Top - Down'

    Usage::

        >>> from gaps.fitness import dissimilarity_measure
        >>> from gaps.piece import Piece
        >>> p1, p2 = Piece(), Piece()
        >>> dissimilarity_measure(p1, p2, orientation="TD")

    """
    # crowd-based fitness
    '''
    # | L | - | R |

    # | T |
    #   |
    # | D |

    '''
    value = dissimilarity_measure.measure_dict.get(str(first_piece.id)+orientation+str(second_piece.id), 0)
    return value

