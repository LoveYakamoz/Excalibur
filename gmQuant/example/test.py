from gmsdk.api import StrategyBase


class MyStrategy(StrategyBase):
    def __init__(self, *args, **kwargs):
        super(MyStrategy, self).__init__(*args, **kwargs)
        print ("init OK")
    def on_tick(self, tick):
        #self.open_long(tick.exchange, tick.sec_id, tick.last_price, 100)
        print("OpenLong: exchange %s, sec_id %s, price %s" %
                (tick.exchange, tick.sec_id, tick.last_price))

if __name__ == '__main__':
    ret = MyStrategy(
        username='18721037520',
        password='242613',
        strategy_id='strategy_1',
        subscribe_symbols='SHSE.600000.tick',
        mode=3
    ).run()
    print(('exit code: ', ret))
