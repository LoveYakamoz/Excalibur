from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *


def init(context):
    # 指定数据窗口大小为50
    subscribe(symbols='SHSE.600001', frequency='1d', count=50)


def on_bar(context, bars):
    # 打印频率为一天的浦发银行的50条最新bar的收盘价和bar开始时间
    print(context.data(symbol='SHSE.600000', frequency='1d', count=50,
                       fields='close,bob'))


if __name__ == '__main__':
    run(strategy_id='1c61a610-fdfd-11e7-974a-00ffaabbccdd', filename='auto_test.py', mode=MODE_BACKTEST,
        token='f1b42b8ab54bb61010b685eac99765b28209c3e0',
        backtest_start_time='2016-06-17 13:00:00', backtest_end_time='2017-08-21 15:00:00')
