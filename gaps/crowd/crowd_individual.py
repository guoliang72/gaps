import numpy as np

from gaps.crowd.nodes import NodesAndHints
#from gaps.crowd.individual import Individual

class CrowdIndividual(object):

    def __init__(self, rows, columns, shapeArray, edges):
        self.shapeArray = shapeArray
        self.pieces = [i for i in range(rows * columns)]
        self.rows = rows
        self.columns = columns
        self._pieces_length = len(self.pieces)
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

    
        self.used_pieces = set()
        self.puzzle = [-1 for _ in range(rows * columns)]
        self.results = []
        for root_piece in range(self.rows * self.columns):
            self.put_piece(root_piece, 0)


    def put_piece(self, piece_id, position):
        self.puzzle[position] = piece_id
        self.used_pieces.add(piece_id)
        if position == len(self.puzzle) - 1 and len(self.used_pieces) == len(self.puzzle):
            print(self.puzzle)
            self.results.append(self.puzzle.copy())

        if position >= self.columns and self.puzzle[position - self.columns] < 0:
            probability_map = self.find_candidate_pieces_probability_map(piece_id, 'T')
            if probability_map:
                size = 3 if len(probability_map) > 3 else len(probability_map)
                top_pieces = np.random.choice(list(probability_map.keys()), size=size, replace=False, p=list(probability_map.values()))
                for top_piece in top_pieces:
                    if self.check_shape_valid(top_piece, position - self.columns) and not top_piece in self.used_pieces:
                        self.put_piece(top_piece, position - self.columns)


        if (position % self.columns) < (self.columns - 1) and self.puzzle[position + 1] < 0:
            probability_map = self.find_candidate_pieces_probability_map(piece_id, 'R')
            if probability_map:
                size = 3 if len(probability_map) > 3 else len(probability_map)
                right_pieces = np.random.choice(list(probability_map.keys()), size=size, replace=False, p=list(probability_map.values()))
                for right_piece in right_pieces:
                    if self.check_shape_valid(right_piece, position + 1) and not right_piece in self.used_pieces:
                        self.put_piece(right_piece, position + 1)

        if position < (self.columns * self.rows - self.columns) and self.puzzle[position + self.columns] < 0:
            probability_map = self.find_candidate_pieces_probability_map(piece_id, 'D')
            if probability_map:
                size = 3 if len(probability_map) > 3 else len(probability_map)
                bottom_pieces = np.random.choice(list(probability_map.keys()), size=size, replace=False, p=list(probability_map.values()))
                for bottom_piece in bottom_pieces:
                    if self.check_shape_valid(bottom_piece, position + self.columns) and not bottom_piece in self.used_pieces:
                        self.put_piece(bottom_piece, position + self.columns)

        if (position % self.columns) > 0 and self.puzzle[position - 1] < 0:
            probability_map = self.find_candidate_pieces_probability_map(piece_id, 'L')
            if probability_map:
                size = 3 if len(probability_map) > 3 else len(probability_map)
                left_pieces = np.random.choice(list(probability_map.keys()), size=size, replace=False, p=list(probability_map.values()))
                for left_piece in left_pieces:
                    if self.check_shape_valid(left_piece, position - 1) and not left_piece in self.used_pieces:
                        self.put_piece(left_piece, position - 1)


        self.used_pieces.remove(piece_id)
        self.puzzle[position] = -1


    def put_piece_to_kernel(self, piece_id, position):
        self._kernel[piece_id] = position
        self._taken_positions[position] = piece_id

        available_boundaries = self._available_boundaries(position)
        for orientation, position in available_boundaries:
            probability_map = self.find_candidate_pieces_probability_map(piece_id, orientation, position)
            print('probability_map', probability_map, sum(list(probability_map.values())))
            # shape: jagged
            candidate_pieces = [i[0] for i in sorted(probability_map.items(), key=lambda a:a[1], reverse=True)]
            print(candidate_pieces)
            for candidate_piece in candidate_pieces:
                if self._is_valid_piece(candidate_piece) and self.check_shape_valid(candidate_piece, position):
                    self.put_piece_to_kernel(candidate_piece, position)
                    break

    def check_shape_valid(self, piece_id, position):
        boundaries_pieces = {
            'T': self.puzzle[position - self.columns] if position >= self.columns else -1,
            'R': self.puzzle[position + 1] if (position % self.columns) < (self.columns - 1) else -1,
            'D': self.puzzle[position + self.columns] if position < (self.columns * self.rows - self.columns) else -1,
            'L': self.puzzle[position - 1] if (position % self.columns) > 0 else -1,
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
        np.random.shuffle(available_pieces)
        return available_pieces


    def find_candidate_pieces_probability_map(self, piece_id, orientation):
        probability_map = {}

        wp_sum = 0.0
        wn_sum = 0.0
        if piece_id in self.nodes:
            wp_sum = self.nodes[piece_id][orientation]['wp_sum']
            wn_sum = self.nodes[piece_id][orientation]['wn_sum']

            if wp_sum > 0:
                for weak_link_piece in self.nodes[piece_id][orientation]['indexes']:
                    wp = self.nodes[piece_id][orientation]['indexes'][weak_link_piece]['wp']
                    probability = wp * 1.0 / wp_sum
                    probability_map[weak_link_piece] = probability

            strong_link_piece = self.hints[piece_id][orientation]
            if strong_link_piece >= 0:
                for weak_link_piece in probability_map:
                    probability = probability_map.get(weak_link_piece, 0)
                    if weak_link_piece == strong_link_piece:
                        probability_map[weak_link_piece] = 0.618 + (1 - 0.618) * probability
                    else:
                        probability_map[weak_link_piece] = (1 - 0.618) * probability

        #print('first', probability_map)

        choose_other_probability = 1.0
        if not wp_sum + wn_sum == 0:
            choose_other_probability = wn_sum * 1.0 / (wp_sum + wn_sum)

        #print(wp_sum, wn_sum, choose_other_probability)

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
            probability = probability_map[link_piece]
            if link_piece in self.used_pieces:
                probability_map[link_piece] = 0
                pop_sum += probability
            elif probability >= max_probability:
                max_probability = probability
                max_probability_piece = link_piece

        probability_sum = 0.0
        if pop_sum < 1:
            for link_piece in probability_map:
                probability = probability_map[link_piece]
                probability *= 1.0 / (1.0 - pop_sum)
                probability_sum += probability
                probability_map[link_piece] = probability

        if max_probability_piece >= 0:
            probability_map[max_probability_piece] += 1.0 - probability_sum
            return probability_map
        else:
            return None

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
        return current_rows < self.rows

    def _is_column_in_range(self, column):
        current_columns = abs(min(self._min_column, column)) + abs(max(self._max_column, column))
        return current_columns < self.columns

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
