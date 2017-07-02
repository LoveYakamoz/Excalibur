from jqdata import *
import numpy as np
import pandas as pd
import talib as ta

# 持仓股票池
g.basestock_pool = []

class Status(Enum):
    INIT    = 0  # 在每天交易开始时，置为INIT
    
    BUYING_SELLING  = 1  # 已经挂单买入及卖出，但还未成交
    BOUGHT_SELLING  = 2  # 买入挂单已经成交，卖出挂单还未成交
    
    SELLING_BUYING  = 3  # 已经挂单卖出及买入，但还未成交
    SOLD_BUYING     = 4  # 卖出挂单已经成交，买入挂单还未成交
    
    BOUGHT_SOLD     = 5  # 买入挂单已经成交，卖出挂单已经成交
    
    NONE            = 6  # 不再做任何交易
    
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
        self.buy_order_id = buy_order_id

    def print_stock(self):
        log.info("stock: %s, close: %f, min_vol: %f, max_vol: %f, lowest: %f, hightest: %f, operator_value: %f, position: %f, sell_roder_id: %d, buy_order_id: %d"
        , self.stock, self.close, self.min_vol, self.max_vol, self.lowest, self.highest, self.operator_value, self.position, self.sell_order_id, self.buy_order_id)
def initialize(context):
    log.info("---> initialize @ %s" % (str(context.current_dt))) 

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
    
# 购买股票，并记录订单号，便于查询订单状态	
def buy_stock(context, stock, amount, limit_price, index):
    buy_order = order(stock, amount, LimitOrderStyle(limit_price))
    
    if buy_order is not None:
		g.basestock_pool[index].buy_order_id = buy_order.order_id

# 卖出股票，并记录订单号，便于查询订单状态		
def sell_stock(context, stock, amount, limit_price, index):
    sell_order = order(stock, -amount, LimitOrderStyle(limit_price))
    
    if sell_order is not None:
		g.basestock_pool[index].sell_order_id = sell_order.order_id
# 产生先卖后买信号
def sell_buy(context, stock, close_price, index):
    if g.basestock_pool[index].status != Status.INIT:
        log.warn("NO Chance to SELL_BUY, current status: ", g.basestock_pool[index].status)
        return

	# 每次交易量为持仓量的1/4    
    amount = 0.25 * context.portfolio.positions[stock].total_amount
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)
        amount = amount_new

	# 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01

    sell_ret = sell_stock(context, stock, amount, limit_price, index)
    
	# 以收盘价 - 价差 * expected_revenue 挂单买入
    yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue
    buy_ret = buy_stock(context, stock, amount, limit_price, index)
    
	#更新交易状态
    g.basestock_pool[index].status = Status.SELLING_BUYING
    
# 产生先买后卖信号	
def buy_sell(context, stock, close_price, index):
	# 如果当前不是INIT状态，则表示已经处于一次交易中（未撮合完成），不能新开交易；或者是14点后，不允许再有新的交易
    if g.basestock_pool[index].status != Status.INIT:
        log.warn("NO Chance to BUY_SELL, current status: ", g.basestock_pool[index].status)
        return
    
	# 每次交易量为持仓量的1/4
    amount = 0.25 * context.portfolio.positions[stock].total_amount
    
	
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)
        #log.info("amount from %d to %d", amount, amount_new)
        amount = amount_new
    
	# 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    buy_stock(context, stock, amount, limit_price, index)
    
	# 以收盘价 + 价差 * expected_revenue 挂单卖出
    yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue
    sell_stock(context, stock, amount, limit_price, index)
	
	#更新交易状态
    g.basestock_pool[index].status = Status.BUYING_SELLING
    
# 计算当前时间点，是开市以来第几分钟   
def get_minute_count(context):
    '''
     9:30 -- 11:30
     13:00 --- 15:00
     '''
    current_hour = context.current_dt.hour
    current_min  = context.current_dt.minute
    
    if current_hour < 12:
        minute_count = (current_hour - 9) * 60 + current_min - 29
    else:
        minute_count = (current_hour - 13) * 60 + current_min + 120

    return minute_count
  
# 获取89分钟内的最低价，不足89分钟，则计算到当前时间点
def update_89_lowest(context):
    minute_count = get_minute_count(context)
    if minute_count > 89:
        minute_count = 89
    for i in range(g.position_count):
        low_df = get_price(g.basestock_pool[i].stock, count = minute_count, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        g.basestock_pool[i].lowest_89 = low_df.sort(['close'], ascending = True).iat[0,0]
        
# 获取233分钟内的最高价，不足233分钟，则计算到当前时间点		
def update_233_highest(context):
    minute_count = get_minute_count(context)
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
        if (status != Status.INIT) and (Status != Status.NONE) and (sell_order_id != -1) and (buy_order_id != -1):
            sell_order =  orders.get(sell_order_id)
            buy_order = orders.get(buy_order_id)
            
            if (sell_order is not None) and (buy_order is not None):
                if sell_order.status == OrderStatus.held and buy_order.status == OrderStatus.held:
                    g.basestock_pool[i].sell_order_id = -1
                    g.basestock_pool[i].buy_order_id = -1
                    g.basestock_pool[i].status = Status.INIT  #一次完整交易（买/卖)结束，可以进行下一次交易
                elif Status == Status.BUYING_SELLING and buy_order.status == OrderStatus.held:
                    g.basestock_pool[i].status = Status.BOUGHT_SELLING
                elif Status == Status.SELLING_BUYING and sell_order.status == OrderStatus.held:
                    g.basestock_pool[i].status = Status.SOLD_BUYING
        # 每天14点后， 不再进行新的买卖
        if hour == 14 and g.basestock_pool[i].status == Status.INIT:
            g.basestock_pool[i].status = Status.NONE
            
        
            
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
    
	# 更新89分钟内的最低收盘价，不足89分钟，则按到当前时间的最低收盘价
    update_89_lowest(context)
	
	# 更新233分钟内的最高收盘价，不足233分钟，则按到当前时间的最高收盘价
    update_233_highest(context)
    
    # 根据订单状态来更新，如果交易均结束（买与卖均成交），则置为INIT状态，表示可以再进行交易
    update_socket_statue(context)
    
    
    
    # 因为要计算移动平均线，所以每天前4分钟，不做交易
    if get_minute_count(context) < 4:
        return
		
		
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号
    for i in range(g.position_count):
        stock = g.basestock_pool[i].stock
        lowest_89 = g.basestock_pool[i].lowest_89
        highest_233 = g.basestock_pool[i].highest_233
		
		# 如果在开市前几分钟，价格不变化，则求突破线时，会出现除数为0，如果遇到这种情况，表示不会有突破，所以直接过掉
        if lowest_89 == highest_233:
            continue
		
		#求取当前是否有突破
        
        close_m = get_price(stock, count = 4, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        close =  np.array([close_m.iat[0,0], close_m.iat[1,0], close_m.iat[2,0], close_m.iat[3,0]]).astype(float)
        for j in range(4):
            close[j] = ((close[j] - lowest_89) * 1.0 / (highest_233 - lowest_89)) * 4
        operator_line =  ta.MA(close, 4)

        log.info("股票代码：%s, 前一分钟操盘线值: %f, 当前操作线值: %f, 两者之差的绝对值: %f", stock,
                g.basestock_pool[i].operator_value, operator_line[3], abs(g.basestock_pool[i].operator_value - operator_line[3]))
        
		# 买入信号产生
        if g.basestock_pool[i].operator_value < 0.1 and operator_line[3] > 0.1 and g.basestock_pool[i].operator_value != 0.0:
            log.info("WARNNIG: Time: %s, BUY SIGNAL for %s, from %f to %f, close_price: %f", 
                    str(context.current_dt), stock, g.basestock_pool[i].operator_value, operator_line[3], close_m.iat[3,0])
            buy_sell(context, stock, close_m.iat[3,0], i)
		# 卖出信息产生
        elif g.basestock_pool[i].operator_value > 3.9 and operator_line[3] < 3.9:
            log.info("WARNNING: Time: %s, SELL SIGNAL for %s, from %f to %f, close_price: %f", 
                    str(context.current_dt), stock, g.basestock_pool[i].operator_value, operator_line[3], close_m.iat[3,0])
            sell_buy(context, stock, close_m.iat[3,0], i)
			
		# 记录当前操盘线值
        g.basestock_pool[i].operator_value = operator_line[3]
        
        
