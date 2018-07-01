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
    pre_timestamp=get_formatted_date(mongo_wrapper.get_round_start_secs()),
    secs_diff=time.time()-mongo_wrapper.get_round_start_secs(),
    crowd_edge_count=0)
def db_update():
    """ Update dissimilarity_measure.measure_didct from mongo database. """
    if not Config.cli_args.offline:
        # online
        dissimilarity_measure.measure_dict.clear()
        for d in db_update.mongodb.nodes_documents():
            first_piece_id = d['index']
            for orient, orientation in zip(['right', 'bottom'], ['LR', 'TD']):
                for link in d[orient]:
                    second_piece_id = link['index']
                    # In crowd-based algorithm, dissimilarity measure = -(opp_num - sup_num)
                    measure = link['opp_num'] - link['sup_num']
                    dissimilarity_measure.measure_dict[str(first_piece_id)+orientation+str(second_piece_id)] = measure
    else:
        # offline
        cur_timestamp = get_formatted_date(time.time()-db_update.secs_diff)
        measure_dict = dissimilarity_measure.measure_dict
        for d in db_update.mongodb.actions_documents(start_timestamp=db_update.pre_timestamp, end_timestamp=cur_timestamp):
            #print("new action by {}.".format(d['player_name'] if d['player_name'] != '' else 'recommendation'))
            # skip gram
            if d['player_name'] == '':
                #print("skip recommendation")
                continue
            # if d['direction'] not in ['bottom', 'right']:
            #     continue
            if d['direction'] in ['left', 'top']:
                # reverse the direction
                first_piece_id, second_piece_id = d['to'], d['from']
                orientation = {
                    'top': 'TD',
                    'left': 'LR',
                }[d['direction']]
            elif d['direction'] in ['bottom', 'right']:
                first_piece_id, second_piece_id = d['from'], d['to']
                orientation = {
                    'bottom': 'TD',
                    'right': 'LR',
                }[d['direction']]
            else:
                print('unknown direction:{}'.format(d['direction']))
                exit(1)
            k = str(first_piece_id)+orientation+str(second_piece_id)
            if k in measure_dict:
                val = measure_dict[k]
            else:
                val = 0
                db_update.crowd_edge_count += 1
            if d['operation'].find('+') != -1:
                measure_dict[k] = val - 1
                print('{}/{}:{}->{}->{}'.format(d['player_name'],d['operation'], first_piece_id, orientation, second_piece_id))
            else:
                measure_dict[k] = val + 2
                print('{}/{}:{}->{}->{}'.format(d['player_name'],d['operation'], first_piece_id, orientation, second_piece_id))
        db_update.pre_timestamp = cur_timestamp



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

