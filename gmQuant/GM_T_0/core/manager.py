from gm.api import *

from gmQuant.GM_T_0.model.BaseStock import Status, T_0, BaseStock, Type, MAX_STOCK_COUNT
from gmQuant.GM_T_0.strategy.buy_sell import buy_signal, sell_stock, reset_position
from gmQuant.GM_T_0.strategy.signal_generator import evaluate_activeVolBuy, g_signal_buy_dict
from gmQuant.GM_T_0.utils.log import logger


def init(context):
    logger.info("---> 策略初始化 @ %s", str(context.now))
    schedule(schedule_func=before_trading, date_rule='1d', time_rule="09:20:00")
    schedule(schedule_func=after_trading, date_rule='1d', time_rule="15:30:00")
    """
    context.client_symbol_dict = {
        "SZSE.002506": 1000}
    """
    context.client_symbol_dict = {
        "SZSE.002506": 3000,
        "SHSE.600703": 3000,
        "SZSE.300059": 3000,
        "SHSE.600206": 3000,
        "SZSE.002281": 3000,
        "SHSE.600340": 3000,
        "SZSE.002092": 3000,
        "SZSE.002440": 3000,
        "SHSE.600897": 3000,
        "SZSE.000063": 3000}

    context.freq = "60s"
    context.count = 50
    context.basestock_pool = []
    context.first_run = True
    context.T_0 = T_0.Open  # 如果只看持仓收益，将其置为T_0.close

    context.repeat_signal_count = 0
    context.reset_order_count = 0
    context.success_count = 0
    # 时间差止损，如果设置大于240， 意味着不使用时间差止损
    context.DELTA_MINITE = 10000

    # 价格差止损，如果设置大于0.1， 意味着不使用价格差止损
    context.DELTA_PRICE = 0.020

    # 每次调整的比例
    context.adjust_scale = 0.25

    # 期望收益率
    context.expected_revenue = 0.010

    context.lastday = ""
    context.today = ""
    get_stocks_by_client(context)
    logger.info("策略初始化完成")


def get_stocks_by_client(context):
    """
    直接从客户得到股票列表
    """
    select_count = 0
    for sym, pos in context.client_symbol_dict.items():
        stock_obj = BaseStock(sym, 0, Status.INIT, pos, -1, -1, Type.NONE)
        logger.info(stock_obj)
        subscribe(symbols=sym, frequency='1m', count=context.count)
        context.basestock_pool.append(stock_obj)
        select_count += 1

    if select_count < MAX_STOCK_COUNT:
        context.position_count = select_count
    else:
        context.position_count = MAX_STOCK_COUNT


# 在每天交易开始时，将状态置为可交易状态
def before_trading(context):
    for s in context.basestock_pool:
        s.cleanup()

    context.repeat_signal_count = 0
    context.reset_order_count = 0
    context.success_count = 0

    logger.info("每日初始化")


def on_bar(context, bars):
    context.today = bars[0].bob.strftime('%Y-%m-%d')
    if context.first_run is True:
        logger.info("开始建仓===========================================================================")
        for stock in context.basestock_pool:
            order_volume(symbol=stock.symbol, volume=stock.position, side=OrderSide_Buy, order_type=OrderType_Market,
                         position_effect=PositionEffect_Open)
            logger.info("股票:\t%s 买入成功", stock.symbol)
        logger.info("结束建仓===========================================================================")

        context.first_run = False
        return

    if context.T_0 == T_0.Close:
        """
        关闭T_0，只测试持仓收益
        """
        logger.info("close T_0")
        return

    if context.lastday is "":
        return

    hour = context.now.hour
    minute = context.now.minute

    # 14点50分钟后，强制恢复仓位
    if hour == 14 and minute == 50:
        # reset_position(context)
        return

    # 14点40分钟后， 不再有新的交易
    if hour == 14 and minute >= 40:
        return

    # 1. 循环股票列表，看当前价格是否有买入或卖出信号
    for stock in context.basestock_pool:
        # 每天14点后， 不再进行新的买卖
        if hour == 14 and stock.status == Status.INIT:
            stock.status = Status.NONE

        if stock.status == Status.NONE:
            continue

        count_number = context.count
        if count_number > context.count:
            logger.info("context.count: %d, current count: %d", context.count, count_number)
            count_number = context.count

        df = context.data(symbol=stock.symbol, frequency='60s',
                          count=count_number, fields='close, volume')

        np_close = []
        vol = []

        for k in range(count_number):
            np_close.append(df.iat[k, 0])
            vol.append(df.iat[k, 1])

        evaluate_activeVolBuy(np_close, vol)

        if g_signal_buy_dict['signal_netVol_buySell'] == 1:
            buy_signal(context, stock, np_close[count_number - 1])
            g_signal_buy_dict['signal_netVol_buySell'] = 0


def on_execution_report(context, execrpt):
    if context.first_run is True:
        return

    if execrpt.exec_type == ExecType_Trade and execrpt.side == OrderSide_Buy:
        logger.info("T_0: [买完再卖] %s 委托买入股票: %s, 交易量: %d, 委托成交价格:%f, 成功",
                    context.now, execrpt.symbol, execrpt.volume, execrpt.price)
        for stock in context.basestock_pool:
            if stock.symbol == execrpt.symbol:
                sell_stock(stock, execrpt.volume, stock.delay_price)
                break

    elif execrpt.exec_type == ExecType_Trade and execrpt.side == OrderSide_Sell:
        context.success_count += 1
        for stock in context.basestock_pool:
            if stock.symbol == execrpt.symbol:
                stock.status = Status.INIT
                logger.info("T_0: [先买后卖成功] %s 委托卖出股票: %s, 交易量: %d, 委托成交价格:%f, 成功",
                            context.now, execrpt.symbol, execrpt.volume, execrpt.price)
                logger.info("===========================================================================")
                break


def after_trading(context):
    context.T_0 = T_0.Open

    logger.info("===========================================================================")
    logger.info("[%s 统计数据]成功交易次数:\t%d, 重复信号交易次数:\t%d, 收盘前强制交易次数:\t%d",
                context.now, context.success_count, context.repeat_signal_count, context.reset_order_count)
    for pos in context.account().positions():
        logger.info(pos)
    logger.info("===========================================================================")
    context.lastday = context.now.strftime('%Y-%m-%d')
    print(context.now)


if __name__ == '__main__':
    print("start")
    run(strategy_id='1c61a610-fdfd-11e7-974a-00ffaabbccdd',
        filename='manager.py',
        mode=MODE_BACKTEST,
        backtest_adjust=ADJUST_PREV,
        backtest_initial_cash=30000000,
        backtest_commission_ratio=0.0001,
        token='f1b42b8ab54bb61010b685eac99765b28209c3e0',
        backtest_start_time='2017-06-19 09:00:00',
        backtest_end_time='2017-06-23 16:00:00')
    print("end")
