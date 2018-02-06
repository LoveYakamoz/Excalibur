from math import floor

from gm.api import *

"""
buy sell信号及操作
"""
from gm.api import order_cancel_all

from gmQuant.GM_T_0.model.BaseStock import Type, Status


def buy_stock(context, stock, amount, limit_price, index):
    """
    购买股票，并记录订单号，便于查询订单状态
    :param context:
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    buy_order = order_volume(symbol=stock, volume=amount,
                             side=OrderSide_Buy,
                             order_type=OrderType_Limit,
                             position_effect=PositionEffect_Open,
                             price=limit_price)

    if buy_order is not None:
        context.basestock_pool[index].buy_price = limit_price
        # print("买入股票: %s, 以%f价格挂单，买入%d, 成功" % (stock, limit_price, amount))
        return True
    else:
        context.basestock_pool[index].buy_price = 0
        print("买入股票: %s, 以%f价格挂单，买入%d, 失败" % (stock, limit_price, amount))
        return False


def sell_stock(context, stock, amount, limit_price, index):
    """
    卖出股票，并记录订单号，便于查询订单状态
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    sell_order = order_volume(symbol=stock, volume=amount,
                              side=OrderSide_Sell,
                              order_type=OrderType_Limit,
                              position_effect=PositionEffect_Open,
                              price=limit_price)

    if sell_order is not None:
        context.basestock_pool[index].sell_price = limit_price
        #print("卖出股票: %s, 以%f价格挂单，卖出%d" % (stock, limit_price, amount))
        return True
    else:
        context.basestock_pool[index].sell_price = 0
        return False


def sell_signal(context, stock, close_price, index):
    if context.basestock_pool[index].status == Status.WORKING:
        # print("股票: %s, 收到重复卖出信号，但不做交易" % stock)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = context.adjust_scale * context.basestock_pool[index].position

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01
    print("卖出信号: %f, src_position: %d, amount: %d, price: %f" %
          (context.adjust_scale, context.basestock_pool[index].position, amount, limit_price))

    if context.basestock_pool[index].status == Status.INIT:
        flag = sell_stock(context, stock, -amount, limit_price, index)
        if not flag:
            return

        # 以收盘价 - 价差 * expected_revenue 挂单买入
        yesterday = history(symbol=stock, frequency='1d', start_time=context.lastday,
                            end_time=context.today, fields='close', df=True)
        limit_price = close_price - yesterday.iat[0, 0] * context.expected_revenue
        context.basestock_pool[index].t_0_type = Type.Active_Sell
        context.basestock_pool[index].delay_amount = amount
        context.basestock_pool[index].delay_price = limit_price
        context.basestock_pool[index].status = Status.WORKING  # 更新交易状态
    else:
        print("股票: %s, 交易状态出错" % stock)


def buy_signal(context, stock, close_price, index):
    print(context.basestock_pool[index].status)
    if context.basestock_pool[index].status == Status.WORKING:
        print("%s 股票: %s, index: %d 收到重复买入信号，但不做交易" % (context.now, stock, index))
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = floor(context.adjust_scale * context.basestock_pool[index].position)

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    print("买入信号: %f, src_position: %d, amount: %d, price: %f" %
          (context.adjust_scale, context.basestock_pool[index].position, amount, limit_price))

    if context.basestock_pool[index].status == Status.INIT:
        flag = buy_stock(context, stock, amount, limit_price, index)
        if not flag:
            return

        # 以收盘价 + 价差 * expected_revenue 挂单卖出
        yesterday = history(symbol=stock, frequency='1d', start_time=context.lastday,
                            end_time=context.today, fields='close', df=True)
        limit_price = close_price + yesterday.iat[0, 0] * context.expected_revenue
        context.basestock_pool[index].t_0_type = Type.Active_Buy
        context.basestock_pool[index].delay_amount = -amount
        context.basestock_pool[index].delay_price = limit_price
        context.basestock_pool[index].status = Status.WORKING  # 更新交易状态
        context.basestock_pool[index].start_time = context.now

    else:
        print("股票: %s, 交易状态出错" % stock)


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
    for s in context.basestock_pool:
        stock = s.stock
        src_position = s.position
        cur_position = context.portfolio.positions[stock].total_amount
        if src_position != cur_position:
            context.reset_order_count += 1
            order_volume(symbol=stock, volume=(src_position - cur_position),
                         side=OrderSide_Buy, order_type=OrderType_Market,
                         position_effect=PositionEffect_Open)

            cur_close = current(symbols=stock).price
            delta_pos = abs(src_position - cur_position)
            if s.t_0_type == Type.Active_Buy:
                print("T_0 ：【先买后卖失败】股票: %s, 恢复仓位: %d, 盈利: %f元" %
                      (stock, delta_pos, (-1) * abs(cur_close - s.buy_price) * delta_pos))
            elif s.t_0_type == Type.Active_Sell:
                print("T_0 ：【先卖后买失败】股票: %s, 恢复仓位: %d, 盈利: %f元" %
                      (stock, delta_pos, (-1) * abs(cur_close - s.sell_price) * delta_pos))
            else:
                pass



