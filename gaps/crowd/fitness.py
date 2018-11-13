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

def update_shape_dissimilarity(measure_dict):
    shapes = db_update.mongodb.shapes_documents()
    for first_piece_id in range(len(shapes)):
        for second_piece_id in range(len(shapes)):
            #print(shapes[first_piece_id], shapes[second_piece_id])
            if(shapes[first_piece_id]['rightTab'] + shapes[second_piece_id]['leftTab'] != 0):
                key = str(first_piece_id) + 'LR' + str(second_piece_id)
                measure_dict[key] = Config.shape_dissimilarity
            if(shapes[first_piece_id]['bottomTab'] + shapes[second_piece_id]['topTab'] != 0):
                key = str(first_piece_id) + 'TD' + str(second_piece_id)
                measure_dict[key] = Config.shape_dissimilarity

@static_vars(mongodb=mongo_wrapper, 
    secs_diff=time.time() * 1000 - mongo_wrapper.get_round_winner_time_milisecs() * Config.offline_start_percent,
    crowd_edge_count=0, only_pixel_update=False, crowd_correct_edge=0, cog_index = 0, edges_confidence={})
def db_update():
    """ Update dissimilarity_measure.measure_didct from mongo database. """
    if Config.only_pixel:
        if db_update.only_pixel_update:
            return
        measure_dict = dissimilarity_measure.measure_dict
        update_shape_dissimilarity(measure_dict)
        #print(measure_dict)
        db_update.only_pixel_update = True
    else:
        if Config.cli_args.online:
            # online
            measure_dict = dissimilarity_measure.measure_dict
            #measure_dict.clear()
            edges, db_update.cog_index = db_update.mongodb.edges_documents(), -1
            if edges:
                db_update.crowd_edge_count = len(edges)
                db_update.crowd_correct_edge = 0
                for e, edge in edges.items():
                    first_piece_id = edge['x']
                    if edge['tag'] == 'L-R':
                        orient = 'LR'
                    else:
                        orient = 'TD'
                    second_piece_id = edge['y']
                    db_update.edges_confidence[e] = float(edge['confidence'])
                    if Config.measure_weight:
                        wp = edge['weight']
                        confidence = edge['confidence']
                        if confidence > 0:
                            wn = wp / confidence - wp + 0.0
                        else:
                            wn = 0.0
                            opposers = edge['opposers']
                            for o in opposers:
                                wn += opposers[o]
                        measure = wn * len(edge['opposers']) - wp * len(edge['supporters'])
                    else:
                        measure = len(edge['opposers']) - len(edge['supporters'])
                    key = str(first_piece_id)+orient+str(second_piece_id)
                    measure_dict[key] = measure
                    if orient == 'LR' and first_piece_id + 1 == second_piece_id and second_piece_id % Config.cli_args.rows != 0:
                        db_update.crowd_correct_edge += 1
                    if orient == 'TD' and first_piece_id + Config.cli_args.rows == second_piece_id:
                        db_update.crowd_correct_edge += 1
            update_shape_dissimilarity(measure_dict)
        else:
            # offline
            measure_dict = dissimilarity_measure.measure_dict
            #measure_dict.clear()
            edges, db_update.cog_index = db_update.mongodb.cog_edges_documents(Config.timestamp)
            if edges:
                db_update.crowd_edge_count = len(edges)
                db_update.crowd_correct_edge = 0
                # print("crowd_edge_count: %d" % crowd_edge_count)
                for e, edge in edges.items():
                    first_piece_id, second_piece_id = int(e.split('-')[0][:-1]), int(e.split('-')[1][1:])
                    if e.split('-')[0][-1] == 'L':
                        orient = 'LR'
                    else:
                        orient = 'TD'
                    key = str(first_piece_id)+orient+str(second_piece_id)
                    wp = float(edge['wp'])
                    wn = float(edge['wn'])
                    oLen = float(edge['oLen'])
                    sLen = float(edge['sLen'])
                    db_update.edges_confidence[e] = wp/(wn + wp) if (wn + wp) > 0 else 0
                    if Config.measure_weight:
                        measure = wn * oLen - wp * sLen
                    else:
                        measure = oLen - sLen
                    measure_dict[key] = measure
                    if orient == 'LR' and first_piece_id + 1 == second_piece_id and second_piece_id % Config.cli_args.rows != 0:
                        db_update.crowd_correct_edge += 1
                    if orient == 'TD' and first_piece_id + Config.cli_args.rows == second_piece_id:
                        db_update.crowd_correct_edge += 1
            update_shape_dissimilarity(measure_dict)


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
            dissimilarity_measure.measure_dict[k] = value
            # value = -value
            return value
        else:
            # not use pixel difference
            return 0

