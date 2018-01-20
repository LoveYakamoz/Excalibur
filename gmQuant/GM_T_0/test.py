# coding=utf-8
from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *


def init(context):
    schedule(schedule_func=algo, date_rule='1d', time_rule='14:50:00')


def algo(context):
    # 购买100股浦发银行股票
    order_volume(symbol='SHSE.600000', volume=100, side=OrderSide_Buy, order_type=OrderType_Market,
                 position_effect=PositionEffect_Open, price=0)

def on_backtest_finished(context, indicator):
    for k, v in indicator.items():
        print(k, v)
if __name__ == '__main__':
    run(strategy_id='1c61a610-fdfd-11e7-974a-00ffaabbccdd', filename='test.py', mode=MODE_BACKTEST, token='f1b42b8ab54bb61010b685eac99765b28209c3e0',
        backtest_start_time='2016-06-17 13:00:00', backtest_end_time='2017-08-21 15:00:00')
