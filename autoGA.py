import subprocess
import json
import time

round_ids = [434, 439, \
	440, 441, 442, 443, 446, 447, 449, \
	450, 451, 452, 455, 457, 458, \
	460, 471, 472, 474, 475, 476, \
	481, 482, 483, 484, 485, 486, 489, \
	490, 494, 495]
start_at = 0.4
repeat_time = 4
fitness_method = 'rank-based' #[rank-based, sigmoid]

result_map = {}

start_time = time.time()

cmd_out_file = open('out.txt' ,'w')

print('GA for rounds: ', round_ids)
cmd_out_file.write('GA for rounds: ' + str(round_ids) + '\n')

for round_id in round_ids:
	result_map[round_id] = {}
	cmd = 'bin/gaps --roundid %d --fitness %s --hide_detail --start_at %f' % (round_id, fitness_method, start_at)
	min_winner_time = 100000.0
	min_GA_time = 100000.0
	for i in range(repeat_time):
		gaps = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		retval = gaps.wait()
		lines = gaps.stdout.readlines()
		winner_time = float(str(lines[-1]).split(' ')[3][:-1])
		if winner_time < min_winner_time:
			min_winner_time = winner_time
		GA_time = float(str(lines[-1]).split(' ')[6][:-3])
		if GA_time < min_GA_time:
			min_GA_time = GA_time
		#print(winner_time, GA_time)
	min_winner_time = round(min_winner_time, 3)
	min_GA_time = round(min_GA_time, 3)
	result_map[round_id] = {
		'winner_time': min_winner_time,
		'GA_time': min_GA_time
	}
	print('round_id: %d, auto_time_cost_for_%d_times: %.3f, ' % (round_id, repeat_time, time.time() - start_time)\
		+ ', winner_time: %.3f, GA_time: %.3f' % (min_winner_time, min_GA_time))
	cmd_out_file.write('round_id: %d, auto_time_cost_for_%d_times: %.3f, ' % (round_id, repeat_time, time.time() - start_time)\
		+ ', winner_time: %.3f, GA_time: %.3f' % (min_winner_time, min_GA_time) + '\n')

pretty_result_file = open('autoGA_result_pretty.json', 'w')
pretty_result_file.write(json.dumps(result_map, indent=4))
pretty_result_file.close()

result_file = open('autoGA_result.json', 'w')
result_file.write(json.dumps(result_map))
result_file.close()

cmd_out_file.close()