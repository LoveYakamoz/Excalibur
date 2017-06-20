from jqdata import *
import numpy as np
import pandas as pd
import talib as ta


def initialize(context):
    log.info("---> initialize @ %s" % (str(context.current_dt))) 
    g.basestock_df = pd.DataFrame(columns=("stock", "close", "min_vol", "max_vol", "lowest", "highest", "operator"))
    g.count = 0
    g.firstrun = True
    g.first_value = 1000000
    g.total_value = 100000000
    g.position_count = 30
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
                g.basestock_df.loc[g.count] = [stock, df.ix[5, 'close'], min_vol, max_vol, 0, 0, 0]
                g.count += 1
            else:
                pass
        else:
            pass
    
    if g.count < g.position_count:
        g.position_count = g.count
        
    # 0. 获取VAR1:=LLV(LOW,89); # 89日的最小值
    # 1. 获取VAR2:=HHV(HIGH,233); # 233日的最大值
    for i in range(g.position_count):
        low_df = get_price(g.basestock_df.ix[i, 0], count = 89, end_date=str(context.current_dt), frequency='daily', fields=['low'])
        g.basestock_df.iat[i, 4] = low_df.sort(['low'], ascending = True).iat[0,0]
        
        high_df = get_price(g.basestock_df.ix[i, 0], count = 233, end_date=str(context.current_dt), frequency='daily', fields=['high'])
        g.basestock_df.iat[i, 5] = high_df.sort(['high'], ascending = False).iat[0,0]
        
        #print "stock: %s, lowest_89: %f, highest_233: %f" % (g.basestock_df.ix[i, 0], g.basestock_df.iat[i, 4], g.basestock_df.iat[i, 5])
        
    for i in range(g.position_count):
        stock = g.basestock_df.ix[i, 0]
        lowest_89 = g.basestock_df.iat[i, 4]
        highest_233 = g.basestock_df.iat[i, 5]
        close_m = get_price(stock, count = 4, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        close =  np.array([close_m.iat[0,0], close_m.iat[1,0], close_m.iat[2,0], close_m.iat[3,0]]).astype(float)
        
        for j in range(4):
            close[j] = (close[j] - lowest_89)/(highest_233 - lowest_89)
        operator_line =  ta.MA(close, 4)
        g.basestock_df.iat[i, 6] = operator_line[3]
        
    print g.basestock_df, g.count 
    

    # 设置基准
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    pass

def process_initialize(context):
    pass


def before_trading_start(context):
    # 0. 更新89日的最小值
    # 1. 更新233日的最大值
    log.info("***************************************************************************")
    log.info("before_trading_start: update lowest_89 and highest_233")
    for i in range(g.position_count):
        low_df = get_price(g.basestock_df.ix[i, 0], count = 1, end_date=str(context.current_dt), frequency='daily', fields=['low'])
        if g.basestock_df.iat[i, 4] > low_df.iat[0,0]:
            log.info("update: lowest_89, stock: %s from %f to %f", g.basestock_df.ix[i, 0], g.basestock_df.iat[i, 4], low_df.iat[0,0])
            g.basestock_df.iat[i, 4] = low_df.iat[0,0]
        
        high_df = get_price(g.basestock_df.ix[i, 0], count = 1, end_date=str(context.current_dt), frequency='daily', fields=['high'])
        if g.basestock_df.iat[i, 5] < high_df.iat[0,0]:
            log.info("update: highest_233, stock: %s from %f to %f", g.basestock_df.ix[i, 0], g.basestock_df.iat[i, 5], high_df.iat[0,0])
            g.basestock_df.iat[i, 5] = high_df.iat[0,0]
        
def buy_stock(context, stock, amount, limit_price):
    buy_order = order(stock, amount, LimitOrderStyle(limit_price))
    #log.info("status: %d", buy_order.status)
    log.info("buy_order: ", buy_order)
    
def sell_stock(context, stock, amount, limit_price):
    sell_order = order(stock, -amount, LimitOrderStyle(limit_price))
    log.info("sell_order: ", sell_order)
    
def sell_buy(context, stock, close_price):
    
    amount = 0.25 * context.portfolio.positions[stock].total_amount
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)  +  100
        log.info("amount from %d to %d", amount, amount_new)
        amount = amount_new

    limit_price = close_price + 0.01

    sell_stock(context, stock, amount, limit_price)
    
    yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    
    limit_price = close_price - yesterday.iat[0, 0] * 0.06
    buy_stock(context, stock, amount, limit_price)
    
    
def buy_sell(context, stock, close_price):
    amount = 0.25 * context.portfolio.positions[stock].total_amount
    
    if amount % 100 != 0:
        amount_new = amount - (amount % 100)  +  100
        log.info("amount from %d to %d", amount, amount_new)
        amount = amount_new
    
    current_data = get_current_data()

    limit_price = close_price - 0.01
    buy_stock(context, stock, amount, limit_price)
    
    yesterday = get_price(stock, count = 1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
    limit_price = close_price - yesterday.iat[0, 0] * 0.06
    sell_stock(context, stock, amount, limit_price)
    
def handle_data(context, data):
    # 0. 购买30支股票
    if str(context.run_params.start_date) ==  str(context.current_dt.strftime("%Y-%m-%d")):
        if g.firstrun is True:
            for i in range(g.position_count):
                log.info("Buy[%d]---> stock: %s, value: %d", i + 1, g.basestock_df.ix[i, 0], g.first_value)
                myorder = order_value(g.basestock_df.ix[i, 0], 1000000)
                log.info(myorder)
            g.firstrun = False
        return
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    
        #强制买回
    
    if hour >= 14:
        # 不再产生新的交易
        return
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号
    for i in range(g.position_count):
        stock = g.basestock_df.ix[i, 0]
        lowest_89 = g.basestock_df.iat[i, 4]
        highest_233 = g.basestock_df.iat[i, 5]
        
        close_m = get_price(stock, count = 4, end_date=str(context.current_dt), frequency='1m', fields=['close'])
        
        close =  np.array([close_m.iat[0,0], close_m.iat[1,0], close_m.iat[2,0], close_m.iat[3,0]]).astype(float)
        for j in range(4):
            close[j] = (close[j] - lowest_89)/(highest_233 - lowest_89)
        operator_line =  ta.MA(close, 4)
        
        if g.basestock_df.iat[i, 6] < 0.1 and operator_line[3] > 0.1 and g.basestock_df.iat[i, 6] != 0.0:
            log.info("WARNNIG: Time: %s, BUY SIGNAL for %s, from %f to %f, close_price: %f", str(context.current_dt), stock, g.basestock_df.iat[i, 6], operator_line[3], close_m.iat[3,0])
            buy_sell(context, stock, close_m.iat[3,0])
        elif g.basestock_df.iat[i, 6] > 3.9 and operator_line[3] < 3.9:
            log.info("WARNNING: Time: %s, SELL SIGNAL for %s, from %f to %f, close_price: %f", str(context.current_dt), stock, g.basestock_df.iat[i, 6], operator_line[3], close_m.iat[3,0])
            sell_buy(context, stock, close_m.iat[3,0])
        g.basestock_df.iat[i, 6] = operator_line[3]
        
            
def after_trading_data(context):
    
    pass


