import tushare ts
import numpy as np
import pandas as pd
import talib as ta
from math import isnan

# 持仓股票池详细信息
g.basestock_pool = ["600446"]
# 上穿及下穿阈值
g.up = 0.1
g.down = 3.9
#MA平均的天数
g.ma_day_count = 4
#每次调整的比例
g.adjust_scale = 0.25 


# 期望收益率
g.expected_revenue = 0.003

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


    
def initialize():
    log.info("---> initialize @ %s" % (str(context.current_dt))) 
    g.repeat_signal_count = 0
    g.reset_order_count = 0
    g.success_count = 0

    # 默认股票池容量
    g.position_count = 1

    
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
        low_df = ts.get_hist_data(g.basestock_pool[i].stock, ktype='1', count = minute_count, end_date=str(context.current_dt))
        g.basestock_pool[i].lowest_89 = min(low_df['low'])
        
# 获取233分钟内的最高价，不足233分钟，则计算到当前时间点
def update_233_highest(context):
    minute_count = get_minute_count(context.current_dt)
    if minute_count > 233:
        minute_count = 233
    for i in range(g.position_count):
        high_df = ts.get_hist_data(g.basestock_pool[i].stock, ktype='1', count = minute_count, end_date=str(context.current_dt))
        g.basestock_pool[i].highest_233 =  max(high_df['high'])
        
def handle_data(context, data):
    hour = context.current_dt.hour
    minute = context.current_dt.minute
        
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
        close_m = get_price(stock, ktype='1', count = g.ma_day_count, end_date=str(context.current_dt))
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

        # 卖出信息产生
        elif g.basestock_pool[i].operator_value > g.down and operator_line[g.ma_day_count-1] < g.down:
            log.info("SELL SIGNAL for %s, from %f to %f, close_price: %f, lowest_89: %f, highest_233: %f", stock, g.basestock_pool[i].operator_value, operator_line[g.ma_day_count-1], close_m.iat[g.ma_day_count-1,0], lowest_89, highest_233)

        # 记录当前操盘线值
        g.basestock_pool[i].operator_value = operator_line[g.ma_day_count-1]

if __name__ == '__main__':
