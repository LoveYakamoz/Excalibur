from jqdata import *
import numpy as np
import pandas as pd
import talib as ta
from math import isnan, floor
from math import atan
import tushare as ts
try:
    import shipane_sdk
except:
    pass

# 股票池来源
class Source(Enum):
    AUTO = 0  # 程序根据波动率及股价自动从沪深300中获取股票
    CLIENT = 1  # 使用用户提供的股票


g.stocks_source = Source.CLIENT  # 默认使用自动的方法获得股票

g.stock_id_list_from_client = ["300059.XSHE", "600206.XSHE"]
g.stock_position = {"300059.XSHE": 100,
                    "600206.XSHG": 100}

# 持仓股票池详细信息
g.basestock_pool = []

# 用于统计结果
g.repeat_signal_count = 0
g.reset_order_count = 0
g.success_count = 0

# MA平均的天数
g.ma_4day_count = 4
g.ma_13day_count = 13

# 每次调整的比例
g.adjust_scale = 0.25

# 期望收益率
g.expected_revenue = 0.003

# 角度阈值
g.angle_threshold = 30


class Angle(Enum):
    UP = 1  # 角度>30
    MIDDLE = 0  # 角度<=30 且 角度>=-30
    DOWN = -1  # 角度<-30


class Status(Enum):
    INIT = 0  # 在每天交易开始时，置为INIT
    WORKING = 1  # 处于买/卖中
    NONE = 2  # 今天不再做任何交易


class Break(Enum):
    UP = 0  # 上穿
    DOWN = 1  # 下穿
    NONE = 2


'''
    记录股票详细信息
'''


class BaseStock(object):
    def __init__(self, stock, close, min_vol, max_vol, lowest, highest, status, position, sell_order_id, buy_order_id):
        self.stock = stock
        self.close = close
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.lowest = lowest
        self.highest = highest

        self.status = status
        self.position = position
        self.sell_order_id = sell_order_id
        self.sell_price = 0
        self.buy_order_id = buy_order_id
        self.buy_price = 0

        self.break_throught_type = Break.NONE  # 突破类型 up or down
        self.break_throught_time = None  # 突破时间点
        self.delay_amount = 0  # 反向挂单量
        self.delay_price = 0  # 反向挂单价格
        self.operator_value_4 = 0
        self.operator_value_13 = 0
        self.angle = 1000

    def print_stock(self):
        log.info(
            "stock: %s, close: %f, min_vol: %f, max_vol: %f, lowest: %f, hightest: %f, position: %f, sell_roder_id: %d, buy_order_id: %d, operator_value_4: %f, operator_value_13: %f"
            , self.stock, self.close, self.min_vol, self.max_vol, self.lowest, self.highest, self.position,
            self.sell_order_id, self.buy_order_id, self.operator_value_4, self.operator_value_13)


def get_stocks_by_client(context):
    '''
    直接从客户得到股票列表
    '''
    select_count = 0
    for stock_id in g.stock_id_list_from_client:
        stock_obj = BaseStock(stock_id, 0, 0, 0, 0, 0, Status.INIT, g.stock_position[stock_id], -1, -1)
        stock_obj.print_stock()

        g.basestock_pool.append(stock_obj)
        select_count += 1

    if select_count < g.position_count:
        g.position_count = select_count


def get_stock_angle(context, stock):
    '''ATAN(（五日收盘价均线值/昨日的五日收盘均线值-1）*100）*57.3'''

    df_close = get_price(stock, count=6, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    close_list = [item for item in df_close['close']]

    yesterday_5MA = (reduce(lambda x, y: x + y, close_list) - close_list[5]) / 5
    today_5MA = (reduce(lambda x, y: x + y, close_list) - close_list[0]) / 5
    angle = math.atan((today_5MA / yesterday_5MA - 1) * 100) * 57.3
    log.info("股票：%s的角度为：%f", stock, angle)
    return angle


def initialize(context):
    log.info("---> 策略初始化 @ %s" % (str(context.current_dt)))
    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0
    # 第一天运行时，需要选股入池，并且当天不可进行股票交易
    g.firstrun = True

    # 默认股票池容量
    g.position_count = 30

    if g.stocks_source == Source.AUTO:
        log.info("程序根据波动率及股价自动从沪深300中获取股票")
        get_stocks_by_vol(context)

    elif g.stocks_source == Source.CLIENT:
        log.info("使用用户提供的股票")
        get_stocks_by_client(context)
    else:
        log.error("未提供获得股票方法！！！")

    # 设置基准
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    log.info("初始化完成")

    g.__manager = shipane_sdk.JoinQuantStrategyManagerFactory(context).create('manager-1')

# 在每天交易开始时，将状态置为可交易状态
def before_trading_start(context):
    log.info("初始化买卖状态为INIT")
    for i in range(g.position_count):
        g.basestock_pool[i].status = Status.INIT
        g.basestock_pool[i].lowest = 0
        g.basestock_pool[i].highest = 0
        g.basestock_pool[i].status = Status.INIT

        g.basestock_pool[i].sell_order_id = -1
        g.basestock_pool[i].sell_price = 0
        g.basestock_pool[i].buy_order_id = -1
        g.basestock_pool[i].buy_price = 0

        g.basestock_pool[i].break_throught_time = None
        g.basestock_pool[i].delay_amount = 0
        g.basestock_pool[i].delay_price = 0
        angle = get_stock_angle(context, g.basestock_pool[i].stock)
        if angle > 30:
            g.basestock_pool[i].angle = Angle.UP
        elif angle < -30:
            g.basestock_pool[i].angle = Angle.DOWN
        else:
            g.basestock_pool[i].angle = Angle.MIDDLE

    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0


# 购买股票，并记录订单号，便于查询订单状态
def buy_stock(context, stock, amount, limit_price, index):
    buy_order = order(stock, amount, LimitOrderStyle(limit_price))
    g.basestock_pool[index].buy_price = limit_price
    if buy_order is not None:
        g.basestock_pool[index].buy_order_id = buy_order.order_id
        log.info("股票: %s, 以%f价格挂单，买入%d", stock, limit_price, amount)
        try:
            g.__manager.execute(buy_order)
            log.info('实盘易买股挂单成功:' + str(buy_order))
        except:
            log.info('实盘易买股挂单失败:' + str(buy_order))


# 卖出股票，并记录订单号，便于查询订单状态
def sell_stock(context, stock, amount, limit_price, index):
    sell_order = order(stock, amount, LimitOrderStyle(limit_price))
    g.basestock_pool[index].sell_price = limit_price
    if sell_order is not None:
        g.basestock_pool[index].sell_order_id = sell_order.order_id
        log.info("股票: %s, 以%f价格挂单，卖出%d", stock, limit_price, amount)
        try:
            g.__manager.execute(sell_order)
            log.info('实盘易卖股挂单成功:' + str(sell_order))
        except:
            log.info('实盘易卖股挂单失败:' + str(sell_order))

def sell_signal(context, stock, close_price, index):
    # 每次交易量为持仓量的g.adjust_scale
    amount = g.adjust_scale * g.basestock_pool[index].position
    log.info("sell scale: %f, src_posiont: %d, amount: %d", g.adjust_scale, g.basestock_pool[index].position, amount)
    
    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount = amount - (amount % 100)
    

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01

    if g.basestock_pool[index].status == Status.WORKING:
        log.warn("股票: %s, 收到重复卖出信号，但不做交易", stock)
    elif g.basestock_pool[index].status == Status.INIT:
        if g.basestock_pool[index].angle == Angle.UP:
            log.warn("股票：%s, 角度大于30， 忽略卖出信号", stock)
            return
        sell_ret = sell_stock(context, stock, -amount, limit_price, index)
        if g.basestock_pool[index].sell_order_id != -1:
            g.basestock_pool[index].break_throught_time = context.current_dt
            # 以收盘价 - 价差 * expected_revenue 挂单买入
            yesterday = get_price(stock, count=1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
            limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue

            g.basestock_pool[index].delay_amount = amount
            g.basestock_pool[index].delay_price = limit_price
            g.basestock_pool[index].break_throught_type = Break.DOWN
            g.basestock_pool[index].status = Status.WORKING  # 更新交易状态
    else:
        log.error("股票: %s, 交易状态出错", stock)


def buy_signal(context, stock, close_price, index):
    # 每次交易量为持仓量的g.adjust_scale
    amount = floor(g.adjust_scale * g.basestock_pool[index].position)
    log.info("buy scale: %f, src_posiont: %d, amount: %d", g.adjust_scale, g.basestock_pool[index].position, amount)
    
    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount = amount - (amount % 100)
    
    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01

    # 如果当前不是INIT状态，则表示已经处于一次交易中（未撮合完成）
    if g.basestock_pool[index].status == Status.WORKING:
        log.warn("股票: %s, 收到重复买入信号，但不做交易", stock)
    elif g.basestock_pool[index].status == Status.INIT:
        if g.basestock_pool[index].angle == Angle.DOWN:
            log.warn("股票：%s, 角度小于-30， 忽略买入信号", stock)
            return

        buy_stock(context, stock, amount, limit_price, index)
        if g.basestock_pool[index].buy_order_id != -1:
            g.basestock_pool[index].break_throught_time = context.current_dt
            # 以收盘价 + 价差 * expected_revenue 挂单卖出
            yesterday = get_price(stock, count=1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
            limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue

            g.basestock_pool[index].delay_amount = -amount
            g.basestock_pool[index].delay_price = limit_price
            g.basestock_pool[index].break_throught_type = Break.UP
            g.basestock_pool[index].status = Status.WORKING  # 更新交易状态

    else:
        log.error("股票: %s, 交易状态出错", stock)


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


# 获取89分钟内的最低价，不足89分钟，则计算到当前时间点
def update_89_lowest(context):
    minute_count = get_minute_count(context.current_dt)
    if minute_count > 89:
        minute_count = 89
    for i in range(g.position_count):
        low_df = get_price(g.basestock_pool[i].stock, count=minute_count, end_date=str(context.current_dt),
                           frequency='1m', fields=['low'])
        g.basestock_pool[i].lowest_89 = min(low_df['low'])


# 获取233分钟内的最高价，不足233分钟，则计算到当前时间点
def update_233_highest(context):
    minute_count = get_minute_count(context.current_dt)
    if minute_count > 233:
        minute_count = 233
    for i in range(g.position_count):
        high_df = get_price(g.basestock_pool[i].stock, count=minute_count, end_date=str(context.current_dt),
                            frequency='1m', fields=['high'])
        g.basestock_pool[i].highest_233 = max(high_df['high'])
        # high_df.sort(['high'], ascending = False).iat[0,0]


# 取消所有未完成的订单（未撮合成的订单）
def cancel_open_order(context):
    orders = get_open_orders()
    for _order in orders.values():
        #cancel_order(_order)
        g.__manager.cancel(_order)



# 恢复所有股票到原有仓位
def reset_position(context):
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        src_position = g.basestock_pool[i].position
        cur_position = context.portfolio.positions[stock].total_amount
        if src_position != cur_position:
            log.info("src_position : cur_position", src_position, cur_position)
            _order = order(stock, src_position - cur_position)
            log.warn("reset posiont: ", _order)
            try:
                g.__manager.execute(_order)
                log.info('实盘易恢复仓位挂单成功:' + str(_order))
            except:
                log.info('实盘易恢复仓位挂单失败:' + str(_order))
            g.reset_order_count += 1


def update_socket_statue(context):
    orders = get_orders()
    if len(orders) == 0:
        return
    hour = context.current_dt.hour
    minute = context.current_dt.minute

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
                    log.info("股票:%s回转交易完成 ==============> SUCCESS", stock)
                    g.basestock_pool[i].sell_order_id = -1
                    g.basestock_pool[i].buy_order_id = -1
                    g.basestock_pool[i].status = Status.INIT  # 一次完整交易（买/卖)结束，可以进行下一次交易
                    g.basestock_pool[i].buy_price = 0
                    g.basestock_pool[i].sell_price = 0
                    g.basestock_pool[i].delay_amount = 0
                    g.basestock_pool[i].delay_price = 0
                    g.basestock_pool[i].break_throught_time = None
                    g.basestock_pool[i].break_throught_type = Break.NONE
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
                    log.info("买完再卖: stock %s, delay_amount: %d", stock, g.basestock_pool[i].delay_amount)
                    sell_stock(context, stock, g.basestock_pool[i].delay_amount, g.basestock_pool[i].delay_price, i)
        # 卖完再买
        if (status == Status.WORKING) and (buy_order_id == -1):
            sell_order = orders.get(sell_order_id)
            if (sell_order is not None):
                if sell_order.status == OrderStatus.held:
                    log.info("卖完再买: stock %s, delay_amount: %d", stock, g.basestock_pool[i].delay_amount)
                    buy_stock(context, stock, g.basestock_pool[i].delay_amount, g.basestock_pool[i].delay_price, i)


def get_delta_minute(datetime1, datetime2):
    minute1 = get_minute_count(datetime1)
    minute2 = get_minute_count(datetime2)

    return abs(minute2 - minute1)


def price_and_volume_up(context, stock):
    df = get_price(stock, end_date=context.current_dt, count=3, frequency='1m', fields=['close', 'volume'])

    if (df['close'][0] < df['close'][1] < df['close'][2]) and (df['volume'][0] < df['volume'][1] < df['volume'][2]):
        log.info("量价买入：%s, close: %f, %f, %f; volume: %d, %d, %d", stock, df['close'][0], df['close'][1],
                 df['close'][2],
                 df['volume'][0], df['volume'][1], df['volume'][2])
        return True
    else:
        return False


def handle_data(context, data):
    hour = context.current_dt.hour
    minute = context.current_dt.minute

    # 每天14点55分钟 将未完成的订单强制恢复到原有持仓量
    if hour == 14 and minute == 55:
        cancel_open_order(context)
        reset_position(context)

    # 14点00分钟后， 不再有新的交易
    if hour == 14 and minute >= 0:
        return

    # 因为要计算移动平均线，所以每天前g.ma_13day_count分钟，不做交易
    if get_minute_count(context.current_dt) < g.ma_13day_count:
        # log.info("13分钟后才有交易")
        return

    # 更新89分钟内的最低收盘价，不足89分钟，则按到当前时间的最低收盘价
    update_89_lowest(context)

    # 更新233分钟内的最高收盘价，不足233分钟，则按到当前时间的最高收盘价
    update_233_highest(context)

    # 根据订单状态来更新，如果交易均结束（买与卖均成交），则置为INIT状态，表示可以再进行交易
    update_socket_statue(context)

    # 1. 循环股票列表，看当前价格是否有买入或卖出信号
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        if isnan(g.basestock_pool[i].lowest_89) is True:
            log.error("stock: %s's lowest_89 is None", stock)
            continue
        else:
            lowest_89 = g.basestock_pool[i].lowest_89

        if isnan(g.basestock_pool[i].highest_233) is True:
            log.error("stock: %s's highest_233 is None", stock)
            continue
        else:
            highest_233 = g.basestock_pool[i].highest_233

        if g.basestock_pool[i].status == Status.NONE:
            continue

        # 如果在开市前几分钟，价格不变化，则求突破线时，会出现除数为0，如果遇到这种情况，表示不会有突破，所以直接过掉
        if lowest_89 == highest_233:
            continue

        # 求取当前是否有突破

        close_m = get_price(stock, count=g.ma_13day_count, end_date=str(context.current_dt), frequency='1m',
                            fields=['close'])

        close_4 = array([0.0, 0.0, 0.0, 0.0], dtype=float)
        close_13 = array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)

        for j in range(g.ma_13day_count):
            close_13[j] = close_m.iat[j, 0]
        for j in range(g.ma_13day_count):
            close_13[j] = ((close_13[j] - lowest_89) * 1.0 / (highest_233 - lowest_89)) * 4

        close_4 = close_13[9:]

        if close_13 is not None:
            operator_line_13 = 0
            operator_line_4 = 0
            for item in close_13:
                operator_line_13 += item

            for item in close_4:
                operator_line_4 += item
            operator_line_13 = operator_line_13 / g.ma_13day_count
            operator_line_4 = operator_line_4 / g.ma_4day_count
        else:
            log.warn("股票: %s 可能由于停牌等原因无法求解MA", stock)
            continue

        # 买入信号产生

        if ((g.basestock_pool[i].operator_value_4 < g.basestock_pool[i].operator_value_13) and (
                    operator_line_4 > operator_line_13) and (operator_line_13 < 0.3) and (
                    close_m.iat[g.ma_13day_count - 1, 0] > close_m.iat[g.ma_13day_count - 2, 0] * 0.97)):
            log.info(
                "金叉买入：%s, ma_4 from %f to %f, ma_13 from %f to %f, close_price: %f, yesterday_close_price: %f, lowest_89: %f, highest_233: %f",
                stock, g.basestock_pool[i].operator_value_4, operator_line_4, g.basestock_pool[i].operator_value_13,
                operator_line_13, close_m.iat[g.ma_4day_count - 1, 0], close_m.iat[g.ma_13day_count - 2, 0], lowest_89,
                highest_233)
            buy_signal(context, stock, close_m.iat[g.ma_13day_count - 1, 0], i)
        # 卖出信号产生
        elif ((g.basestock_pool[i].operator_value_4 > g.basestock_pool[i].operator_value_13) and (
                    operator_line_4 < operator_line_13) and (operator_line_13 > 3.7) and (
                    close_m.iat[g.ma_13day_count - 1, 0] < close_m.iat[g.ma_13day_count - 2, 0] * 1.03)):
            log.info(
                "死叉卖出：%s, ma_4 from %f to %f, ma_13 from %f to %f, close_price: %f, yesterday_close_price: %f, lowest_89: %f, highest_233: %f",
                stock, g.basestock_pool[i].operator_value_4, operator_line_4, g.basestock_pool[i].operator_value_13,
                operator_line_13, close_m.iat[g.ma_4day_count - 1, 0], close_m.iat[g.ma_13day_count - 2, 0], lowest_89,
                highest_233)
            sell_signal(context, stock, close_m.iat[g.ma_13day_count - 1, 0], i)
        # 价格与成交量均上涨，也是买入信号
        elif (price_and_volume_up(context, stock)):
            buy_signal(context, stock, close_m.iat[g.ma_13day_count - 1, 0], i)
        else:
            # log.info("%s, ma_4 from %f to %f, ma_13 from %f to %f, close_price: %f, yesterday_close_price: %f, lowest_89: %f, highest_233: %f", stock, g.basestock_pool[i].operator_value_4, operator_line_4, g.basestock_pool[i].operator_value_13, operator_line_13, close_m.iat[g.ma_4day_count-1,0], close_m.iat[g.ma_13day_count-2,0], lowest_89, highest_233)
            pass
        g.basestock_pool[i].operator_value_4 = operator_line_4
        g.basestock_pool[i].operator_value_13 = operator_line_13


def after_trading_end(context):
    log.info("===========================================================================")
    log.info("[统计数据]成功交易次数: %d, 重复信号交易次数: %d, 收盘前强制交易次数: %d", g.success_count, g.repeat_signal_count,
             g.reset_order_count)
    log.info("===========================================================================")
