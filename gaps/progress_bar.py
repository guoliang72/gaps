# -*- coding: utf-8 -*-

import sys
import time
import datetime
from gaps.crowd.dbaccess import mongo_wrapper
from gaps.config import Config


def print_progress(iteration, total, prefix="", start_time = None, suffix="", decimals=1, bar_length=50):
    """ Call in a loop to create terminal progress bar"""
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = "\033[32m█\033[0m" * filled_length + "\033[31m-\033[0m" * (bar_length - filled_length)
    time_passed = str(datetime.timedelta(seconds=time.time()-start_time + mongo_wrapper.get_round_winner_time_milisecs() * Config.offline_start_percent / 1000))[:-3] \
                    if start_time is not None else 0

    sys.stdout.write("\r{0: <16} [{1}] {2} {3}/{4} {5}{6} {7}".format(prefix, time_passed, bar, iteration, total, percents, "%", suffix))

    if iteration == total:
        sys.stdout.write("\n")
    sys.stdout.flush()
