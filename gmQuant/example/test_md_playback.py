from gmsdk.api import md


def on_tick(tick):
    print('tick: %s %s %s' % (tick.sec_id, tick.last_price, tick.strtime))


def on_bar(bar):
    print('bar: %s %s %s' % (bar.sec_id, bar.open, bar.strtime))


md.ev_tick += on_tick
md.ev_bar += on_bar
ret = md.init(username='demo@myquant.cn',
              password='123456',
              mode=4,
              subscribe_symbols='SZSE.000001.bar.daily',
              start_time='2015-05-27 00:00:00',
              end_time='2015-06-27 09:30:00')

print('init result: ', ret)
md.run()
