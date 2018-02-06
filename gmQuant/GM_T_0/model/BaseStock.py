from enum import Enum

# 持仓股票池详细信息
MAX_STOCK_COUNT = 30

class Status(Enum):
    INIT = 0  # 在每天交易开始时，置为INIT
    WORKING = 1  # 处于买/卖中
    NONE = 2  # 今天不再做任何交易


class Type(Enum):
    Active_Buy = "主动买入"
    Active_Sell = "主动卖出"
    NONE = "无"


class T_0(Enum):
    """
    T_0是否打开
    """
    Open = 1
    Close = 2


class BaseStock:
    """
    股票详细信息
    """

    def __init__(self, stock, close, status, position, sell_order_id, buy_order_id, t_0_type):
        self.stock = stock
        self.close = close

        self.status = status
        self.position = position
        self.sell_order_id = sell_order_id
        self.sell_price = 0.0
        self.buy_order_id = buy_order_id
        self.buy_price = 0.0

        self.delay_amount = 0  # 反向挂单量
        self.delay_price = 0.0  # 反向挂单价格
        self.t_0_type = t_0_type  # t+0的类型

        self.start_time = None
        self.end_time = None

    def __repr__(self):
        return "stock: {}, close: {}, position: {}, sell_order_id: {}, buy_order_id: {}, t_0_type: {}".format(
            self.stock, self.close, self.position, self.sell_order_id, self.buy_order_id, self.t_0_type)

    def cleanup(self):
        self.status = Status.INIT
        self.sell_order_id = -1
        self.sell_price = 0.0
        self.buy_order_id = -1
        self.buy_price = 0.0
        self.delay_amount = 0
        self.delay_price = 0.0
        self.t_0_type = Type.NONE
        self.start_time = None
        self.end_time = None
        print("cleanup %s" % self.stock)

