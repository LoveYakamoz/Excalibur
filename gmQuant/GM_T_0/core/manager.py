"""
设置控制函数
"""
from __future__ import print_function, absolute_import, unicode_literals
from gm.api import *
import numpy as np

g.stock_id_list_from_client = ["002506.XSHE", "600703.XSHG", "300059.XSHE", "600206.XSHG",
                               "002281.XSHE", "600340.XSHG", "002092.XSHE", "002440.XSHE",
                               "600897.XSHG", "000063.XSHE"]
g.stock_position = {"002506.XSHE": 0,
                    "600703.XSHG": 0,
                    "300059.XSHE": 0,
                    "600206.XSHG": 0,
                    "002281.XSHE": 0,
                    "600340.XSHG": 0,
                    "002092.XSHE": 0,
                    "002440.XSHE": 0,
                    "600897.XSHG": 0,
                    "000063.XSHE": 0}
"""
g.stock_id_list_from_client = ["600206.XSHG"]
g.stock_position = {
    "600206.XSHG": 0,
}
"""
# 持仓股票池详细信息
g.basestock_pool = []

# 用于统计结果
g.repeat_signal_count = 0
g.reset_order_count = 0
g.success_count = 0

# 每次调整的比例
g.adjust_scale = 0.25

# 期望收益率
g.expected_revenue = 0.010

g.sampleSize = 20  # 20 or 30
g.scale = 1.5  # 倍数1.0-5倍
g.signal_buy_dict = {}

g.t_0 = T_0.Open  # 如果只看持仓收益，将其置为T_0.close

# 时间差止损，如果设置大于240， 意味着不使用时间差止损
DELTA_MINITE = 10000

# 价格差止损，如果设置大于0.1， 意味着不使用价格差止损
DELTA_PRICE = 0.020

def algo(context):
    # 购买100股浦发银行股票
    order_volume(symbol='SHSE.600000', volume=100, side=OrderSide_Buy, order_type=OrderType_Market,
                 position_effect=PositionEffect_Open, price=0)
def init(context):
    log.info("---> 策略初始化 @ %s" % (str(context.current_dt)))
    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0

    # 第一天运行时，需要选股入池，并且当天不可进行股票交易
    g.firstrun = True

    # 默认股票池容量
    g.position_count = 30
    get_stocks_by_client()

    # 设置基准
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info("初始化完成")
    schedule(schedule_func=algo, date_rule='1d', time_rule='14:50:00')

# 在每天交易开始时，将状态置为可交易状态
def before_trading_start(context):
    log.info("初始化买卖状态为INIT")
    for s in g.basestock_pool:
        s.clearup()

    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0


def update_socket_statue(context):
    """
    每一bar，更新股票的状态
    :param context:
    :return:
    """
    orders = get_orders()
    if len(orders) == 0:
        return
    hour = context.current_dt.hour

    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        sell_order_id = g.basestock_pool[i].sell_order_id
        buy_order_id = g.basestock_pool[i].buy_order_id
        status = g.basestock_pool[i].status
        if (status == Status.WORKING) and ((sell_order_id != -1) and (buy_order_id != -1)):
            sell_order = orders.get(sell_order_id)
            buy_order = orders.get(buy_order_id)
            if (sell_order is not None) and (buy_order is not None):
                if sell_order.status == OrderStatus.held and buy_order.status == OrderStatus.held:
                    if g.basestock_pool[i].t_0_type == Type.Active_Buy:
                        g.basestock_pool[i].end_time = context.current_dt

                        log.info("T_0 ：【先买后卖成功】股票: {}, 在{}以 {} 价格买入 {} 股，然后在{}以 {} 价格卖出 {} 股, 盈利 {} 元"
                                 .format(stock, g.basestock_pool[i].start_time, g.basestock_pool[i].buy_price, abs(g.basestock_pool[i].delay_amount),
                                         g.basestock_pool[i].end_time, g.basestock_pool[i].delay_price, abs(g.basestock_pool[i].delay_amount),
                                 (g.basestock_pool[i].delay_price - g.basestock_pool[i].buy_price) * abs(
                                     g.basestock_pool[i].delay_amount))
                                 )
                    else:
                        pass
                    g.basestock_pool[i].clearup()

                    g.success_count += 1

        # 每天14点后， 不再进行新的买卖
        if hour == 14 and g.basestock_pool[i].status == Status.INIT:
            g.basestock_pool[i].status = Status.NONE

    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        sell_order_id = g.basestock_pool[i].sell_order_id
        buy_order_id = g.basestock_pool[i].buy_order_id
        status = g.basestock_pool[i].status
        # 买完再卖
        if (status == Status.WORKING) and (sell_order_id == -1):
            buy_order = orders.get(buy_order_id)
            if (buy_order is not None):
                if buy_order.status == OrderStatus.held:
                    flag = sell_stock(stock, g.basestock_pool[i].delay_amount, g.basestock_pool[i].delay_price, i)
                    log.info("买完再卖: stock %s, delay_amount: %d, flag = %d", stock, g.basestock_pool[i].delay_amount,
                             flag)

        if (status == Status.WORKING) and (sell_order_id != -1) and (sell_order.status != OrderStatus.held):

            cur_close = get_price(stock, count=1, end_date=str(context.current_dt), frequency='1m',
                                  fields=['close']).iat[0, 0]
            """
            价差卖出止损
            """
            if (g.basestock_pool[i].buy_price - cur_close) / cur_close >= DELTA_PRICE:
                cancel_order(sell_order_id)
                _order = order(stock, g.basestock_pool[i].delay_amount, MarketOrderStyle())

                if (_order is not None):
                    g.basestock_pool[i].sell_order_id = _order.order_id
                    g.basestock_pool[i].sell_price = cur_close
                    g.basestock_pool[i].end_time = context.current_dt
                    log.info("T_0 : 【价差止损成功】股票: {}, 在{}以 {} 价格买入 {} 股，然后在{}以 {} 价格卖出 {} 股, 盈利 {} 元"
                             .format(g.basestock_pool[i].stock, g.basestock_pool[i].start_time, g.basestock_pool[i].buy_price,
                             abs(g.basestock_pool[i].delay_amount), g.basestock_pool[i].end_time, cur_close, abs(g.basestock_pool[i].delay_amount),
                             (-1) * abs(g.basestock_pool[i].buy_price - cur_close) * abs(
                                 g.basestock_pool[i].delay_amount))
                             )
                    g.basestock_pool[i].clearup()
                    continue
                else:
                    log.error("T_0 : 【价差止损成功】股票: %s, 进行止损失败", g.basestock_pool[i].stock)
            """
            时差止损
            """
            if get_delta_minute(context.current_dt, g.basestock_pool[i].start_time) > DELTA_MINITE:
                cancel_order(sell_order_id)
                _order = order(stock, g.basestock_pool[i].delay_amount, MarketOrderStyle())


                if (_order is not None):
                    g.basestock_pool[i].sell_order_id = _order.order_id
                    g.basestock_pool[i].sell_price = cur_close
                    g.basestock_pool[i].end_time = context.current_dt
                    log.info("T_0 : 【时差止损成功】股票: {}, 在{}以 {} 价格买入 {} 股，然后在{}以 {} 价格卖出 {} 股, 盈利 {} 元"
                             .format(g.basestock_pool[i].stock, g.basestock_pool[i].start_time, g.basestock_pool[i].buy_price,
                             abs(g.basestock_pool[i].delay_amount), g.basestock_pool[i].end_time, cur_close, abs(g.basestock_pool[i].delay_amount),
                             (cur_close - g.basestock_pool[i].buy_price) * abs(
                                 g.basestock_pool[i].delay_amount))
                             )
                    g.basestock_pool[i].clearup()
                    continue

def handle_data(context, data):
    if str(context.run_params.start_date) == str(context.current_dt.strftime("%Y-%m-%d")):
        if g.firstrun is True:
            for s in g.basestock_pool:
                myorder = order_value(s.stock, 100000)

                if myorder is not None:
                    s.position = myorder.amount
                else:
                    log.error("股票:\t%s 买入失败", s.stock)
            log.info("====================================================================")
            for s in g.basestock_pool:
                log.info(s)
            g.firstrun = False
        return

    if g.t_0 == T_0.Close:
        """
        关闭T_0，只测试持仓收益
        """
        return
    hour = context.current_dt.hour
    minute = context.current_dt.minute

    # 每天14点55分钟 将未完成的订单强制恢复到原有持仓量
    if hour == 14 and minute == 55:
        cancel_open_order(context)
        reset_position(context)
        return

    if hour == 14 and minute > 55:
        return

    update_socket_statue(context)

    # 14点00分钟后， 不再有新的交易
    if hour == 14 and minute >= 40:
        return
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        if g.basestock_pool[i].status == Status.NONE:
            continue

        count_number = g.sampleSize * 2
        df = get_price(stock, count=count_number, end_date=str(context.current_dt), frequency='1m',
                       fields=['close', 'volume'])
        np_close = []
        vol = []

        for k in range(count_number):
            np_close.append(df.iat[k, 0])
            vol.append(df.iat[k, 1])

        evaluate_activeVolBuy(np.array(np_close), np.array(vol))

        # 买入信号产生
        if g.signal_buy_dict['signal_netVol_buySell'] == 1:
            buy_signal(context, stock, np_close[count_number - 1], i)
            g.signal_buy_dict['signal_netVol_buySell'] = 0
        else:
            pass

def on_backtest_finished(context, indicator):
    g.t_0 = T_0.Open

    log.info("===========================================================================")
    log.info("[统计数据]成功交易次数:\t%d, 重复信号交易次数:\t%d, 收盘前强制交易次数:\t%d", g.success_count, g.repeat_signal_count,
             g.reset_order_count)
    log.info("===========================================================================")

    for k, v in indicator.items():
        print(k, v)