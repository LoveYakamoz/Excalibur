from jqdata import *
import numpy as np
import talib


def initialize(context):
    log.info("---> initialize @ %s" % (str(context.current_dt))) 

    # 获得沪深300的股票列表, 5天波动率大于2%，单价大于10.00元, 每标的买入100万元
    stock_list = get_index_stocks('399300.XSHE')
    for stock in stock_list:

    # 设置基准
    set_benchmar('000300.XSHG')
    set_option('use_real_price', True)
    pass

def process_initialize(context):
    pass


def before_trading_start(context):
    pass


def handle_data(context, data):
    # 1. 循环股票列表，看当前价格是否有买入或卖出信号

    pass


def after_trading_data(context):
    # 每天记录其MA
    pass


