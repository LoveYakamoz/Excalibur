from enum import Enum

from jqdata import *
import numpy as np
import pandas as pd
import talib as ta
from math import isnan, floor
from math import atan
import tushare as ts


class Status(Enum):
    INIT = 0  # 在每天交易开始时，置为INIT
    WORKING = 1  # 处于买/卖中
    NONE = 2  # 今天不再做任何交易


class Type(Enum):
    Active_Buy = "主动买入"
    Active_Sell = "主动卖出"
    NONE = "无"


class T_0(Enum):
    """
    T_0是否打开
    """
    Open = 1
    Close = 2



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

class BaseStock(object):
    """
    股票详细信息
    """

    def __init__(self, stock, close, status, position, sell_order_id, buy_order_id, type):
        self.stock = stock
        self.close = close

        self.status = status
        self.position = position
        self.sell_order_id = sell_order_id
        self.sell_price = 0.0
        self.buy_order_id = buy_order_id
        self.buy_price = 0.0

        self.delay_amount = 0  # 反向挂单量
        self.delay_price = 0.0  # 反向挂单价格
        self.t_0_type = type  # t+0的类型

        self.start_time = None
        self.end_time = None

    def __repr__(self):
        return "stock: {}, close: {}, position: {}, sell_order_id: {}, buy_order_id: {}, t_0_type: {}".format(
            self.stock, self.close, self.position, self.sell_order_id, self.buy_order_id, self.t_0_type)

    def clearup(self):
        self.status = Status.INIT
        self.sell_order_id = -1
        self.sell_price = 0.0
        self.buy_order_id = -1
        self.buy_price = 0.0
        self.delay_amount = 0
        self.delay_price = 0.0
        self.t_0_type = Type.NONE
        self.start_time = None
        self.end_time = None
        log.info("clearup %s", self.stock)


def get_stocks_by_client():
    """
    直接从客户得到股票列表
    :param context:
    :return:
    """
    select_count = 0
    for stock_id in g.stock_id_list_from_client:
        stock_obj = BaseStock(stock_id, 0, Status.INIT, g.stock_position[stock_id], -1, -1, Type.NONE)
        print(stock_obj)

        g.basestock_pool.append(stock_obj)
        select_count += 1

    if select_count < g.position_count:
        g.position_count = select_count


def evaluate_activeVolBuy(np_close, vol):
    """
    主动性买盘成交量
    :param np_close:  3~4 sampleSize
    :param vol:
    :return:
    """
    diff_a1 = np.diff(np_close)
    comp_vol = vol[1:]
    activeVolBuy = []
    activeVolSell = []
    swingVol = []
    accumulateNetVol = 0
    netVol_buySell = []

    for i in range(len(diff_a1)):
        if diff_a1[i] > 0:
            activeVolBuy.append(comp_vol[i])
            activeVolSell.append(0)
        elif diff_a1[i] < 0:
            activeVolSell.append(comp_vol[i])
            activeVolBuy.append(0)
        else:
            swingVol.append(comp_vol[i])
            activeVolBuy.append(0)
            activeVolSell.append(0)

    for k in range(len(activeVolBuy)):
        netVol = activeVolBuy[k] - activeVolSell[k]
        accumulateNetVol += netVol
        netVol_buySell.append(float(accumulateNetVol))

    netVol_buySell_sum = np.sum(np.array(activeVolBuy)) - np.sum(np.array(activeVolSell))

    threshold_netVol = np.average(netVol_buySell[-g.sampleSize:])
    # print('netVol_buySell_sum=%d, threshold_netvol=%d' % (netVol_buySell_sum, threshold_netVol))
    if netVol_buySell[-1] > 0 and netVol_buySell_sum > 0 and netVol_buySell[-1] > (threshold_netVol * g.scale):
        g.signal_buy_dict['signal_netVol_buySell'] = 1

    elif netVol_buySell[-1] < 0 and threshold_netVol < 0 and abs(netVol_buySell[-1]) > (
                abs(threshold_netVol) * g.scale):
        g.signal_buy_dict['signal_netVol_buySell'] = -1
    else:
        g.signal_buy_dict['signal_netVol_buySell'] = 0

    return activeVolBuy, activeVolSell, netVol_buySell


def initialize(context):
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


# 在每天交易开始时，将状态置为可交易状态
def before_trading_start(context):
    log.info("初始化买卖状态为INIT")
    for s in g.basestock_pool:
        s.clearup()

    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0


def buy_stock(stock, amount, limit_price, index):
    """
    购买股票，并记录订单号，便于查询订单状态
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    buy_order = order(stock, amount, LimitOrderStyle(limit_price))
    if buy_order is not None:
        g.basestock_pool[index].buy_order_id = buy_order.order_id
        g.basestock_pool[index].buy_price = limit_price
        log.info("股票: %s, 以%f价格挂单，买入%d", stock, limit_price, amount)
        return True
    else:
        g.basestock_pool[index].buy_price = 0
        return False


def sell_stock(stock, amount, limit_price, index):
    """
    卖出股票，并记录订单号，便于查询订单状态
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    sell_order = order(stock, amount, LimitOrderStyle(limit_price))

    if sell_order is not None:
        g.basestock_pool[index].sell_order_id = sell_order.order_id
        g.basestock_pool[index].sell_price = limit_price
        log.info("股票: %s, 以%f价格挂单，卖出%d", stock, limit_price, amount)
        return True
    else:
        g.basestock_pool[index].sell_price = 0
        return False


def sell_signal(context, stock, close_price, index):
    if g.basestock_pool[index].status == Status.WORKING:
        log.warn(" 股票: %s, 收到重复卖出信号，但不做交易", stock)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = g.adjust_scale * g.basestock_pool[index].position

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01
    log.info(" sell scale: %f, src_posiont: %d, amount: %d, price: %f", g.adjust_scale,
             g.basestock_pool[index].position, amount, limit_price)

    if g.basestock_pool[index].status == Status.INIT:
        flag = sell_stock(stock, -amount, limit_price, index)
        if (False == flag):
            return

        # 以收盘价 - 价差 * expected_revenue 挂单买入
        yesterday = get_price(stock, count=1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
        limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue
        g.basestock_pool[index].t_0_type = Type.Active_Sell
        g.basestock_pool[index].delay_amount = amount
        g.basestock_pool[index].delay_price = limit_price
        g.basestock_pool[index].status = Status.WORKING  # 更新交易状态
    else:
        log.error("股票: %s, 交易状态出错", stock)


def buy_signal(context, stock, close_price, index):
    if g.basestock_pool[index].status == Status.WORKING:
        log.warn(" 股票: %s, 收到重复买入信号，但不做交易", stock)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = floor(g.adjust_scale * g.basestock_pool[index].position)

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    log.info("buy scale: %f, src_posiont: %d, amount: %d, price: %f", g.adjust_scale,
             g.basestock_pool[index].position,
             amount, limit_price)

    if g.basestock_pool[index].status == Status.INIT:
        flag = buy_stock(stock, amount, limit_price, index)
        if (False == flag):
            return

        # 以收盘价 + 价差 * expected_revenue 挂单卖出
        yesterday = get_price(stock, count=1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
        limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue
        g.basestock_pool[index].t_0_type = Type.Active_Buy
        g.basestock_pool[index].delay_amount = -amount
        g.basestock_pool[index].delay_price = limit_price
        g.basestock_pool[index].status = Status.WORKING  # 更新交易状态
        g.basestock_pool[index].start_time = context.current_dt

    else:
        log.error("股票: %s, 交易状态出错", stock)


def cancel_open_order(context):
    """
    取消所有未完成的订单（未撮合成的订单）
    :param context:
    :return:
    """
    orders = get_open_orders()
    for _order in orders.values():
        cancel_order(_order)


def reset_position(context):
    """
    恢复所有股票到原有仓位
    :param context:
    :return:
    """
    for s in g.basestock_pool:
        stock = s.stock
        src_position = s.position
        cur_position = context.portfolio.positions[stock].total_amount
        if src_position != cur_position:
            order(stock, src_position - cur_position)
            cur_close = get_price(stock, count=1, end_date=str(context.current_dt), frequency='1m',
                                  fields=['close']).iat[0, 0]
            delta_pos = abs(src_position - cur_position)
            if s.t_0_type == Type.Active_Buy:
                log.info("T_0 ：【先买后卖失败】股票: %s, 恢复仓位: %d, 盈利: %f元", stock, delta_pos,
                         (-1) * abs(cur_close - s.buy_price) * delta_pos)
            elif s.t_0_type == Type.Active_Sell:
                log.info("T_0 ：【先卖后买失败】股票: %s, 恢复仓位: %d, 盈利: %f元", stock, delta_pos,
                         (-1) * abs(cur_close - s.sell_price) * delta_pos)
            else:
                pass
            g.reset_order_count += 1


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


def after_trading_end(context):
    g.t_0 = T_0.Open

    log.info("===========================================================================")
    log.info("[统计数据]成功交易次数:\t%d, 重复信号交易次数:\t%d, 收盘前强制交易次数:\t%d", g.success_count, g.repeat_signal_count,
             g.reset_order_count)
    log.info("===========================================================================")
