from jqdata import *
import numpy as np
import pandas as pd
import talib as ta

# 持仓股票池
g.basestock_pool = []
g.repeat_signal_count = 0
g.reset_order_count = 0
g.success_count = 0
g.up = 0.3 
g.down = 3.7
# 一次突破时，反向挂单时间（距离突破点）， 单位：分钟
g.delay_time = 30
class Status(Enum):
    INIT    = 0  # 在每天交易开始时，置为INIT
    WORKING = 1  # 处于买/卖中
    NONE    = 2  # 今天不再做任何交易
    
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
    
        self.break_throught_time = None  # 突破时间点
        self.delay_amount = 0            # 反向挂单量
        self.delay_price = 0             # 反向挂单价格

    def print_stock(self):
        log.info("stock: %s, close: %f, min_vol: %f, max_vol: %f, lowest: %f, hightest: %f, operator_value: %f, position: %f, sell_roder_id: %d, buy_order_id: %d"
        , self.stock, self.close, self.min_vol, self.max_vol, self.lowest, self.highest, self.operator_value, self.position, self.sell_order_id, self.buy_order_id)
def initialize(context):
    log.info("---> initialize @ %s" % (str(context.current_dt))) 
    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0
    # 第一天运行时，需要选股入池，并且当天不可进行股票交易
    g.firstrun = True
    
    # 默认股票池容量
    g.position_count = 30
    
    # 记录进入股票池中的股票数量
    select_count = 0
    g.expected_revenue = 0.003  # 期望收益率
    # 获得沪深300的股票列表, 5天波动率大于2%，单价大于10.00元, 每标的买入100万元
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
    # 每次交易量为持仓量的1/4    
    amount = 0.25 * context.portfolio.positions[stock].total_amount
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)
        amount = amount_new

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01
    
    # 如果当前不是INIT状态，则表示已经处于一次交易中（未撮合完成）	
    if g.basestock_pool[index].status == Status.WORKING:
        #30分钟内出现同向信号
        if (get_delta_minute(context.current_dt, g.basestock_pool[index].break_throught_time) < g.delay_time):
            #新的卖出价高于之前，以现有价格买入，并当日不做回转交易
            if limit_price > g.basestock_pool[index].sell_price:
                src_position = g.basestock_pool[index].position
                cur_position = context.portfolio.positions[stock].total_amount
                _order = order(stock, (src_position - cur_position), LimitOrderStyle(limit_price))
                log.warn("[30分钟内信号重复]股票: %s, 以%f价格挂单，买入%d", stock, limit_price, (src_position - cur_position))
                g.basestock_pool[index].status = Status.NONE
                g.repeat_signal_count += 1
                return
            else:
                log.warn("NO Chance to SELL_BUY, current status: ", g.basestock_pool[index].status)
                return
    
    sell_ret = sell_stock(context, stock, -amount, limit_price, index)
    g.basestock_pool[index].break_throught_time = context.current_dt
    # 以收盘价 - 价差 * expected_revenue 挂单买入
    yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue
    
    if g.delay_time == 0:        
        buy_ret = buy_stock(context, stock, amount, limit_price, index)
        g.basestock_pool[index].status = Status.WORKING  #更新交易状态		
    elif g.delay_time > 0:
        g.basestock_pool[index].delay_amount = amount;
        g.basestock_pool[index].delay_price = limit_price;	
        g.basestock_pool[index].status = Status.WORKING  #更新交易状态
    else:
        log.error("g.delay_time: %d, is ERROR", g.delay_time)
        
    
    
    #更新交易状态
    g.basestock_pool[index].status = Status.WORKING
    
# 产生先买后卖信号	
def buy_sell(context, stock, close_price, index):

    # 每次交易量为持仓量的1/4
    amount = 0.25 * context.portfolio.positions[stock].total_amount
    
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)
        amount = amount_new
    
    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    
    # 如果当前不是INIT状态，则表示已经处于一次交易中（未撮合完成）	
    if g.basestock_pool[index].status == Status.WORKING:
        #30分钟内出现同向信号
        
        if (get_delta_minute(context.current_dt, g.basestock_pool[index].break_throught_time) < g.delay_time):
            #新的买入价低于之前，以现有价格卖出，并当日不做回转交易
            if limit_price < g.basestock_pool[index].buy_price:
                src_position = g.basestock_pool[index].position
                cur_position = context.portfolio.positions[stock].total_amount
                _order = order(stock, (src_position - cur_position), LimitOrderStyle(limit_price))
                log.warn("[30分钟内信号重复]股票: %s, 以%f价格挂单，卖出%d", stock, limit_price, (src_position - cur_position))
                g.basestock_pool[index].status = Status.NONE
                g.repeat_signal_count += 1
                return
            else:
                log.warn("NO Chance to BUY_SELL, current status: ", g.basestock_pool[index].status)
                return
    

    buy_stock(context, stock, amount, limit_price, index)
    g.basestock_pool[index].break_throught_time = context.current_dt
    # 以收盘价 + 价差 * expected_revenue 挂单卖出
    yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue
    
    if g.delay_time == 0:        
        sell_stock(context, stock, -amount, limit_price, index)
        g.basestock_pool[index].status = Status.WORKING   #更新交易状态
    elif g.delay_time > 0:
        g.basestock_pool[index].delay_amount = -amount;
        g.basestock_pool[index].delay_price = limit_price;
        g.basestock_pool[index].status = Status.WORKING   #更新交易状态
    else:
        log.error("g.delay_time: %d, is ERROR", g.delay_time)
    
    
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
        low_df = get_price(g.basestock_pool[i].stock, count = minute_count, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        g.basestock_pool[i].lowest_89 = low_df.sort(['close'], ascending = True).iat[0,0]
        
# 获取233分钟内的最高价，不足233分钟，则计算到当前时间点		
def update_233_highest(context):
    minute_count = get_minute_count(context.current_dt)
    if minute_count > 233:
        minute_count = 233
    for i in range(g.position_count):
        high_df = get_price(g.basestock_pool[i].stock, count = minute_count, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        g.basestock_pool[i].highest_233 = high_df.sort(['close'], ascending = False).iat[0,0]

# 取消所有未完成的订单（未撮合成的订单）        
def cancel_open_order(context):
    orders = get_open_orders()
    for _order in orders.values():
        cancel_order(_order)
        log.warn("cancel order: ", _order)
    
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
                    g.basestock_pool[i].sell_order_id = -1
                    g.basestock_pool[i].buy_order_id = -1
                    g.basestock_pool[i].status = Status.INIT  #一次完整交易（买/卖)结束，可以进行下一次交易
                    g.basestock_pool[i].buy_price = 0
                    g.basestock_pool[i].sell_price = 0
                    g.basestock_pool[i].delay_amount = 0
                    g.basestock_pool[i].delay_price = 0
                    g.basestock_pool[i].break_throught_time = None
                    g.success_count += 1
        # 每天14点后， 不再进行新的买卖
        if hour == 14 and g.basestock_pool[i].status == Status.INIT:
            g.basestock_pool[i].status = Status.NONE

def get_delta_minute(datetime1, datetime2):
    minute1 = get_minute_count(datetime1)
    minute2 = get_minute_count(datetime2)
    
    return abs(minute2 - minute1)
    
'''
    在突破点半小时后，进行反向挂单
'''
def resting_reverse_order(context):
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        break_throught_time = g.basestock_pool[i].break_throught_time
        delay_amount = g.basestock_pool[i].delay_amount
        delay_price = g.basestock_pool[i].delay_price
        if g.basestock_pool[i].status == Status.NONE or break_throught_time is None:
            continue
            
        if (get_delta_minute(context.current_dt, break_throught_time) > g.delay_time):
            if delay_amount > 0:    # 反向买入
                _order = order(stock, delay_amount, LimitOrderStyle(delay_price))
                if _order is not None:
                    g.basestock_pool[i].buy_order_id = _order.order_id
                    g.basestock_pool[i].delay_amount = 0
                    g.basestock_pool[i].buy_price = delay_price
                    log.info("股票:%s 挂买入单成功，买入量: %d, 买入价格: %f", stock, delay_amount, delay_price)
                else:
                    log.error("股票:%s 挂买入单失败，买入量: %d, 买入价格: %f", stock, delay_amount, delay_price)
            elif delay_amount < 0:   # 反向卖出
                _order = order(stock, delay_amount, LimitOrderStyle(delay_price))
                if _order is not None:
                    g.basestock_pool[i].sell_order_id = _order.order_id
                    g.basestock_pool[i].delay_amount = 0
                    g.basestock_pool[i].sell_price = delay_price
                    log.info("股票:%s 挂卖出单成功，卖出量: %d, 卖出价格: %f", stock, delay_amount, delay_price)
                else:
                    log.error("股票:%s 挂卖出单失败，卖出量: %d, 卖出价格: %f", stock, delay_amount, delay_price)
            else:
                pass

            
def handle_data(context, data):
    # 0. 平均购买价值1000000元的30个股票，并记录持仓数量
    if str(context.run_params.start_date) == str(context.current_dt.strftime("%Y-%m-%d")):
        if g.firstrun is True:
            for i in range(g.position_count):                
                myorder = order_value(g.basestock_pool[i].stock, 1000000)
                g.basestock_pool[i].position = myorder.amount
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

    # 因为要计算移动平均线，所以每天前4分钟，不做交易
    if get_minute_count(context.current_dt) < 4:
        return
        
    # 更新89分钟内的最低收盘价，不足89分钟，则按到当前时间的最低收盘价
    update_89_lowest(context)
    
    # 更新233分钟内的最高收盘价，不足233分钟，则按到当前时间的最高收盘价
    update_233_highest(context)
    
    # 根据突破点与当前时间，看是否反向挂单
    resting_reverse_order(context)
    
    # 根据订单状态来更新，如果交易均结束（买与卖均成交），则置为INIT状态，表示可以再进行交易
    update_socket_statue(context)
            
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        lowest_89 = g.basestock_pool[i].lowest_89
        highest_233 = g.basestock_pool[i].highest_233
        
        if g.basestock_pool[i].status == Status.NONE:
            continue
        
        # 如果在开市前几分钟，价格不变化，则求突破线时，会出现除数为0，如果遇到这种情况，表示不会有突破，所以直接过掉
        if lowest_89 == highest_233:
            continue
        
        #求取当前是否有突破
        
        close_m = get_price(stock, count = 4, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        close =  np.array([close_m.iat[0,0], close_m.iat[1,0], close_m.iat[2,0], close_m.iat[3,0]]).astype(float)
        for j in range(4):
            close[j] = ((close[j] - lowest_89) * 1.0 / (highest_233 - lowest_89)) * 4
        operator_line =  ta.MA(close, 4)
        
        '''
        log.info("股票代码：%s, 前一分钟操盘线值: %f, 当前操作线值: %f, 两者之差的绝对值: %f", stock,
                g.basestock_pool[i].operator_value, operator_line[3], abs(g.basestock_pool[i].operator_value - operator_line[3]))
        '''
        
        # 买入信号产生
        if g.basestock_pool[i].operator_value < g.up and operator_line[3] > g.up and g.basestock_pool[i].operator_value != 0.0:
            log.info("BUY SIGNAL for %s, from %f to %f, close_price: %f", stock, g.basestock_pool[i].operator_value, operator_line[3], close_m.iat[3,0])
            
            buy_sell(context, stock, close_m.iat[3,0], i)
        # 卖出信息产生
        elif g.basestock_pool[i].operator_value > g.down and operator_line[3] < g.down:
            log.info("SELL SIGNAL for %s, from %f to %f, close_price: %f", stock, g.basestock_pool[i].operator_value, operator_line[3], close_m.iat[3,0])
            
            sell_buy(context, stock, close_m.iat[3,0], i)
            
        # 记录当前操盘线值
        g.basestock_pool[i].operator_value = operator_line[3]

def after_trading_end(context):
    log.info("===========================================================================")
    log.info("[统计数据]成功交易次数: %d, 重复信号交易次数: %d, 收盘前强制交易次数: %d",  g.success_count, g.repeat_signal_count, g.reset_order_count)
    log.info("===========================================================================")
        
