from gm.api import *

from gmQuant.GM_T_0.model.BaseStock import Status, T_0, BaseStock, Type, MAX_STOCK_COUNT
from gmQuant.GM_T_0.strategy.buy_sell import buy_signal, sell_stock
from gmQuant.GM_T_0.strategy.signal_generator import evaluate_activeVolBuy, g_signal_buy_dict

g_stock_id_list_from_client = ["SHSE.600000"]
g_stock_position = {"SHSE.600000": 100}

# 时间差止损，如果设置大于240， 意味着不使用时间差止损
DELTA_MINITE = 10000

# 价格差止损，如果设置大于0.1， 意味着不使用价格差止损
DELTA_PRICE = 0.020

g_first_run = True


def get_stocks_by_client(context):
    """
    直接从客户得到股票列表
    """
    select_count = 0
    for stock_id in g_stock_id_list_from_client:
        stock_obj = BaseStock(stock_id, 0, Status.INIT, g_stock_position[stock_id], -1, -1, Type.NONE)
        print(stock_obj)
        subscribe(symbols=stock_id, frequency='1m')
        context.basestock_pool.append(stock_obj)
        select_count += 1

    if select_count < MAX_STOCK_COUNT:
        context.position_count = select_count
    else:
        context.position_count = MAX_STOCK_COUNT


def init(context):
    print("---> 策略初始化 @ %s" % (str(context.now)))
    schedule(schedule_func=before_trading, date_rule='1d', time_rule="09:20:00")
    schedule(schedule_func=after_trading, date_rule='1d', time_rule="15:30:00")
    context.symbol = "SHSE.600000"
    context.freq = "60s"
    context.count = 50
    context.basestock_pool = []
    subscribe(symbols=context.symbol, frequency=context.freq, count=context.count)
    context.first_run = True
    context.T_0 = T_0.Open  # 如果只看持仓收益，将其置为T_0.close

    context.repeat_signal_count = 0
    context.reset_order_count = 0
    context.success_count = 0

    # 每次调整的比例
    context.adjust_scale = 0.25

    # 期望收益率
    context.expected_revenue = 0.010

    context.lastday = ""
    context.today = ""
    get_stocks_by_client(context)
    print("策略初始化完成")


# 在每天交易开始时，将状态置为可交易状态
def before_trading(context):
    for s in context.basestock_pool:
        s.cleanup()

    context.repeat_signal_count = 0
    context.reset_order_count = 0
    context.success_count = 0

    print("每日初始化")


def on_bar(context, bars):
    context.today = bars[0].bob.strftime('%Y-%m-%d')
    if context.T_0 == T_0.Close:
        """
        关闭T_0，只测试持仓收益
        """
        print("close T_0")
        return

    if context.first_run is True:
        for s in context.basestock_pool:
            order_volume(symbol=s.stock, volume=100, side=OrderSide_Buy, order_type=OrderType_Market,
                         position_effect=PositionEffect_Open)
            print("股票:\t%s 买入成功" % s.stock)
        print("===========================================================================")

        context.first_run = False
        return

    if context.lastday is "":
        return
    hour = context.now.hour
    minute = context.now.minute

    # 14点00分钟后， 不再有新的交易
    if hour == 14 and minute >= 40:
        return
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号

    for s in context.basestock_pool:
        # 每天14点后， 不再进行新的买卖
        if hour == 14 and s.status == Status.INIT:
            s.status = Status.NONE

        if s.status == Status.NONE:
            continue

        count_number = context.count
        if count_number > context.count:
            print("context.count: %d, current count: %d" % (context.count, count_number))
            count_number = context.count

        df = context.data(symbol=s.stock, frequency='60s',
                          count=count_number, fields='close, volume')

        np_close = []
        vol = []

        for k in range(count_number):
            np_close.append(df.iat[k, 0])
            vol.append(df.iat[k, 1])

        evaluate_activeVolBuy(np_close, vol)

        if g_signal_buy_dict['signal_netVol_buySell'] == 1:
            buy_signal(context, s.stock, np_close[count_number - 1], 0)
            g_signal_buy_dict['signal_netVol_buySell'] = 0
"""
def on_order_status(context, order):

    委托状态更新事件
    :param order:
    :param context:
    :return:


    if order.status == OrderStatus_Filled and order.side == OrderSide_Buy:
        print("T_0: [买完再卖] %s 委托买入股票: %s, 交易量: %d, 成功" %
              (context.now, order.symbol, order.volume))
        sell_stock(context, order.symbol, order.volume, context.basestock_pool[0].delay_price, 0)
    elif order.status == OrderStatus_Filled and order.side == OrderSide_Sell:
        context.success_count += 1
        context.basestock_pool[0].status = Status.INIT
        print("T_0: [先买后卖成功] %s 委托卖出股票: %s, 交易量: %d, 成功" %
              (context.now, order.symbol, order.volume))
"""
def on_execution_report(context, execrpt):
    if execrpt.exec_type == ExecType_Trade and execrpt.side == OrderSide_Buy:
        print("T_0: [买完再卖] %s 委托买入股票: %s, 交易量: %d, 委托成交价格:%f, 成功" %
              (context.now, execrpt.symbol, execrpt.volume, execrpt.price))
        sell_stock(context, execrpt.symbol, execrpt.volume, context.basestock_pool[0].delay_price, 0)
    elif execrpt.exec_type == ExecType_Trade and execrpt.side == OrderSide_Sell:
        context.success_count += 1
        context.basestock_pool[0].status = Status.INIT
        print("T_0: [先买后卖成功] %s 委托卖出股票: %s, 交易量: %d, 委托成交价格:%f, 成功" %
              (context.now, execrpt.symbol, execrpt.volume, execrpt.price))


def after_trading(context):
    context.T_0 = T_0.Open

    print("===========================================================================")
    print("[统计数据]成功交易次数:\t%d, 重复信号交易次数:\t%d, 收盘前强制交易次数:\t%d" %
          (context.success_count, context.repeat_signal_count, context.reset_order_count))
    print("===========================================================================")
    context.lastday = context.now.strftime('%Y-%m-%d')


if __name__ == '__main__':
    run(strategy_id='1c61a610-fdfd-11e7-974a-00ffaabbccdd',
        filename='manager.py',
        mode=MODE_BACKTEST,
        token='f1b42b8ab54bb61010b685eac99765b28209c3e0',
        backtest_start_time='2017-06-19 09:00:00',
        backtest_end_time='2017-06-23 15:00:00')




