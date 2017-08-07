# -*- coding: utf-8 -*-
import time
from gmsdk.api import md
import arrow

def to_local(utc):
  return arrow.get(utc).to('local')


def on_tick(tick):
    print('%s %s %s %s' % (to_local(time.time()), tick.strtime, tick.sec_id, tick.last_price))

def on_bar(bar):
    print('%s %s %s %s %s %s %s %s' % (to_local(time.time()), bar.strtime, bar.sec_id, bar.bar_type, bar.open, bar.high, bar.low, bar.close))

def on_error(code, message):
    print (code, message)


md.ev_tick += on_tick
md.ev_bar += on_bar
md.ev_error += on_error


ret = md.init(
              username='demo@myquant.cn',
              password='123456',
              mode=2,
              subscribe_symbols="SZSE.000001.tick,SHSE.600000.tick",
              )

print('init result: ', ret)
md.run()
