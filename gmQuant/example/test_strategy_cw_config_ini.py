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
    ret = MyStrategy(config_file='test_strategy.ini', config_file_encoding='utf-8').run()
    print(('exit code: ', ret))
