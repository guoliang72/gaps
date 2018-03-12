import numpy as np
from gaps.crowd.mongodbaccess import MongoWrapper

def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

@static_vars(mongodb=MongoWrapper())
def db_update():
    dissimilarity_measure.measure_dict.clear()
    for d in db_update.mongodb.documents():
        first_piece_id = d['index']
        for orient, orientation in zip(['right', 'bottom'], ['LR', 'TD']):
            for link in d[orient]:
                second_piece_id = link['index']
                # In crowd-based algorithm, dissimilarity measure = -(opp_num - sup_num)
                measure = link['opp_num'] - link['sup_num']
                dissimilarity_measure.measure_dict[str(first_piece_id)+orientation+str(second_piece_id)] = measure

@static_vars(measure_dict=dict())
def dissimilarity_measure(first_piece, second_piece, orientation="LR"):
    """Calculates color difference over all neighboring pixels over all color channels.

    The dissimilarity measure relies on the premise that adjacent jigsaw pieces in the original image tend to share
    similar colors along their abutting edges, i.e., the sum (over all neighboring pixels) of squared color differences
    (over all three color bands) should be minimal. Let pieces pi , pj be represented in normalized L*a*b*
    space by corresponding W x W x 3 matrices, where W is the height/width of each piece (in pixels).

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
    # edge-based fitness
    '''
    rows, columns, _ = first_piece.shape()
    color_difference = None

    # | L | - | R |
    if orientation == "LR":
        color_difference = first_piece[:rows, columns - 1, :] - second_piece[:rows, 0, :]

    # | T |
    #   |
    # | D |
    if orientation == "TD":
        color_difference = first_piece[rows - 1, :columns, :] - second_piece[0, :columns, :]

    squared_color_difference = np.power(color_difference / 255.0, 2)
    color_difference_per_row = np.sum(squared_color_difference, axis=1)
    total_difference = np.sum(color_difference_per_row, axis=0)

    value = np.sqrt(total_difference)

    return value
    '''
    value = dissimilarity_measure.measure_dict.get(str(first_piece.id)+orientation+str(second_piece.id), 0)
    return value

