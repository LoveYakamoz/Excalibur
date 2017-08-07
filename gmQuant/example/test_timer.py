#!/usr/bin/env python
# -*- coding: utf-8 -*-

from gmsdk.api import StrategyBase
import time

INTERVAL = 1000

class MyStrategy(StrategyBase):
    def __init__(self, *args, **kwargs):
        super(MyStrategy, self).__init__(*args, **kwargs)
        self.count = 0

    def on_login(self):
        print('%s: loggedin' % time.strftime("%Y-%m-%d %X", time.localtime()))

    def on_timer(self, interval):
        print('%s: on timer event: #%s of %s' % (time.strftime("%Y-%m-%d %X", time.localtime()), self.count, interval))
        self.count += 1
        if (self.count > 10):
            print('stop timer')
            global INTERVAL
            self.unset_timer(INTERVAL)


if __name__ == '__main__':
    myStrategy = MyStrategy(
        username='demo@myquant.cn',
        password='123456',
        strategy_id='',
        subscribe_symbols='',
        mode=1
    )
    myStrategy.set_timer(INTERVAL)
    ret = myStrategy.run()
    print(('exit code: ', ret))
