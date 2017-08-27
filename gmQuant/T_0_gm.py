from gmsdk.api import StrategyBase
from gmsdk.util import bar_to_dict
import re
import logging
import logging.handlers
import numpy as np
import pandas as pd
import talib as ta
from math import isnan

g_base_dir = "gmQuant\\"
LOG_FILE = g_base_dir + 'gmQuant.log'

handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=4 * 1024 * 1024, backupCount=5)
fmt = '%(asctime)s - %(filename)s:%(lineno)s - %(name)s - %(message)s'

formatter = logging.Formatter(fmt)
handler.setFormatter(formatter)

logger = logging.getLogger('GM')
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# 上穿及下穿阈值
g_up = 0.1
g_down = 3.9

# MA平均的天数
g_ma_day_count = 4

# 持仓股票池详细信息
g_basestock_pool = []

g_position_count = 1


class BaseStock(object):

    def __init__(self, stock, close, lowest, highest, operator_value):
        self.stock = stock
        self.close = close
        self.lowest_89 = lowest
        self.highest_233 = highest
        self.operator_value = operator_value

    def __repr__(self):
        return 'stock: {0}, close: {1}, lowest: {2}, hightest: {3}, operator_value: {4}'.format(self.stock, self.close, self.lowest, self.highest, self.operator_value)


class T_0_Strategy(StrategyBase):
    def __init__(self, *args, **kwargs):
        super(T_0_Strategy, self).__init__(*args, **kwargs)
        basestock = BaseStock("SHSE.600446", 0, None, None, 0)
        g_basestock_pool.append(basestock)
        logger.info("- ---> initialize")

    def get_current_hour(self, date_time):
        '''
        从2017-08-25T09:30:00+08:00抽取出hour
        '''
        matchObj = re.match(r'.*T(\d+):(\d+):(\d+).*', date_time, re.M | re.I)
        if matchObj:
            return int(matchObj.group(1))
        else:
            logger.error("Not find hour string")
            return 0

    def get_current_minute(self, date_time):
        '''
        从2017-08-25T09:30:00+08:00抽取出minute
        '''
        matchObj = re.match(r'.*T(\d+):(\d+):(\d+).*', date_time, re.M | re.I)
        if matchObj:
            return int(matchObj.group(2))
        else:
            logger.error("Not find minute string")
            return 0

    def get_minute_count(self, date_time):
        '''
        计算当前时间点，是开市以来第几分钟
        9:30 -- 11:30
        13:00 --- 15:00
        '''
        current_hour = self.get_current_hour(date_time)
        current_min = self.get_current_minute(date_time)

        if current_hour < 12:
            minute_count = (current_hour - 9) * 60 + current_min - 30
        else:
            minute_count = (current_hour - 13) * 60 + current_min + 120

        return minute_count

    def on_login(self):
        logger.info('logged in')

    def on_error(self, err_code, msg):
        #logger.error('get error: %s - %s' % (err_code, msg))
        pass

    def get_min_low(self, bars):
        min_low = 100000000

        for bar in bars:
            bar = bar_to_dict(bar)

            if bar['low'] < min_low:
                min_low = bar['low']

        return min_low

    def get_max_high(self, bars):
        max_high = 0

        for bar in bars:
            bar = bar_to_dict(bar)

            if bar['high'] > max_high:
                max_high = bar['high']

        return max_high

    def update_89_lowest(self, minute_count):
        if minute_count > 89:
            minute_count = 89
        for i in range(g_position_count):
            bars = self.get_last_n_bars(
                g_basestock_pool[i].stock, 60, minute_count, "")

            g_basestock_pool[i].lowest_89 = self.get_min_low(bars)

    def update_233_highest(self, minute_count):
        if minute_count > 233:
            minute_count = 233
        for i in range(g_position_count):
            bars = self.get_last_n_bars(
                g_basestock_pool[i].stock, 60, minute_count, "")
            g_basestock_pool[i].highest_233 = self.get_max_high(bars)

    def on_bar(self, bar):
        obj = bar_to_dict(bar)
        strtime = obj['strtime']

        logger.info("processing %s", strtime)

        hour = self.get_current_hour(strtime)
        minute = self.get_current_minute(strtime)

        # 14点45分钟后， 不再有新的交易
        if hour == 14 and minute >= 45:
            return
        minute_count = self.get_minute_count(strtime)
        # 因为要计算移动平均线，所以每天前g_ma_day_count分钟，不做交易
        if minute_count < g_ma_day_count:
            return

        # 更新89分钟内的最低收盘价，不足89分钟，则按到当前时间的最低收盘价
        self.update_89_lowest(minute_count)

        # 更新233分钟内的最高收盘价，不足233分钟，则按到当前时间的最高收盘价
        self.update_233_highest(minute_count)

        # 1. 循环股票列表，看当前价格是否有买入或卖出信号
        for i in range(g_position_count):
            stock = g_basestock_pool[i].stock

            if isnan(g_basestock_pool[i].lowest_89) is True:
                logger.error("stock: %s's lowest_89 is None", stock)
                continue
            else:
                lowest_89 = g_basestock_pool[i].lowest_89

            if isnan(g_basestock_pool[i].lowest_233) is True:
                logger.error("stock: %s's highest_233 is None", stock)
                continue
            else:
                highest_233 = g_basestock_pool[i].highest_233

            # 如果在开市前几分钟，价格不变化，则求突破线时，会出现除数为0，如果遇到这种情况，表示不会有突破，所以直接过掉
            if lowest_89 == highest_233:
                continue

            # 求取当前是否有突破
            last_n_dailybars = self.get_last_n_dailybars(stock, g_ma_day_count)

            close = [0.0] * g_ma_day_count

            j = 0
            for dailybar in last_n_dailybars:
                bar = bar_to_dict(dailybar)
                close[j] = bar['close']
                j += 1

            close = np.array(close).astype(float)

            for j in range(g_ma_day_count):
                close[j] = ((close[j] - lowest_89) * 1.0 /
                            (highest_233 - lowest_89)) * 4

            if close is not None:
                operator_line = ta.MA(close, g_ma_day_count)
            else:
                logger.warn("股票: %s 可能由于停牌等原因无法求解MA", stock)
                continue

            # 买入信号产生
            if g_basestock_pool[i].operator_value < g_up and operator_line[g_ma_day_count - 1] > g_up and g_basestock_pool[i].operator_value != 0.0:
                log.info("BUY SIGNAL for %s, from %f to %f, close_price: %f, lowest_89: %f, highest_233: %f",
                         stock, g_basestock_pool[i].operator_value, operator_line[g_ma_day_count - 1],
                         last_n_dailybars[g_ma_day_count - 1]['close'], lowest_89, highest_233)

            # 卖出信息产生
            elif g_basestock_pool[i].operator_value > g_down and operator_line[g_ma_day_count - 1] < g_down:
                log.info("SELL SIGNAL for %s, from %f to %f, close_price: %f, lowest_89: %f, highest_233: %f",
                         stock, g_basestock_pool[i].operator_value, operator_line[g_ma_day_count - 1],
                         last_n_dailybars[g_ma_day_count - 1]['close'], lowest_89, highest_233)

            # 记录当前操盘线值
            g_basestock_pool[i].operator_value = operator_line[g_ma_day_count - 1]


if __name__ == '__main__':
    ret = T_0_Strategy(
        username='18721037520',
        password='242613',
        strategy_id='strategy_2',
        subscribe_symbols='SHSE.600446.bar.60',
        mode=3
    ).run()

    #ret = T_0_Strategy(config_file='T_0_strategy.ini')
    print('exit code: %d' % ret)