#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gmsdk import td, get_strerror, to_dict
from gmsdk.enums import *



def on_execrpt(execrpt):
    print('got execrpt report: ', execrpt)


def on_order_status(o):
    print('got order: ', o)


def on_error(code, message):
    print('got error: %s=%s' % (code, message))


def on_login():
    # place 4 orders
    order1 = td.open_long('SHSE', '600000', 0, 100)
    order2 = td.open_short('SHSE', '600000', 0, 100)
    order3 = td.close_long('SHSE', '600000', 0, 10)
    order4 = td.close_short('SHSE', '600000', 0, 10)

    print('placed 4 orders:', order1, order2, order3, order4)
    # try to cancel order1
    td.cancel_order(order1.cl_ord_id)

    # query order
    order = td.get_order(order2.cl_ord_id)
    print('query order: ', order)

    # get orders
    orders = td.get_orders('2016-01-01', '2016-03-16')
    print('query orders: ', len(orders))

    # get orders
    orders = td.get_orders_by_symbol('SHSE', '600000', '2016-01-01', '2016-03-16')
    print('query orders by symbol: ', len(orders))

    # query cash
    cash = td.get_cash()
    print('query cash: ', cash)

    # query position
    position = td.get_position('SHSE', '600000', OrderSide_Bid)
    print('query position: ', position)

    # query all positions
    positions = td.get_positions()
    print('query all positions: ', positions)

    # get unfinished orders
    orders = td.get_unfinished_orders()
    print('query unfinished orders: ', orders)

    # 策略已配置实盘账户，查询策略关联账户的相关信息

    # 获取柜台交易账号列表
    # r = td.get_broker_accounts()
    # print ('get_broker_accounts', [to_dict(i) for i in r])

    # 获取柜台交易账号资金
    # r = td.get_broker_cash()
    # print ('get_broker_cash', [to_dict(i) for i in r])

    # 获取柜台交易账号持仓
    # r = td.get_broker_positions()
    # print ('get_broker_positions', [to_dict(i) for i in r])


# register callbacks
td.ev_execrpt += on_execrpt
td.ev_error += on_error
td.ev_login += on_login
td.ev_order_status += on_order_status

#连接本地终端时，td_addr为localhost:8001,
#ret = td.init('demo@myquant.cn', '123456', 'strategy_1', 'localhost:8001')

ret = td.init('demo@myquant.cn', '123456', 'strategy_1')
print('td init result: ', ret)
td.run()
