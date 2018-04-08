import time
import datetime

def get_formatted_date(secs = None):
	secs = secs or time.time()
	date = time.localtime(secs)
	ms = int((secs - time.mktime(date)) * 1000)
	formatted_date = str(date.tm_year) + '-' + \
					 '{:02d}'.format(date.tm_mon) + '-' + \
					 '{:02d}'.format(date.tm_mday) + ' ' + \
					 '{:02d}'.format(date.tm_hour) + ':' + \
					 '{:02d}'.format(date.tm_min) + ':' + \
					 '{:02d}'.format(date.tm_sec) + ':' + \
					 '{:03d}'.format(ms).rstrip('0')
	return formatted_date
 
def cvt_to_secs(formatted_date):
	tmp = formatted_date.split()
	year, month, day = map(lambda x: int(x), tmp[0].split('-'))
	hour, minute, second, ms = map(lambda x:int(x), tmp[1].split(':'))
	dt = datetime.datetime(year, month, day, hour, minute, second)
	secs = float(time.mktime(dt.timetuple()))
	secs += ms / 1000.0
	return secs