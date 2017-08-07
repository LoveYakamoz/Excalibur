#!/usr/bin/env python
# -*- coding: utf-8 -*-
from gmsdk.api import StrategyBase
from gmsdk.util import bar_to_dict

class MyStrategy(StrategyBase):
    def __init__(self, *args, **kwargs):
        super(MyStrategy, self).__init__(*args, **kwargs)
        self.oc = True
    
    def on_login(self):
        print('logged in')
    
    def on_error(self, err_code, msg):
        # print('get error: %s - %s' % (err_code, msg))
        pass
    
    def on_bar(self, bar):
        print(bar_to_dict(bar))
        if self.oc:
            self.open_long(bar.exchange, bar.sec_id, 0, 100)
        else:
            self.close_long(bar.exchange, bar.sec_id, 0, 100)
        self.oc = not self.oc



if __name__ == '__main__':
    ret = MyStrategy(
        username='demo@myquant.cn',
        password='123456',
        strategy_id='strategy_2',
        subscribe_symbols='CFFEX.IF1603.bar.60',
        mode=2
    ).run()
    print(('exit code: ', ret))
