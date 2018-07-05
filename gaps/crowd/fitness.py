import numpy as np
from gaps.crowd.dbaccess import mongo_wrapper
from gaps.config import Config
import time
from gaps.utils import get_formatted_date

def static_vars(**kwargs):
    """ Decorator for initializing static function variables. """
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func
    return decorate

@static_vars(mongodb=mongo_wrapper, 
    secs_diff=time.time() * 1000 - mongo_wrapper.get_round_winner_time_milisecs() * Config.offline_start_percent,
    crowd_edge_count=0)
def db_update():
    """ Update dissimilarity_measure.measure_didct from mongo database. """
    if not Config.cli_args.offline:
        # online
        dissimilarity_measure.measure_dict.clear()
        edges = db_update.mongodb.edges_documents()
        db_update.crowd_edge_count = len(edges)
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
            dissimilarity_measure.measure_dict[str(first_piece_id)+orientation+str(second_piece_id)] = measure
    else:
        # offline
        timestamp = time.time() * 1000 - db_update.secs_diff
        measure_dict = dissimilarity_measure.measure_dict
        cogs = list(db_update.mongodb.cogs_documents(timestamp=timestamp))
        if len(cogs) > 0:
            cog = cogs[-1]
            edges = cog['edges_changed']
            db_update.crowd_edge_count = len(edges)
            # print("crowd_edge_count: %d" % crowd_edge_count)
            for e in edges:
                first_piece_id, second_piece_id = int(e.split('-')[0][:-1]), int(e.split('-')[1][1:])
                if e.split('-')[0][-1] == 'L':
                    orient = 'LR'
                else:
                    orient = 'TD'
                key = str(first_piece_id)+orient+str(second_piece_id)
                edge = edges[e]
                measure = float(edge['wn']) - float(edge['wp'])
                measure_dict[key] = measure



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
    k = str(first_piece.id)+orientation+str(second_piece.id)
    if not Config.use_pixel:
        return dissimilarity_measure.measure_dict.get(k, 0)

    else:
        if k in dissimilarity_measure.measure_dict:
            return dissimilarity_measure.measure_dict[k]
        if db_update.crowd_edge_count >= int(Config.use_pixel_shred * Config.total_edges):
            # use pixel difference
            # | L | - | R |
            if orientation == "LR":
                color_difference = first_piece[:, -Config.erase_edge-1, :] - second_piece[:, Config.erase_edge, :]

            # | T |
            #   |
            # | D |
            if orientation == "TD":
                color_difference = first_piece[Config.erase_edge-1, :, :] - second_piece[Config.erase_edge, :, :]

            squared_color_difference = np.power(color_difference / 255.0, 2)
            color_difference_per_row = np.sum(squared_color_difference, axis=1)
            total_difference = np.sum(color_difference_per_row, axis=0)

            value = np.sqrt(total_difference)

            value /= np.sqrt(Config.cli_args.size * 3) # to make sure value < 1

            # value = -value
            return value
        else:
            # not use pixel difference
            return 0

