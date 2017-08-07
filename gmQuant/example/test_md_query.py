#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gmsdk import md, to_dict

md.init('demo@myquant.cn', '123456')
# 提取tick数据
r = md.get_ticks(
    'SHSE.600000',
    '2016-01-04 09:00:00',
    '2016-01-04 12:00:00',
)
print('get_ticks: ', len(r))

#提取tick快照
r = md.get_last_ticks('SHSE.600000')
print('get_last_ticks: ', len(r))

#提取最新N笔tick数据
r = md.get_last_n_ticks(
    'SHSE.600000', 10)
print('get_last_n_ticks(10): ', len(r))

#提起一分钟分时数据(freq=60 seconds)
r = md.get_bars(
    'SHSE.600000',
    60,
    '2015-12-01 09:30:00',
    '2015-12-10 09:31:00',
)
print('get_bars: ', len(r))

#提取bar快照
r = md.get_last_bars('SHSE.600000,', 60)
print('get_last_bars: ', len(r))

#提取最新N笔bar数据
r = md.get_last_n_bars('SHSE.600000',60,10)
print('get_last_n_bars(10): ', len(r))

#提取日频数据
r = md.get_dailybars(
    'SHSE.600000',
    '2015-05-01 00:00:00',
    '2015-05-20 23:59:59')
print('get_dailybars: ', len(r))

#提取dailybar快照
r = md.get_last_dailybars('SHSE.600000,')
print('get_last_dailybars: ', len(r))

#提取最新N笔dailybar数据
r = md.get_last_n_dailybars('SHSE.600000', 10)
print('get_last_n_dailybars(10): ', len(r))

#提取交易代码
r = md.get_instruments('SHSE', 1, 1)
print('get_instruments: ', len(r))

#根据期货品种提取交易代码
r = md.get_instruments_by_name('ag')
print('get_instruments_by_name', len(r))

#提取指数的成分股代码
r = md.get_constituents('SHSE.000001')
print('get_constituents', len(r))

#按时间周期提取FinancialIndex
r = md.get_financial_index('SHSE.600000', '2010-12-01 09:30:00', '2016-01-08 12:00:00')
print('get_financial_index', len(r))

#提取快照, 即最新的FinancialIndex
r = md.get_last_financial_index('SHSE.600000,SZSE.000001')
print('get_last_financial_index', len(r))

#提取最近n条FinancialIndex
r = md.get_last_n_financial_index('SHSE.600000', 5)
print('get_last_n_financial_index', len(r))

#按时间周期提取ShareIndex
r = md.get_share_index('SHSE.600000', '2015-12-01 09:30:00', '2016-01-08 12:00:00')
print('get_share_index', len(r))

#提取快照, 即最新的ShareIndex
r = md.get_last_share_index('SHSE.600000,SZSE.000001')
print('get_last_share_index', len(r))

#提取最近n条ShareIndex
r = md.get_last_n_share_index('SHSE.600000', 5)
print('get_last_n_share_index', len(r))

#按时间周期提取MarketIndex
r = md.get_market_index('SHSE.600000', '2015-12-01 09:30:00', '2016-01-08 12:00:00')
print('get_market_index', len(r))

#提取快照, 即最新的MarketIndex
r = md.get_last_market_index('SHSE.600000,SZSE.000001')
print('get_last_market_index', len(r))

#提取最近n条MarketIndex
r = md.get_last_n_market_index('SHSE.600000', 5)
print('get_last_n_market_index', len(r))

#提取交易日历
r = md.get_calendar('SHSE', '2016-01-00', '2016-03-16')
print('get_calendar', len(r))

input()
