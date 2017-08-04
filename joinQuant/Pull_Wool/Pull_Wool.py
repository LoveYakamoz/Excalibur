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
    2、列出持仓股中均线多头的股票，放入全局变量g.junxianbianduotou 
    3、列出股票池中均线变多头的股票，放入全局变量g.junxianbianduotou
    4、g.buy_list = g.junxianbianduotou 最多不超过10个股票 （候选从2，3步骤得到，但按市值排序时，如何搞？）
    5、买入股票
    6、卖出持仓中不在g.buy_list 股票池的股票，卖出比例通过调用sell_scale卖出

'''
import talib
import jqdata
import pandas as pd


def initialize(context):
    '''
    初始化模块，设定参数之类，初始化持仓股票队列
    '''
    # 0. 待调整的参数
    g.max_chicang_count = 10
    g.min_value_scale = 0.1
    g.sell_scale = [0.5, 0.75, 1]
    g.ma_scale = [5, 10, 20]

    # 1. 初始化参数
    set_benchmark('000300.XSHG')  # 设定沪深300作为基准
    set_option('use_real_price', True)  # 使用真实价格
    set_slippage(PriceRelatedSlippage(0.01))  # 设定滑点
    # 手续费是：交易成本（买0.03%，卖0.13%   0.001+0.0003
    set_order_cost(OrderCost(open_tax=0, close_tax=0.001, open_commission=0.0003,
                             close_commission=0.0003, close_today_commission=0, min_commission=5), type='stock')
    log.set_level('order', 'error')
    log.set_level('strategy', 'info')

    g.stock_pool = get_init_stock_list()
    g.stock_pool = sort_by_market_cap(context, g.stock_pool)

    # 2. 得到候选股票队列
    g.candidate = []
    get_candidate(context)

    # 3. 根据最大持仓股票数约束，将候选股票加入到买入队列
    g.buy_list = []
    get_buy_list(context)

    # 4. 根据买入列表，初始化仓位
    init_stock_position(context)
    g.first_init = True

    log.info("---------------->Init OK")


def before_trading_start(context):
    if g.first_init is True:
        pass
    else:
        get_candidate(context)
    g.first_init = False

    log.info("---------------->Before trading process OK")


def handle_data(context, data):
    '''
    每个交易日的14点30分进行调仓
    '''
    hour = context.current_dt.hour
    minute = context.current_dt.minute

    if hour == 14 and minute == 30:
        non_duotou_list = []
        # 1. 将持仓中股票分为多头与非多头股票列表
        non_duotou_list = get_divided_Duotou(context)

        if (len(non_duotou_list) > 0 and len(context.portfolio.positions) > 0) or (len(context.portfolio.positions) == 0):
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
    g.candidate = []
    g.buy_list = []

    log.info("===========================Stat=============================")
    log.info("当前总收益: %f, 本金: %f, 盈利: %f, 盈亏比率: %f",
             context.portfolio.total_value,
             context.portfolio.starting_cash,
             context.portfolio.total_value - context.portfolio.starting_cash,
             context.portfolio.total_value / context.portfolio.starting_cash * 100
             )
    log.info("当前可用资金: %f", context.portfolio.available_cash)
    log.info("当前持仓股票%d个", len(context.portfolio.positions.keys()))
    log.info("当前持仓股票分别为：", context.portfolio.positions.keys())
    log.info("============================================================")


def is_junxianduotou(context, stock, delta=0):
    '''
    判断个股是否多头排列
    '''
    ma5 = 0
    ma10 = 0
    ma20 = 0

    df = get_price(stock, count=g.ma_scale[2] + 10, end_date=str(
        context.current_dt), frequency='daily', fields=['close'])
    current_close = df['close'][0 + delta]

    for i in range(g.ma_scale[0]):
        ma5 += df['close'][-i + delta]
    ma5 = ma5 * 1.0 / g.ma_scale[0]

    for i in range(g.ma_scale[1]):
        ma10 += df['close'][-i + delta]
    ma10 = ma10 * 1.0 / g.ma_scale[1]

    for i in range(g.ma_scale[2]):
        ma20 += df['close'][-i + delta]
    ma20 = ma20 * 1.0 / g.ma_scale[2]
    log.debug("stock: %s, current: %f, ma5: %f, ma10: %f, ma20: %f",
              stock, current_close, ma5, ma10, ma20)
    if current_close > ma5 and ma5 > ma10 and ma10 > ma20:
        return True
    else:
        return False

def is_not_limitup_limitdown_pause(stock,):
    '''
    判断当前是否涨跌停或停牌
    '''

    df = get_price(stock, count=1, end_date=str(
        context.current_dt), frequency='1m', fields=['close'])
    current_close = df['close'][0]
    
    current_data = get_current_data()

    if (current_data[stock].low_limit < current_close < current_data[stock].high_limit) and (not current_data[stock].paused):
        return True
    else:
        return False

def get_candidate(context):
    '''
    将多头股票，且满足不停牌，当前价格在跌停与涨停中间， 加入持仓候选队列中
    '''
    for stock in g.stock_pool:
        if (is_junxianduotou(context, stock) is True
                and is_not_limitup_limitdown(stock)
                and g.candidate.count(stock) == 0):
            log.debug("%s 为多头股票，加入到候选列表中", stock)
            g.candidate.append(stock)


def get_buy_list(context):
    '''
    准备买入的股票池
    '''
    # 0. 获得当前持仓数量
    current_stock_count = len(context.portfolio.positions)
    log.info("当前持仓数量为%d个", current_stock_count)

    # 1. 按照最大买入约束，候选队列股票 ---> 买入队列
    for stock in g.candidate:
        if len(g.buy_list) >= g.max_chicang_count - current_stock_count:  # 达到计划持仓股票支数
            log.warn('已经达到最大持仓股票数，不再增加股票')
            break
        else:
            g.buy_list.append(stock)
    log.info('选入股票:', (g.buy_list))


def init_stock_position(context):
    '''
    根据买入列表，进行初始化仓位
    '''
    buy_stock(context)


def get_init_stock_list():
    '''
    行业龙头股和绩优股（暂时用沪深300来替代）
    如果使用股票列表，直接定义一个列表，返回即可。
    如：
    return ['xxxx.XSHE', 'yyyy.XSHE', 'zzzz.XSHE']
    '''
    return get_index_stocks('399300.XSHE')


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
            log.debug("stock: %s change to Duotou", stock)
            return True
        else:
            return False

    current_data = get_current_data()
    for stock in g.stock_pool:
        if is_changeduotou(context, stock) is True and is_not_limitup_limitdown(stock):
            log.debug("stock: %s add to candidate list", stock)
            if g.candidate.count(stock) == 0:
                g.candidate.append(stock)


def get_sell_scale(context, stock):
    '''
    判断持仓个股卖出的比例
    '''
    ma5 = 0
    ma10 = 0
    ma20 = 0

    df = get_price(stock, count=g.ma_scale[2] + 10, end_date=str(
        context.current_dt), frequency='daily', fields=['close'])
    current_close = df['close'][0]

    for i in range(g.ma_scale[0]):
        ma5 += df['close'][-i]
    ma5 = ma5 * 1.0 / g.ma_scale[0]

    for i in range(g.ma_scale[1]):
        ma10 += df['close'][-i]
    ma10 = ma10 * 1.0 / g.ma_scale[1]

    for i in range(g.ma_scale[2]):
        ma20 += df['close'][-i]
    ma20 = ma20 * 1.0 / g.ma_scale[2]

    if current_close <= ma20:
        return g.sell_scale[2]
    elif current_close <= ma10:
        return g.sell_scale[1]
    elif current_close <= ma5:
        return g.sell_scale[0]
    else:
        log.warn("stock: %s, current: %f, ma5: %f, ma10: %f, ma20: %f",
                 stock, current_close, ma5, ma10, ma20)
        return 0


def buy_stock(context):
    '''
    根据购买列表，买入股票 
    '''
    if len(g.buy_list) == 0:
        log.warn("买入列表为空")
        return

    available_cash = context.portfolio.available_cash
    total_value = context.portfolio.total_value
    if available_cash >= total_value * g.min_value_scale:
        available_cash = available_cash * 0.5

    money_per_stock = available_cash / len(g.buy_list)
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
        if scale == 0:
            log.warn("%s 虽然不是多头，但是当前价格未跌破各均线，所以不用卖出", stock)
            continue

        cur_position = context.portfolio.positions[stock].total_amount
        amount = -1 * cur_position * scale

        sell_order = order(stock, amount)

        if sell_order is not None:
            log.info("股票: %s, 以%f比例挂单卖出%d成功", stock, scale, amount)
        else:
            log.error("股票: %s, 以%f比例挂单卖出%d失败", stock, scale, amount)
    pass


def get_divided_Duotou(context):
    '''
    从持仓股票中，获得非多头股票列表，并把多头股票加入到修选队列
    '''
    non_duotou_list = []

    for stock in context.portfolio.positions.keys():
        if is_junxianduotou(context, stock) == False:
            non_duotou_list.append(stock)
        else:
            if g.candidate.count(stock) == 0:
                g.candidate.append(stock)
    return non_duotou_list


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


def sort_by_market_cap(context, stock_list):
    '''
    按流通市值升序排列
    '''
    tmpList = []

    stock_list = no_paused_no_ST(stock_list)

    df = get_fundamentals(
        query(valuation).filter(valuation.code.in_(stock_list)
                                ).order_by(
            valuation.market_cap.asc()
        ),
        date=context.current_dt.today())

    for i in range(len(df)):
        tmpList.append(df['code'][i])

    return tmpList
