from jqdata import *
import numpy as np
import pandas as pd
import talib as ta
from math import isnan
# 股票池来源
class Source(Enum):
    AUTO  = 0  # 程序根据波动率及股价自动从沪深300中获取股票
    CLIENT = 1 # 使用用户提供的股票

g.stocks_source = Source.AUTO  # 默认使用自动的方法获得股票
g.stock_id_list_from_client = ["000031.XSHE", "000059.XSHE", "000060.XSHE", "000401.XSHE", 
                               "000423.XSHE", "000528.XSHE", "000562.XSHE", "600036.XSHG", 
                               "000568.XSHE", "000612.XSHE", "000728.XSHE", "000768.XSHE", 
                               "000800.XSHE", "000878.XSHE", "000898.XSHE", "000927.XSHE", 
                               "000937.XSHE", "002024.XSHE", "002142.XSHE", "600009.XSHG", 
                               "600026.XSHG", "600037.XSHG", "000024.XSHE", "000527.XSHE",  
                               "600104.XSHG", "600109.XSHG", "600161.XSHG", "600251.XSHG", 
                               "600266.XSHG", "600096.XSHG"]

# 持仓股票池详细信息
g.basestock_pool = []

#用于统计结果
g.repeat_signal_count = 0
g.reset_order_count = 0
g.success_count = 0

# 上穿及下穿阈值
g.up = 0.1
g.down = 3.9

#MA平均的天数
g.ma_day_count = 4

#每次调整的比例
g.adjust_scale = 0.25 
# 一次突破时，反向挂单时间（距离突破点）， 单位：分钟
g.delay_time = 30

# 期望收益率
g.expected_revenue = 0.003

class Status(Enum):
    INIT    = 0  # 在每天交易开始时，置为INIT
    WORKING = 1  # 处于买/卖中
    NONE    = 2  # 今天不再做任何交易
    
class Break(Enum):
    UP   = 0  # 上穿
    DOWN = 1  # 下穿 
    NONE = 2
'''
    记录股票详细信息
'''

class BaseStock(object):

    def __init__ (self, stock, close, min_vol, max_vol, lowest, highest, operator_value, status, position, sell_order_id, buy_order_id):
        self.stock = stock
        self.close = close
        self.min_vol = min_vol
        self.max_vol = max_vol
        self.lowest = lowest
        self.highest = highest
        self.operator_value = operator_value
        self.status = status
        self.position = position
        self.sell_order_id = sell_order_id
        self.sell_price = 0
        self.buy_order_id = buy_order_id
        self.buy_price = 0
    
        self.break_throught_type = Break.NONE  # 突破类型 up or down
        self.break_throught_time = None  # 突破时间点
        self.delay_amount = 0            # 反向挂单量
        self.delay_price = 0             # 反向挂单价格

    def print_stock(self):
        log.info("stock: %s, close: %f, min_vol: %f, max_vol: %f, lowest: %f, hightest: %f, operator_value: %f, position: %f, sell_roder_id: %d, buy_order_id: %d"
        , self.stock, self.close, self.min_vol, self.max_vol, self.lowest, self.highest, self.operator_value, self.position, self.sell_order_id, self.buy_order_id)

'''
    获得沪深300的股票列表, 5天波动率大于2%，单价大于10.00元, 每标的买入100万元
'''
def get_stocks_by_vol(context):
    select_count = 0

    stock_list = get_index_stocks('399300.XSHE')
    for stock in stock_list:
        df = get_price(stock, count = 6, end_date = str(context.current_dt), frequency = 'daily', fields = ['high','low', 'close'])
        for i in range(5):
            df.ix[i+1, 'Volatility'] = (df.ix[i, 'high'] - df.ix[i, 'low']) / df.ix[i+1, 'close']
        
        #选择单价大于10.0元
        if df.ix[5, 'close'] > 10.00:
            vol_df = df.ix[1:6,['Volatility']].sort(["Volatility"], ascending=True)
            min_vol = vol_df.iat[0, 0]
            max_vol = vol_df.iat[4, 0]
            #选择最近5天的波动率最小值大于0.02
            if min_vol > 0.02:
                stock_obj = BaseStock(stock, df.ix[5, 'close'], min_vol, max_vol, 0, 0, 0, Status.INIT, 0, -1, -1)
                g.basestock_pool.append(stock_obj)
                select_count += 1
            else:
                pass
        else:
            pass
    if select_count < g.position_count:
        g.position_count = select_count

'''
    直接从客户得到股票列表
'''
def get_stocks_by_client(context):
    select_count = 0
    for stock_id in g.stock_id_list_from_client:
        stock_obj = BaseStock(stock_id, 0, 0, 0, 0, 0, 0, Status.INIT, 0, -1, -1)
        g.basestock_pool.append(stock_obj)
        select_count += 1
    
    if select_count < g.position_count:
        g.position_count = select_count
    
def initialize(context):
    log.info("---> initialize @ %s" % (str(context.current_dt))) 
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
    
# 在每天交易开始时，将状态置为可交易状态
def before_trading_start(context):
    log.info("初始化买卖状态为INIT")
    for i in range(g.position_count):
        g.basestock_pool[i].status = Status.INIT
        g.basestock_pool[i].lowest = 0
        g.basestock_pool[i].highest = 0
        g.basestock_pool[i].operator_value = 0
        g.basestock_pool[i].status = Status.INIT

        g.basestock_pool[i].sell_order_id = -1
        g.basestock_pool[i].sell_price = 0
        g.basestock_pool[i].buy_order_id = -1
        g.basestock_pool[i].buy_price = 0
    
        g.basestock_pool[i].break_throught_time = None
        g.basestock_pool[i].delay_amount = 0
        g.basestock_pool[i].delay_price = 0
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
# 卖出股票，并记录订单号，便于查询订单状态		
def sell_stock(context, stock, amount, limit_price, index):
    sell_order = order(stock, amount, LimitOrderStyle(limit_price))
    g.basestock_pool[index].sell_price = limit_price
    if sell_order is not None:
        g.basestock_pool[index].sell_order_id = sell_order.order_id
        log.info("股票: %s, 以%f价格挂单，卖出%d", stock, limit_price, amount)
# 产生先卖后买信号
def sell_buy(context, stock, close_price, index):
    # 每次交易量为持仓量的g.adjust_scale
    amount = g.adjust_scale * g.basestock_pool[index].position
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)
        amount = amount_new

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01
    
    # 如果当前不是INIT状态，则表示已经处于一次交易中（未撮合完成）	
    if g.basestock_pool[index].status == Status.WORKING:
        #30分钟内出现同向信号
        if (get_delta_minute(context.current_dt, g.basestock_pool[index].break_throught_time) < g.delay_time):
            src_position = g.basestock_pool[index].position
            cur_position = context.portfolio.positions[stock].total_amount
        
            #新的卖出价高于之前，以现有价格买入平仓，再挂买入单，再挂卖出单
            if limit_price > g.basestock_pool[index].sell_price:
                # 0. 撤销原有卖出单
                cancel_order(g.basestock_pool[index].buy_order_id)
                log.warn("[30分钟内卖出信号重复]股票: %s, 撤销原有买入单", stock)
                # 1. 先以当前价格平仓
                #_order = order(stock, (src_position - cur_position), LimitOrderStyle(close_price))
                #log.warn("[30分钟内卖出信号重复]股票: %s, 以%f价格挂单，买入%d，用于平仓", stock, close_price, (src_position - cur_position))
                log.info("src: %d, cur: %d", src_position, cur_position)
                # 2. 当前收盘价格-价差挂买入单
                amount = g.adjust_scale * src_position
                if amount % 100 != 0:
                    amount_new = amount - (amount % 100)
                    amount = amount_new
                yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
                limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue
                
                buy_stock(context, stock, 2 * amount, limit_price, index)
                # 3. 以当前价格+0.01挂单卖出
                limit_price = close_price + 0.01
                
                g.basestock_pool[index].delay_amount = -amount
                g.basestock_pool[index].delay_price = limit_price
                g.basestock_pool[index].break_throught_type = Break.DOWN
                log.info("待股票: %s买入挂单完成后，需要挂出卖出单：%d, 卖出价%f", stock, -amount, limit_price)
                g.basestock_pool[index].break_throught_time = context.current_dt
                g.basestock_pool[index].status = Status.WORKING
                
                g.repeat_signal_count += 1
                return
            else:
                log.warn("[30分钟内卖出信号重复]股票: %s, 但不做交易", stock)
                return
        else:
            log.warn("[30分钟以上卖出信号重复]股票: %s, 但不做交易", stock)
    if g.basestock_pool[index].status == Status.INIT:
        sell_ret = sell_stock(context, stock, -amount, limit_price, index)
        g.basestock_pool[index].break_throught_time = context.current_dt
        # 以收盘价 - 价差 * expected_revenue 挂单买入
        yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
        limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue
        
        g.basestock_pool[index].delay_amount = amount
        g.basestock_pool[index].delay_price = limit_price
        g.basestock_pool[index].break_throught_type = Break.DOWN
        log.info("待股票: %s卖出挂单完成后，需要挂出买入单：%d, 买入价%f", stock, amount, limit_price)        
        g.basestock_pool[index].status = Status.WORKING  #更新交易状态

    
# 产生先买后卖信号	
def buy_sell(context, stock, close_price, index):

    # 每次交易量为持仓量的g.adjust_scale
    amount = g.adjust_scale * g.basestock_pool[index].position
    
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)
        amount = amount_new
    
    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    
    # 如果当前不是INIT状态，则表示已经处于一次交易中（未撮合完成）	
    if g.basestock_pool[index].status == Status.WORKING:
        
        #30分钟内出现同向信号
        if (get_delta_minute(context.current_dt, g.basestock_pool[index].break_throught_time) < g.delay_time):
            #新的买入价低于之前，平仓（卖出）后，再挂卖出单 和 买入单
            src_position = g.basestock_pool[index].position
            cur_position = context.portfolio.positions[stock].total_amount
            log.info("src: %d, cur: %d", src_position, cur_position)
            # 在这一刻，撮合成功

            if limit_price < g.basestock_pool[index].buy_price:
                # 0. 撤销原有卖出单
                cancel_order(g.basestock_pool[index].sell_order_id)
                log.warn("[30分钟内买入信号重复]股票: %s, 撤销原有卖出单", stock)
                log.info("src: %d, cur: %d", src_position, cur_position)
                # 1. 以现有价格平仓
                #_order = order(stock, (src_position - cur_position), LimitOrderStyle(close_price))
                #log.warn("[30分钟内买入信号重复]股票: %s, 以%f价格挂单，卖出%d，用于平仓", stock, close_price, (src_position - cur_position))
                
                # 2. 以当前价格+0.01挂单卖出
                amount = g.adjust_scale * src_position
                if amount % 100 != 0:
                    amount_new = amount - (amount % 100)    
                    amount = amount_new
                limit_price = close_price + 0.01
                sell_stock(context, stock, -2*amount, limit_price, index)
                # 3. 当前收盘价格-价差挂买入单
                yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
                limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue
               
                g.basestock_pool[index].delay_amount = amount
                g.basestock_pool[index].delay_price = limit_price
                g.basestock_pool[index].break_throught_type = Break.DOWN
                log.info("待股票: %s卖出挂单完成后，需要挂出买入单：%d, 买入价%f", stock, amount, limit_price)
                g.basestock_pool[index].break_throught_time = context.current_dt
                g.basestock_pool[index].status = Status.WORKING
                g.repeat_signal_count += 1
                return
            else:
                log.warn("[30分钟内买入信号重复]股票: %s, 但不做交易", stock)
                return
        else:
            log.warn("[30分钟以上卖出信号重复]股票: %s, 但不做交易", stock)
    if g.basestock_pool[index].status == Status.INIT:
        buy_stock(context, stock, amount, limit_price, index)
        g.basestock_pool[index].break_throught_time = context.current_dt
        # 以收盘价 + 价差 * expected_revenue 挂单卖出
        yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
        limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue
        
        g.basestock_pool[index].delay_amount = -amount
        g.basestock_pool[index].delay_price = limit_price
        g.basestock_pool[index].break_throught_type = Break.UP
        log.info("待股票: %s买入挂单完成后，需要挂出卖出单：%d, 卖出价%f, index:%d", stock, -amount, limit_price, index)
        g.basestock_pool[index].status = Status.WORKING   #更新交易状态
    
    
# 计算当前时间点，是开市以来第几分钟   
def get_minute_count(current_dt):
    '''
     9:30 -- 11:30
     13:00 --- 15:00
     '''
    current_hour = current_dt.hour
    current_min  = current_dt.minute
    
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
        low_df = get_price(g.basestock_pool[i].stock, count = minute_count, end_date=str(context.current_dt), frequency='1m', fields=['low'])
        g.basestock_pool[i].lowest_89 = min(low_df['low'])
        #low_df.sort(['low'], ascending = True).iat[0,0]
        
# 获取233分钟内的最高价，不足233分钟，则计算到当前时间点
def update_233_highest(context):
    minute_count = get_minute_count(context.current_dt)
    if minute_count > 233:
        minute_count = 233
    for i in range(g.position_count):
        high_df = get_price(g.basestock_pool[i].stock, count = minute_count, end_date=str(context.current_dt), frequency='1m', fields=['high'])
        g.basestock_pool[i].highest_233 =  max(high_df['high'])
        #high_df.sort(['high'], ascending = False).iat[0,0]
        

# 取消所有未完成的订单（未撮合成的订单）        
def cancel_open_order(context):
    orders = get_open_orders()
    for _order in orders.values():
        cancel_order(_order)
        #log.warn("cancel order: ", _order)
    
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
            sell_order =  orders.get(sell_order_id)
            buy_order = orders.get(buy_order_id)
            if (sell_order is not None) and (buy_order is not None):
                if sell_order.status == OrderStatus.held and buy_order.status == OrderStatus.held:
                    log.info("股票:%s回转交易完成 ==============> SUCCESS", stock)
                    g.basestock_pool[i].sell_order_id = -1
                    g.basestock_pool[i].buy_order_id = -1
                    g.basestock_pool[i].status = Status.INIT  #一次完整交易（买/卖)结束，可以进行下一次交易
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

def get_delta_minute(datetime1, datetime2):
    minute1 = get_minute_count(datetime1)
    minute2 = get_minute_count(datetime2)
    
    return abs(minute2 - minute1)

'''
    该函数查看在上穿或下穿信号到来时的正向单是否已经成功，如果是，则需要挂出反向单
    在handle_data开始及结束时，调用
'''
def post_reverse_order(context):
    orders = get_orders()
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        break_throught_type = g.basestock_pool[i].break_throught_type
        delay_amount = g.basestock_pool[i].delay_amount
        delay_price = g.basestock_pool[i].delay_price
        status = g.basestock_pool[i].status
        
        if break_throught_type == Break.NONE:
            continue
            
        if (Break.UP == break_throught_type):
            buy_order_id = g.basestock_pool[i].buy_order_id
            if (status == Status.WORKING) and (buy_order_id != -1):
                buy_order = orders.get(buy_order_id)
                if (buy_order is not None):
                    if buy_order.status == OrderStatus.held:
                        log.info("股票: %s在上穿信号产生的买入单成功交易，当前仓位:%d，原有仓位：%d", 
                                 stock, context.portfolio.positions[stock].total_amount, g.basestock_pool[i].position)
                        sell_stock(context, stock, delay_amount, delay_price, i)
                        log.info("股票：%s在上穿信号产生的买入单，当前成功反向挂卖出%d", stock, delay_amount)
                        g.basestock_pool[i].break_throught_type = Break.NONE
                else:
                    log.error("无法得到股票：%s在上穿信号产生的买入单，所以无法反向挂卖出单", stock)
        else:
            sell_order_id = g.basestock_pool[i].sell_order_id
            if (status == Status.WORKING) and (sell_order_id != -1):
                sell_order = orders.get(sell_order_id)
                if (sell_order is not None):
                    if sell_order.status == OrderStatus.held:
                        log.info("股票: %s在下穿信号产生的卖入单成功交易，当前仓位:%d，原有仓位：%d", 
                                  stock, context.portfolio.positions[stock].total_amount, g.basestock_pool[i].position)
                        buy_stock(context, stock, delay_amount, delay_price, i)
                        log.info("股票：%s在下穿信号产生的卖出单，当前成功反向挂买入%d", stock, delay_amount)
                        g.basestock_pool[i].break_throught_type = Break.NONE
                else:
                    log.error("无法得到股票：%s在下穿信号产生的卖出单，所以无法反向挂买入单", stock)
            
            
def handle_data(context, data):
    # 0. 平均购买价值1000000元的30个股票，并记录持仓数量
    if str(context.run_params.start_date) == str(context.current_dt.strftime("%Y-%m-%d")):
        if g.firstrun is True:
            for i in range(g.position_count):                
                myorder = order_value(g.basestock_pool[i].stock, 1000000)
                if myorder is not None:
                    g.basestock_pool[i].position = myorder.amount
                else:
                    log.error("股票: %s 买入失败", g.basestock_pool[i].stock)
            log.info("====================================================================")
            for i in range(g.position_count):                
                g.basestock_pool[i].print_stock()    
            g.firstrun = False
        return
    
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    
    # 每天14点45分钟 将未完成的订单强制恢复到原有持仓量
    if hour == 14 and minute == 45:
        cancel_open_order(context)
        reset_position(context)     
        
    # 14点45分钟后， 不再有新的交易 
    if hour == 14 and minute >= 45:
        return

    # 因为要计算移动平均线，所以每天前g.ma_day_count分钟，不做交易
    if get_minute_count(context.current_dt) < g.ma_day_count:
        return
        
    # 更新89分钟内的最低收盘价，不足89分钟，则按到当前时间的最低收盘价
    update_89_lowest(context)
    
    # 更新233分钟内的最高收盘价，不足233分钟，则按到当前时间的最高收盘价
    update_233_highest(context)
    
    # 根据挂单状态，决定是否挂反向单
    post_reverse_order(context)
    
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
            
        if  isnan(g.basestock_pool[i].highest_233) is True:
            log.error("stock: %s's highest_233 is None", stock)
            continue
        else:
            highest_233 = g.basestock_pool[i].highest_233
            
        if g.basestock_pool[i].status == Status.NONE:
            continue
        
        # 如果在开市前几分钟，价格不变化，则求突破线时，会出现除数为0，如果遇到这种情况，表示不会有突破，所以直接过掉
        if lowest_89 == highest_233:
            continue
        
        #求取当前是否有突破
        
        close_m = get_price(stock, count = g.ma_day_count, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        close = [0.0] * g.ma_day_count
        for j in range(g.ma_day_count):
            close[j] = close_m.iat[j, 0]
        close =  np.array(close).astype(float)
        for j in range(g.ma_day_count):
            close[j] = ((close[j] - lowest_89) * 1.0 / (highest_233 - lowest_89)) * 4
            
        if close is not None:
            operator_line =  ta.MA(close, g.ma_day_count)
        else:
            log.warn("股票: %s 可能由于停牌等原因无法求解MA", stock)
            continue
        
        
        # 买入信号产生
        if g.basestock_pool[i].operator_value < g.up and operator_line[g.ma_day_count-1] > g.up and g.basestock_pool[i].operator_value != 0.0:
            log.info("BUY SIGNAL for %s, from %f to %f, close_price: %f, lowest_89: %f, highest_233: %f", stock, g.basestock_pool[i].operator_value, operator_line[g.ma_day_count-1], close_m.iat[g.ma_day_count-1,0], lowest_89, highest_233)
            buy_sell(context, stock, close_m.iat[g.ma_day_count-1,0], i)
        # 卖出信息产生
        elif g.basestock_pool[i].operator_value > g.down and operator_line[g.ma_day_count-1] < g.down:
            log.info("SELL SIGNAL for %s, from %f to %f, close_price: %f, lowest_89: %f, highest_233: %f", stock, g.basestock_pool[i].operator_value, operator_line[g.ma_day_count-1], close_m.iat[g.ma_day_count-1,0], lowest_89, highest_233)
            sell_buy(context, stock, close_m.iat[g.ma_day_count-1,0], i)
            
        # 记录当前操盘线值
        g.basestock_pool[i].operator_value = operator_line[g.ma_day_count-1]
    
    # 根据挂单状态，决定是否挂反向单
    post_reverse_order(context)
    
def after_trading_end(context):
    log.info("===========================================================================")
    log.info("[统计数据]成功交易次数: %d, 重复信号交易次数: %d, 收盘前强制交易次数: %d",  g.success_count, g.repeat_signal_count, g.reset_order_count)
    log.info("===========================================================================")
        
