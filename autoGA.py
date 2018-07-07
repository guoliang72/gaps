import subprocess
import json
import time

round_ids = [458, 452]
erase_edges = [2,3]
measure_weights = [True, False]
start_at = 0.2
repeat_time = 3
fitness_method = 'rank-based' #[rank-based, sigmoid]

result_map = {}

start_time = time.time()

print('GA for rounds: ', round_ids)

for round_id in round_ids:
	result_map[round_id] = {}
	for erase_edge in erase_edges:
		for measure_weight in measure_weights:
			if measure_weight:
				cmd = 'bin/gaps --roundid %d --fitness %s --use_pixel --measure_weight --hide_detail --erase_edge %d --start_at %f' % (round_id, fitness_method, erase_edge, start_at)
			else:
				cmd = 'bin/gaps --roundid %d --fitness %s --use_pixel --hide_detail --erase_edge %d --start_at %f' % (round_id, fitness_method, erase_edge, start_at)
			winner_time = 0.0
			GA_time = 0.0
			for i in range(repeat_time):
				gaps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
				retval = gaps.wait()
				lines = gaps.stdout.readlines()
				winner_time += float(str(lines[-1]).split(' ')[3][:-1])
				GA_time += float(str(lines[-1]).split(' ')[6][:-3])
				#print(winner_time, GA_time)
			winner_time = round(winner_time / 3, 3)
			GA_time = round(GA_time / 3, 3)
			key = 'erase_edge:%d,measure_weight:%s' % (erase_edge, str(measure_weight))
			result_map[round_id][key] = {
				'winner_time': winner_time,
				'GA_time': GA_time
			}
			print('round_id: %d, auto_time_cost_for_%d_times: %.3f, ' % (round_id, repeat_time, time.time() - start_time)\
				 + key + ', winner_time: %.3f, GA_time: %.3f' % (winner_time, GA_time))

pretty_result_file = open('autoGA_result_pretty.json', 'w')
pretty_result_file.write(json.dumps(result_map, indent=4))
pretty_result_file.close()

result_file = open('autoGA_result.json', 'w')
result_file.write(json.dumps(result_map))
result_file.close()