from jqdata import *
import numpy as np
import talib


def initialize(context):
    
    # 获得沪深300的股票列表, 5天波动率大于2%，单价大于10.00元, 每标的买入100万元

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


