from math import floor

from gm.api import *

from gmQuant.GM_T_0.utils.log import logger

"""
buy sell信号及操作
"""
from gm.api import order_cancel_all

from gmQuant.GM_T_0.model.BaseStock import Type, Status


def buy_stock(stock, amount, limit_price):
    """
    购买股票，并记录订单号，便于查询订单状态
    :param context:
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    buy_order = order_volume(symbol=stock.symbol, volume=amount,
                             side=PositionSide_Long,
                             order_type=OrderType_Limit,
                             position_effect=PositionEffect_Open,
                             price=limit_price)

    if buy_order is not None:
        stock.buy_price = limit_price
        return True
    else:
        stock.buy_price = 0
        logger.error("买入股票: %s, 以%f价格挂单，买入%d, 失败", stock, limit_price, amount)
        return False


def sell_stock(stock, amount, limit_price):
    """
    卖出股票，并记录订单号，便于查询订单状态
    :param context:
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    sell_order = order_volume(symbol=stock.symbol, volume=amount,
                              side=PositionSide_Short,
                              order_type=OrderType_Limit,
                              position_effect=PositionEffect_Close,
                              price=limit_price)

    if sell_order is not None:
        stock.sell_price = limit_price
        return True
    else:
        stock.sell_price = 0
        return False


def sell_signal(context, stock, close_price):
    if stock.status == Status.WORKING:
        logger.debug("股票: %s, 收到重复卖出信号，但不做交易", stock.symbol)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = context.adjust_scale * stock.position

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01
    logger.info("卖出信号: %f, src_position: %d, amount: %d, price: %f",
                context.adjust_scale, stock.position, amount, limit_price)

    if stock.status == Status.INIT:
        # 以收盘价 - 价差 * expected_revenue 挂单买入
        yesterday = history(symbol=stock, frequency='1d', start_time=context.lastday,
                            end_time=context.today, fields='close', df=True)
        delay_price = close_price - yesterday.iat[0, 0] * context.expected_revenue
        stock.t_0_type = Type.Active_Sell
        stock.delay_amount = amount
        stock.delay_price = delay_price
        stock.status = Status.WORKING  # 更新交易状态

        sell_stock(stock, amount, limit_price)
    else:
        logger.info("股票: %s, 交易状态出错", stock)


def buy_signal(context, stock, close_price):
    if stock.status == Status.WORKING:
        logger.info("%s 股票: %s 收到重复买入信号，但不做交易", context.now, stock.symbol)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = floor(context.adjust_scale * stock.position)

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    logger.info("%s 买入信号: src_position: %d, amount: %d, price: %f", stock.symbol, stock.position, amount, limit_price)

    if stock.status == Status.INIT:
        # 以收盘价 + 价差 * expected_revenue 挂单卖出
        yesterday = history(symbol=stock.symbol, frequency='1d', start_time=context.lastday,
                            end_time=context.today, fields='close', df=True)
        delay_price = close_price + yesterday.iat[0, 0] * context.expected_revenue
        stock.t_0_type = Type.Active_Buy
        stock.delay_amount = amount
        stock.delay_price = delay_price
        stock.status = Status.WORKING  # 更新交易状态
        stock.start_time = context.now

        buy_stock(stock, amount, limit_price)
    else:
        logger.info("股票: %s, 交易状态出错", stock)


def cancel_open_order():
    """
    取消所有未完成的订单（未撮合成的订单）
    :return:
    """
    order_cancel_all()


def reset_position(context):
    """
    恢复所有股票到原有仓位
    :param context:
    :return:
    """
    for stock in context.basestock_pool:
        cur_position = (context.account().position(symbol=stock.symbol, side=PositionSide_Long))['volume']
        if cur_position == stock.position:
            # 仓位相等，不做操作
            pass

        elif cur_position > stock.position:
            # 说明 买了卖不出去，强制卖出
            context.reset_order_count += 1
            order_volume(symbol=stock.symbol, volume=(cur_position - stock.position),
                         side=PositionSide_Short, order_type=OrderType_Market,
                         position_effect=PositionEffect_Open)

            cur_close = current(symbols=stock.symbol, fields='price')[0].price
            delta_pos = abs(cur_position - stock.position)

            logger.info("T_0: [先买后卖失败]股票: %s, 恢复仓位: %d, 盈利: %f元",
                        stock, delta_pos, (-1) * abs(cur_close - stock.buy_price) * delta_pos)
        elif cur_position < stock.position:
            # 说明 卖了买不回来，强制买入
            context.reset_order_count += 1
            pass
        else:
            pass
