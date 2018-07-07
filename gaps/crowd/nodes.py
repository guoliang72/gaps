import json

constants = {
    'phi': 0.618,
    'epsilon': 0.2
}

class NodesAndHints(object):

    def __init__(self, edges, rows, columns):
        self.rows = rows
        self.columns = columns
        self.nodes = {}
        self.hints = {}
        for e in edges:
            first_piece_id, second_piece_id = int(e.split('-')[0][:-1]), int(e.split('-')[1][1:])
            if not first_piece_id in self.nodes:
                self.initNodesAndHints(first_piece_id)
            if not second_piece_id in self.nodes:
                self.initNodesAndHints(second_piece_id)
            edge = edges[e]
            wp = float(edge['wp'])
            wn = float(edge['wn'])
            if e.split('-')[0][-1] == 'L':
                self.updateNodesAndHints(first_piece_id, 'R', second_piece_id, wp, wn)
                self.updateNodesAndHints(second_piece_id, 'L', first_piece_id, wp, wn)
            else:
                self.updateNodesAndHints(first_piece_id, 'D', second_piece_id, wp, wn)
                self.updateNodesAndHints(second_piece_id, 'T', first_piece_id, wp, wn)
        self.checkUnsureHints()
        print(json.dumps(self.nodes, indent=4))


    def initNodesAndHints(self, piece_id):
        self.nodes[piece_id] = {
            'T': {
                'indexes': {},
                'maxConfidence': constants['phi'],
                'wp_sum': 0.0,
                'wn_sum': 0.0,
            },
            'R': {
                'indexes': {},
                'maxConfidence': constants['phi'],
                'wp_sum': 0.0,
                'wn_sum': 0.0,
            },
            'D': {
                'indexes': {},
                'maxConfidence': constants['phi'],
                'wp_sum': 0.0,
                'wn_sum': 0.0,
            },
            'L': {
                'indexes': {},
                'maxConfidence': constants['phi'],
                'wp_sum': 0.0,
                'wn_sum': 0.0,
            },
        }
        self.hints[piece_id] = {
            'T': -1,
            'R': -1,
            'D': -1,
            'L': -1,
        }

    def updateNodesAndHints(self, first_piece_id, orient, second_piece_id, wp, wn):
        confidence = wp / (wp + wn)
        self.nodes[first_piece_id][orient]['indexes'][second_piece_id] = {
            'confidence': confidence,
            'wp': wp,
            'wn': wn,
        }
        self.nodes[first_piece_id][orient]['wp_sum'] += wp
        self.nodes[first_piece_id][orient]['wn_sum'] += wn
        if confidence > self.nodes[first_piece_id][orient]['maxConfidence']:
            self.hints[first_piece_id][orient] = second_piece_id
            self.nodes[first_piece_id][orient]['maxConfidence'] = confidence

    def checkUnsureHints(self):
        for first_piece_id in self.hints:
            for orient in self.hints[first_piece_id]:
                if self.hints[first_piece_id][orient] >= 0:
                    second_piece_id = self.hints[first_piece_id][orient]
                    unsure = False
                    for other_piece_id in self.nodes[first_piece_id][orient]['indexes']:
                        confidence = self.nodes[first_piece_id][orient]['indexes'][other_piece_id]['confidence']
                        maxConfidence = self.nodes[first_piece_id][orient]['maxConfidence']
                        if other_piece_id != second_piece_id and maxConfidence - confidence <= constants['epsilon']:
                            unsure = True
                    if unsure:
                        self.hints[first_piece_id][orient] = -1
                        self.nodes[first_piece_id][orient]['maxConfidence'] = constants['phi']
