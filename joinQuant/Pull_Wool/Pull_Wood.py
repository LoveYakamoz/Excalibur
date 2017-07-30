import talib
import jqdata

'''
薅羊毛策略
一、选股标的：行业龙头股和绩优股（暂时用沪深300来替代）
    行业龙头标准
        1、静态PE处于行业最低30%；
        2、流通市值处于行业最大30%；
        3、所属行业个股超过10个；
        4、静态PE小于30倍；
    绩优股标准：
        5、流通市值在50亿以上；
        6、静态市盈率低于20倍；
        7、扣非净利润占净利润80%以上；
        8、每个行业最多2个股票（含行业龙头股，多余两个选流通市值比较小的）
二、买入标准：均线多头排列（5日，10日，20日）

三、买入原则:
    1、每天买入可用资金的50%，如果可用资金少于总市值10%，则全部买入；
    2、买入持仓股中均线依旧保持多头排列的个股，如果持仓个股中均线多头少于10个，则添加当天均线变成多头的个股（按流通市值排列）。如果两者数量超过10只，则当日均线变成多头的个股按流通市值排序，总计不超过10只个股；如果两者数量仍少于10只，那么就按实际可买数量平均分配资金；

四、卖出原则：
    1、股价跌破5日均线，卖出可卖部分的50%；
    2、跌破10日均线，卖出可卖部分75%；
    3、跌破20日均线，全部卖出。
五、每天先买后卖
    1、启动时间
    2、列出持仓股中均线多头的股票，放入全局变量g.junxianduotou 
    3、列出股票池中均线变多头的股票，放入全局变量g.junxianbianduotou
    4、g.mairu = g.junxianduotou + g.junxianbianduotou 最多不超过10个股票
    5、买入股票
    6、卖出持仓中不在g.mairu股票池的股票，卖出比例通过调用maichubili卖出

'''
'''
================================================================================
初始化模块，设定参数之类
================================================================================
'''
#初始化函数，设定要操作的股票、基准等等
def initialize(context):
    
    
    # 设定沪深300作为基准
    set_benchmark('000300.XSHG')
    # 使用真实价格
    set_option('use_real_price', True)
    # 设定滑点
    set_slippage(PriceRelatedSlippage(0.01))
    # 手续费是：交易成本（买0.03%，卖0.13%   0.001+0.0003
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003, close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')

    # log级别设定，只显示错误
    log.set_level('order', 'error')
    
    #持仓股，持仓股中仍多头排列，今日变成多头排列
    g.chicang = []
    g.chicanghouxuan = []
    g.duotouhouxuan = []
    g.mairu = []
    g.mairu = get_mairu
    g.zuidachicang = 10
    g.mairushuliang = 10

    
    g.gupiaochi = get_index_stocks('399300.XSHE')
    
def handle_data(context, data):
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    if hour == 14 and minute == 30:
       adjust_position(context,data)
    
# 准备买入的股票池        
def get_mairu(context, data):
    dst_Stocks = []
    current_data = get_current_data()
    dst_Stocks = get_chicangduotou()
    for stk in get_duotouhouxuan():
        dst_Stocks.append(stk)
        if len(dst_Stocks)>=g.zuidachicang:   #达到计划持仓股票支数
            break
        continue
    log.info('选入股票:%s' % (dst_Stocks))
    g.mairushuliang = len(dst_Stocks())
    return dst_Stocks
 
#如果持仓股多头，股票进入持仓候选中    
def get_chicangduotou(context,data):
    for stock in context.portfolio.positions.keys():
        if get_junxianduotou == 1 and curr_data[stock].low_limit < data[stock].close < curr_data[stock].high_limit and not current_data[stock].paused :
            g.chicanghouxuan.append(stock)
        continue

#如果个股变多头，股票进入多投候选中    
def get_duotouhouxuan(context,data):
    for stock in g.gupiaochi:
        if get_junxianbianduotou == 1 and curr_data[stock].low_limit < data[stock].close < curr_data[stock].high_limit and not current_data[stock].paused :
            g.duotouhouxuan.append(stock)
        continue
    
    
#判断个股是否多头排列
def get_junxianduotou(context,stock):
    grid = get_price(security, 30 , unit='1d',
            fields=['close'],skip_paused=True, 
            df=True, fq='pre')
    todayma5 = grid[-4:].mean()
    todayma10 = grid[-9:].mean()
    todayma20 = grid[-19:].mean()
    if  grid.close> todayma5 and todayma5 > todayma10 and todayma10 > todayma20:
        return 1
    else:
        return 0
        
#判断个股是否今日变多头排列
def get_junxianbianduotou(context,stock):
    grid = get_price(security, 30 , unit='1d',
            fields=['close'],skip_paused=True, 
            df=True, fq='pre')
    todayma5 = grid[-4:].mean()
    todayma10 = grid[-9:].mean()
    todayma20 = grid[-19:].mean()
    
    yestodayma5 = grid[-5:-1].mean()
    yestodayma10 = grid[-10:-1].mean()
    yestodayma20 = grid[-20:-1].mean()
    
    todayduotou = grid.close > todayma5 and todayma5 > todayma10 and todayma10 > todayma20
    yestodayduotou = grid[-1] > yestodayma5 and yestodayma5 > yestodayma10 and yestodayma10 > yestodayma20
    
    if todayduotou and not(yestodayduotou):
        return 1
    else:
        return 0
    
#判断持仓个股卖出的比例
def get_maichubili(context,stock):
    grid = get_price(security, 30 , unit='1d',
            fields=['close'],skip_paused=True, 
            df=True, fq='pre')
    todayma5 = grid[-4:].mean()
    todayma10 = grid[-9:].mean()
    todayma20 = grid[-19:].mean()
    if grid <= todayma20:
        return 1
    elif grid <= todayma10:
        return 0.75
    elif grid <= todayma5:
        return 0.5
    else:
        return 0


 # 去除停牌和ST    
def no_paused_no_ST(stock_list):
    current_data = get_current_data()
    return [stock for stock in stock_list if 
    not current_data[stock].paused 
    and not current_data[stock].is_st
    and 'ST' not in current_data[stock].name
    and '*' not in current_data[stock].name
    and '退' not in current_data[stock].name]
    
def sort_by_market_cap(stks):
    # 按流通市值排序，大的在后
    varDict = {}
    for stk in stks:
        q = query(valuation).filter(valuation.code == stk)
        df = get_fundamentals(q,g.today)
        varDict[stk] = df['market_cap'][0]
    tmpDict = sorted(varDict.iteritems(),key=lambda d:d[1], reverse = True)
    tmpList = [i[0] for i in tmpDict]
    
    # 是否反序，有这句买入市值高的优先，反之市值低的优先
    # tmpList.reverse()

    # 返回降序
    return tmpList     
    
def adjust_position(context, buy_stocks):
    #买入mairu列表中的股票，买入金额按现有资金的50%
    gegumairujiner = context.portfolio.total_value*0.5 / g.mairushuliang
    for stock in g.mairu:
        order_target_value(stock, gegumairujiner)
    
    maichubili = get_maichubili
    for stock in context.portfolio.positions.keys():
        order_target_value(stock, maichubili)
    
#判断持仓个股卖出的比例-杨佩版    
def get_sell_scale(context, stock):

    current_close = get_price(stock, count = 1, end_date = str(context.current_dt), frequency='1m', fields=['close'],skip_paused=True, fq='pre')
    grid = get_price(stock, count = 30, end_date = str(context.current_dt), frequency='daily', fields=['close'],skip_paused=True, fq='pre')
   
        
    todayma5 = grid[-5:].mean()
    todayma10 = grid[-10:].mean()
    todayma20 = grid[-20:].mean()
    
    log.info(grid)
    log.info("current_close: %f, ma20: %f, ma10: %f, ma5: %f", current_close['close'], todayma20['close'], todayma10['close'], todayma5['close'])
    if current_close.iat[0,0] <= todayma20['close']:
        return 1.0
    elif current_close.iat[0,0] <= todayma10['close']:
        return 0.75
    elif current_close.iat[0,0] <= todayma5['close']:
        return 0.5
    else:
        return 0   
    
