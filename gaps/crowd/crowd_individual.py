import random
import heapq
import bisect

from gaps.crowd.nodes import Nodes
from gaps.crowd.individual import Individual

class CrowdIndividual(object):

    def __init__(self, pieces, rows, columns, shapeArray, edges):
        self.shapeArray = shapeArray
        self.pieces = pieces[:]
        self.rows = rows
        self.columns = columns
        self._pieces_length = len(pieces)
        nodesAndHints = NodesAndHints(edges, rows, columns)
        self.nodes = nodesAndHints.nodes
        self.hints = nodesAndHints.hints

        # Borders of growing kernel
        self._min_row = 0
        self._max_row = 0
        self._min_column = 0
        self._max_column = 0

        self._kernel = {}
        self._taken_positions = {}

        # Priority queue
        self._candidate_pieces = []

        root_piece = self.pieces[int(random.uniform(0, self._pieces_length))]
        self.put_piece_to_kernel(root_piece.id, (0, 0))

        # priority pool for fitness-based random selection
        # needed??

    def getIndividual(self):
        pieces = [None] * self._pieces_length

        for piece, (row, column) in self._kernel.items():
            index = (row - self._min_row) * self.columns + (column - self._min_column)
            pieces[index] = piece

        return Individual(pieces, self.rows, self.columns, shuffle=False)

    def put_piece_to_kernel(self, piece_id, position):
        self._kernel[piece_id] = position
        self._taken_positions[position] = piece_id

        available_boundaries = self._available_boundaries(position)
        for orientation, position in available_boundaries:
            probability_map = self.find_candidate_pieces_probability_map(piece_id, orientation, position)
            # shape: jagged
            candidate_pieces = sorted(probability_map.items(), lambda x, y: cmp(x[1], y[1]))
            for candidate_piece in candidate_pieces:
                if self._is_valid_piece(candidate_piece) and self.check_shape_valid(candidate_piece, position):
                    self.put_piece_to_kernel(candidate_piece, position)


    def check_shape_valid(self, piece_id, position):
        boundaries_pieces = {
            'T': _taken_positions.get((position[0] - 1, position[1]), -1)
            'R': _taken_positions.get((position[0], position[1] + 1), -1)
            'D': _taken_positions.get((position[0] + 1, position[1]), -1)
            'L': _taken_positions.get((position[0], position[1] - 1), -1)
        }
        for orientation in ['T', 'R', 'D', 'L']:
            oppose_piece = boundaries_pieces[orientation]
            if oppose_piece >= 0:
                mine_shape_orient = get_shape_orientation(orientation)
                oppose_shape_orient =  get_shape_orientation(complementary_orientation(orientation))
                if self.shapeArray[piece_id][mine_shape_orient] + self.shapeArray[oppose_piece][oppose_shape_orient] != 0:
                    return False
        return True

    def find_shape_available_pieces(self, piece_id, orientation):
        mine_shape_orient = get_shape_orientation(orientation)
        oppose_shape_orient =  get_shape_orientation(complementary_orientation(orientation))
        available_pieces = []
        for i in range(len(self.shapeArray)):
            if i == piece_id:
                continue
            if self.shapeArray[piece_id][mine_shape_orient] + self.shapeArray[i][oppose_shape_orient] == 0:
                available_pieces.append(i)
        return np.random.shuffle(available_pieces)


    def find_candidate_pieces_probability_map(self, piece_id, orientation, position):
        probability_map = {}
        
        wp_sum = self.nodes[piece_id][orientation]['wp_sum']
        wn_sum = self.nodes[piece_id][orientation]['wn_sum']

        for weak_link_piece in self.nodes[piece_id][orientation]['indexes']:
            wp = self.nodes[piece_id][orientation]['indexes'][weak_link_piece]['wp']
            probability = wp * 1.0 / self.nodes[piece_id][orientation]['wp_sum']
            probability_map[weak_link_piece] = probability

        strong_link_piece = self.hints[piece_id][orientation]
        if strong_link_piece >= 0:
            for weak_link_piece in probability_map:
                probability = probability_map[weak_link_piece]
                if weak_link_piece == strong_link_piece:
                    probability_map[weak_link_piece] = 0.618 + (1 - 0.618) * probability
                else:
                    probability_map[weak_link_piece] = (1 - 0.618) * probability

        choose_other_probability = 1.0
        if not wp_sum + wn_sum == 0:
            choose_other_probability = wn_sum * 1.0 / wp_sum + wn_sum

        if choose_other_probability > 0:
            for link_piece in probability_map:
                probability = probability_map[link_piece]
                probability_map[link_piece] = probability * (1 - choose_other_probability)
            available_pieces = self.find_shape_available_pieces(piece_id, orientation)
            for other_piece in available_pieces:
                if not other_piece in probability_map:
                    probability_map[other_piece] = choose_other_probability / len(available_pieces)
        
        pop_sum = 0.0
        max_probability = 0
        max_probability_piece = -1
        for link_piece in probability_map:
            if not self._is_valid_piece(link_piece):
                pop_sum += probability_map.pop(link_piece)
            elif probability_map[link_piece] > max_probability:
                max_probability = probability_map[link_piece]
                max_probability_piece = link_piece

        probability_sum = 0.0
        for link_piece in probability_map:
            probability = probability_map[link_piece]
            probability *= 1.0 / (1.0 - pop_sum)
            probability_sum += probability
            probability_map[link_piece] = probability

        probability_map[max_probability_piece] += 1.0 - probability_sum

        return probability_map

    def _add_priority_piece_candidate(self, piece_id, position, priority, relative_piece):
        piece_candidate = (priority, (position, piece_id), relative_piece)
        heapq.heappush(self._candidate_pieces, piece_candidate)

    def _available_boundaries(self, row_and_column):
        (row, column) = row_and_column
        boundaries = []

        if not self._is_kernel_full():
            positions = {
                "T": (row - 1, column),
                "R": (row, column + 1),
                "D": (row + 1, column),
                "L": (row, column - 1)
            }
            for orientation, position in positions.items():
                if position not in self._taken_positions and self._is_in_range(position):
                    self._update_kernel_boundaries(position)
                    boundaries.append((orientation, position))

        return boundaries

    def _is_kernel_full(self):
        return len(self._kernel) == self._pieces_length

    def _is_in_range(self, row_and_column):
        (row, column) = row_and_column
        return self._is_row_in_range(row) and self._is_column_in_range(column)

    def _is_row_in_range(self, row):
        current_rows = abs(min(self._min_row, row)) + abs(max(self._max_row, row))
        return current_rows < self._child_rows

    def _is_column_in_range(self, column):
        current_columns = abs(min(self._min_column, column)) + abs(max(self._max_column, column))
        return current_columns < self._child_columns

    def _update_kernel_boundaries(self, row_and_column):
        (row, column) = row_and_column
        self._min_row = min(self._min_row, row)
        self._max_row = max(self._max_row, row)
        self._min_column = min(self._min_column, column)
        self._max_column = max(self._max_column, column)

    def _is_valid_piece(self, piece_id):
        return piece_id is not None and piece_id not in self._kernel

def get_shape_orientation(orientation):
    return {
        'T': 'topTab',
        'R': 'rightTab',
        'D': 'bottomTab',
        'L': 'leftTab',
    }.get(orientation, None)

def complementary_orientation(orientation):
    return {
        "T": "D",
        "R": "L",
        "D": "T",
        "L": "R"
    }.get(orientation, None)
