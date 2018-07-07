import numpy as np
from gaps.crowd.dbaccess import mongo_wrapper
from gaps.crowd.nodes import NodesAndHints
from gaps.crowd.crowd_individual import CrowdIndividual

import time
import datetime
import json

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

def check_shape_valid(piece_id, position, puzzle, columns, shapeArray):
    boundaries_pieces = {
        'T': puzzle[position - columns] if position >= columns else -1,
        'L': puzzle[position - 1] if (position % columns) > 0 else -1,
    }
    for orientation in ['T', 'L']:
        oppose_piece = boundaries_pieces[orientation]
        if oppose_piece >= 0:
            mine_shape_orient = get_shape_orientation(orientation)
            oppose_shape_orient =  get_shape_orientation(complementary_orientation(orientation))
            if shapeArray[piece_id][mine_shape_orient] + shapeArray[oppose_piece][oppose_shape_orient] != 0:
                return False
    return True

r = mongo_wrapper.round_document()
shapeArray = mongo_wrapper.shapes_documents()
rows = r['tilesPerRow']
columns = r['tilesPerColumn']
cogs = list(mongo_wrapper.cogs_documents(50000))
cog = cogs[-1]
edges = cog['edges_changed']
#print(cog['correctLinks'], cog['totalLinks'])

#nodesAndHints = NodesAndHints(edges, rows, columns)
ci = CrowdIndividual(rows, columns, shapeArray, edges)
'''
used_pieces = set()
puzzle = [-1 for _ in range(rows * columns)]

results = []

def put_piece(piece_id, position, puzzle, used_pieces, columns, shapeArray):
	puzzle[position] =  piece_id
	used_pieces.add(piece_id)
	if position == len(puzzle) - 1:
		results.append(puzzle.copy())
	for i in range(rows * columns):
		if check_shape_valid(piece_id, position, puzzle, columns, shapeArray) and not i in used_pieces:
			put_piece(i, position + 1, puzzle, used_pieces, columns, shapeArray)
	used_pieces.remove(piece_id)
	puzzle[position] = -1

for piece_id in range(rows * columns):
	put_piece(piece_id, 0, puzzle, used_pieces, columns, shapeArray)
	print('root:', len(results))
	'''


