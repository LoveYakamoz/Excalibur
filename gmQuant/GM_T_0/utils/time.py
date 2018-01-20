# 计算当前时间点，是开市以来第几分钟
def get_minute_count(current_dt):
    '''
     9:30 -- 11:30
     13:00 --- 15:00
     '''
    current_hour = current_dt.hour
    current_min = current_dt.minute

    if current_hour < 12:
        minute_count = (current_hour - 9) * 60 + current_min - 30
    else:
        minute_count = (current_hour - 13) * 60 + current_min + 120

    return minute_count


def get_delta_minute(datetime1, datetime2):
    minute1 = get_minute_count(datetime1)
    minute2 = get_minute_count(datetime2)

    return abs(minute2 - minute1)