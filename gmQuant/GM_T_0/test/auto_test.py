from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *


class stockobj:
    """
        股票详细信息
    """

    def __init__(self, stock, state):
        self.stock = stock
        self.state = state

    def __repr__(self):
        return "stock: {}, stage: {}".format(self.stock, self.state)


def init(context):
    # 指定数据窗口大小为50
    print("---> 策略初始化 @ %s" % (str(context.now)))
    context.symbol = "SHSE.600000"
    context.freq = "60s"
    context.count = 50
    context.basestock_pool = []
    subscribe(symbols=context.symbol, frequency=context.freq, count=context.count)
def buy(context):
    print("%s 股票:\t%s 买入成功" % (context.now, context.basestock_pool[0].stock))
    order_volume(symbol=context.basestock_pool[0].stock, volume=100, side=OrderSide_Buy, order_type=OrderType_Market,
                 position_effect=PositionEffect_Open)

def sell(context):
    print("%s 股票:\t%s 卖出成功" % (context.now, context.basestock_pool[0].stock))
    order_volume(symbol=context.basestock_pool[0].stock, volume=100, side=OrderSide_Sell, order_type=OrderType_Market,
                 position_effect=PositionEffect_Open)



def on_execution_report(context, execrpt):
    if execrpt.exec_type == ExecType_Trade and execrpt.side == OrderSide_Buy:
        print("<--- %s 委托买入股票: %s, 交易量: %d, 成功" %
              (context.now, execrpt.symbol, execrpt.volume))
        context.basestock_pool[0].state = 1
        sell(context)
    elif execrpt.exec_type == ExecType_Trade and execrpt.side == OrderSide_Sell:
        print("---> %s 委托卖出股票: %s, 交易量: %d, 成功" %
              (context.now, execrpt.symbol, execrpt.volume))
        context.basestock_pool[0].state = 2


def on_bar(context, bars):

    if context.now.hour == 9 and context.now.minute == 33:
        s = stockobj(context.symbol, 0)
        context.basestock_pool.append(s)
        print(s)
    if len(context.basestock_pool) > 0:
        print("%s %s" % (context.now, context.basestock_pool[0]))
        if context.now.minute == 40:
            buy(context)




if __name__ == '__main__':
    run(strategy_id='1c61a610-fdfd-11e7-974a-00ffaabbccdd',
        filename='auto_test.py',
        mode=MODE_BACKTEST,
        token='f1b42b8ab54bb61010b685eac99765b28209c3e0',
        backtest_start_time='2017-06-19 09:00:00',
        backtest_end_time='2017-06-23 15:00:00')
