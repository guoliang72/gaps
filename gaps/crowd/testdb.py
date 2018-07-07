import numpy as np
from gaps.crowd.dbaccess import mongo_wrapper
from gaps.crowd.nodes import NodesAndHints
from gaps.crowd.crowd_individual import CrowdIndividual

import time
import datetime
import json

r = mongo_wrapper.round_document()
shapeArray = mongo_wrapper.shapes_documents()
rows = r['tilesPerRow']
columns = r['tilesPerColumn']
cogs = list(mongo_wrapper.cogs_documents(50000))
cog = cogs[-1]
edges = cog['edges_changed']
#print(cog['correctLinks'], cog['totalLinks'])

nodesAndHints = NodesAndHints(edges, rows, columns)
#ci = CrowdIndividual(rows, columns, shapeArray, edges)
