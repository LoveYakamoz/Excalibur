from jqdata import *
import numpy as np
import pandas as pd
import talib


def initialize(context):
    log.info("---> initialize @ %s" % (str(context.current_dt))) 
    g.basestock_df = pd.DataFrame(columns=("stock", "close", "min_vol", "max_vol"))
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
                g.basestock_df.loc[g.count] = [stock, df.ix[5, 'close'], min_vol, max_vol]
                g.count += 1
            else:
                pass
        else:
            pass
        
    print g.basestock_df, g.count

    
    # 设置基准
    set_benchmark('000300.XSHG')
    set_option('use_real_price', True)
    pass

def process_initialize(context):
    pass


def before_trading_start(context):
    pass


def handle_data(context, data):
    # 0. 购买30支股票
    if g.firstrun is True:
        for i in range(g.position_count):
            print "Buy[%d]---> stock: %s, value: %d" % (i + 1, g.basestock_df.ix[i, 0], g.first_value)
            #order_value(g.basestock_df.ix[i, 0], 1000000)
        g.firstrun = False
    
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号


def after_trading_data(context):
    # 每天记录其MA
    pass


