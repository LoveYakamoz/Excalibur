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
    2、买入持仓股中均线依旧保持多头排列的个股，如果持仓个股中均线多头少于10个，则添加当天均线变成多头的个股（按流通市值排列）。
      如果两者数量超过10只，则当日均线变成多头的个股按流通市值排序，
      总计不超过10只个股；如果两者数量仍少于10只，那么就按实际可买数量平均分配资金；

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
import talib
import jqdata
import pandas as pd


def is_junxianduotou(context, stock, delta=0):
    '''
    判断个股是否多头排列
    '''
    ma5 = 0
    ma10 = 0
    ma20 = 0
    
    df = get_price(stock, count=30, end_date = str(context.current_dt), frequency='daily', fields=['close'])
    current_close = df['close'][0+delta]

    for i in range(5):
        ma5 += df['close'][-i + delta]
    ma5 = ma5 * 1.0 / 5

    for i in range(10):
        ma10 += df['close'][-i + delta]
    ma10 = ma10 * 1.0 / 10

    for i in range(20):
        ma20 += df['close'][-i + delta]
    ma20 = ma20 * 1.0 / 20

    if current_close > ma5 and ma5 > ma10 and ma10 > ma20:
        log.debug("stock: %s, current: %f, ma5: %f, ma10: %f, ma20: %f",
                 stock, current_close, ma5, ma10, ma20)
        return True
    else:
        return False


def get_chicanghouxuan(context):
    '''
    将多头股票，且满足不停牌，当前价格在跌停与涨停中间， 加入持仓候选队列中
    '''
    current_data = get_current_data()

    for stock in g.gupiaochi:
        if (is_junxianduotou(context, stock) is True
            # and current_data[stock].low_limit < current_data[stock].close < current_data[stock].high_limit
                and not current_data[stock].paused):
            log.info("%s 为多头股票，加入到候选列表中", stock)
            g.chicanghouxuan.append(stock)

def get_buy_list(context):
    '''
    准备买入的股票池
    '''
    # 1. 按照最大买入约束，候选队列股票 ---> 买入队列
    for stock in g.chicanghouxuan:
        g.buy_list.append(stock)
        if len(g.buy_list) >= g.max_chicang_count:  # 达到计划持仓股票支数
            log.warn('已经达到最大持仓股票数，不再增加股票')
            break

    log.info('选入股票:%s', (g.buy_list))

def init_stock_position(context):
    '''
    根据买入列表，进行初始化仓位
    '''

    pass

def initialize(context):
    '''
    初始化模块，设定参数之类，初始化持仓股票队列
    '''
    # 1. 初始化参数
    set_benchmark('000300.XSHG')  # 设定沪深300作为基准
    set_option('use_real_price', True)  # 使用真实价格
    set_slippage(PriceRelatedSlippage(0.01))  # 设定滑点
    # 手续费是：交易成本（买0.03%，卖0.13%   0.001+0.0003
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003,
                             close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    log.set_level('order', 'error')
    log.set_level('strategy', 'info')
    g.chicanghouxuan = []
    g.buy_list = []

    g.max_chicang_count = 10

    g.gupiaochi = get_index_stocks('399300.XSHE')
    # 2. 得到候选股票队列
    get_chicanghouxuan(context)

    # 3. 根据最大持仓股票数约束，将候选股票加入到买入队列
    get_buy_list(context)

    # 4. 根据买入列表，初始化仓位
    init_stock_position(context)

def before_trading_start():
    pass
def get_new_Duotou(context):
    '''
    个股变多头，股票进入多投候选中
    '''
    def is_changeduotou(context, stock):
        '''
        判断个股是否今日变多头排列
        '''
        todayduotou = is_junxianduotou(context, stock)
        yestodayduotou = is_junxianduotou(context, stock, - 1)

        if todayduotou is True and yestodayduotou is False:
            log.info("stock: %s change to Duotou", stock)
            return True
        else:
            return False

    current_data = get_current_data()
    for stock in g.gupiaochi:
        if is_changeduotou(context, stock) is True and not current_data[stock].paused:
        #and curr_data[stock].low_limit < data[stock].close < curr_data[stock].high_limit 
       
            log.info("stock: %s add to candidate list", stock)
            g.chicanghouxuan.append(stock)

def get_sell_scale(context, stock):
    '''
    判断持仓个股卖出的比例
    '''
    ma5 = 0
    ma10 = 0
    ma20 = 0
    
    df = get_price(stock, count=30, end_date = str(context.current_dt), frequency='daily', fields=['close'])
    current_close = df['close'][0]

    for i in range(5):
        ma5 += df['close'][-i]
    ma5 = ma5 * 1.0 / 5

    for i in range(10):
        ma10 += df['close'][-i]
    ma10 = ma10 * 1.0 / 10

    for i in range(20):
        ma20 += df['close'][-i]
    ma20 = ma20 * 1.0 / 20

    if current_close <= ma20:
        return 1.0
    elif current_close <= ma10:
        return 0.75
    elif current_close <= ma5:
        return 0.5
    else:
        return 0
            
def buy_stock(context):
    '''
    根据购买列表，买入股票 
    '''
    if len(g.buy_list) == 0:
        log.error("买入列表为空")
        return

    # TODO: 获取当前可用资金
    current_total_money = xxx
    money_per_stock = current_total_money / len(g.buy_list)
    for stock in g.buy_list:
        buy_order = order_value(stock, money_per_stock)
        if buy_order is not None:
            log.info("股票: %s, 买入%d元成功", stock, money_per_stock)
        else:
            log.error("股票: %s, 买入%d元失败", stock, money_per_stock)


def sell_stock(context, non_duotou_list):
    '''
    将非多头股票分为以下三类，并卖出
        1、股价跌破5日均线，卖出可卖部分的50%；
        2、跌破10日均线，卖出可卖部分75%；
        3、跌破20日均线，全部卖出。
    '''
    for stock in non_duotou_list:
        scale = get_sell_scale(context, stock)
        cur_position = context.portfolio.positions[stock].total_amount
        amount = -1 * cur_position * scale 
        sell_order = order(stock, amount)
        if sell_order is not None:
            log.info("股票: %s, 以%f比例挂单卖出%d成功", stock, scale, amount)
        else:
            log.error("股票: %s, 以%f比例挂单卖出%d失败", stock, scale, amount)
    pass

def get_non_Duotou(context):
    '''
    从持仓股票中，获得非多头股票列表，并把多头股票加入到修选队列
    '''
    non_duotou_list = []
    # TODO: 获取持仓股票列表
    for stock in xxxx:
        if is_junxianduotou(context, stock) == False:
            non_duotou_list.append(stock)
        else:
            g.chicanghouxuan.append(stock)
    return non_duotou_list

def handle_data(context, data):
    '''
    每个交易日的14点30分进行调仓
    '''
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    
    if hour == 14 and minute == 30:
        non_duotou_list = []
        # 1. 得到持仓中的非多头股票列表
        non_duotou_list = get_non_Duotou(context)
        if (len(non_duotou_list) > 0):
            # 2. 获得新的多头股票列表
            get_new_Duotou(context)
            # 3. 获得新的购买股票列表
            get_buy_list(context)
            # 4. 购买新的股票
            buy_stock(context)

            # 5. 卖出持仓中的非多头股票
            sell_stock(context, non_duotou_list)



def after_trading_end(context):
    '''
    每天交易后， 将候选列表及买入列表清空
    '''
    g.chicanghouxuan = []
    g.buy_list = []


def no_paused_no_ST(stock_list):
    '''
    去除停牌和ST
    '''
    current_data = get_current_data()
    return [stock for stock in stock_list if
            not current_data[stock].paused
            and not current_data[stock].is_st
            and 'ST' not in current_data[stock].name
            and '*' not in current_data[stock].name
            and '退' not in current_data[stock].name]


def sort_by_market_cap(stock_list):
    '''
    按流通市值升序排列
    '''
    varDict = {}
    for stk in stock_list:
        q = query(valuation).filter(valuation.code == stk)
        df = get_fundamentals(q, g.today)
        varDict[stk] = df['market_cap'][0]
    tmpDict = sorted(varDict.iteritems(), key=lambda d: d[1], reverse=True)
    tmpList = [i[0] for i in tmpDict]

    # 是否反序，有这句买入市值高的优先，反之市值低的优先
    # tmpList.reverse()

    # 返回降序
    return tmpList

def adjust_position(context, buy_stocks):
    '''
    买入mairu列表中的股票，买入金额按现有资金的50%
    '''
    gegumairujiner = context.portfolio.total_value * 0.5 / g.mairushuliang
    for stock in g.mairu:
        order_target_value(stock, gegumairujiner)

    sell_scale = get_sell_scale(context, stock)
    for stock in context.portfolio.positions.keys():
        order_target_value(stock, sell_scale)