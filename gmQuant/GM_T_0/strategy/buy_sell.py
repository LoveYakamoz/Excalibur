"""
buy sell信号及操作
"""


def buy_stock(stock, amount, limit_price, index):
    """
    购买股票，并记录订单号，便于查询订单状态
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    try:
        buy_order = order(stock, amount, LimitOrderStyle(limit_price))
    finally:
        g.__manager.work()

    if buy_order is not None:
        g.basestock_pool[index].buy_order_id = buy_order.order_id
        g.basestock_pool[index].buy_price = limit_price
        log.info("股票: %s, 以%f价格挂单，买入%d", stock, limit_price, amount)
        return True
    else:
        g.basestock_pool[index].buy_price = 0
        return False


def sell_stock(stock, amount, limit_price, index):
    """
    卖出股票，并记录订单号，便于查询订单状态
    :param stock:
    :param amount:
    :param limit_price:
    :param index:
    :return:
    """
    try:
        sell_order = order(stock, amount, LimitOrderStyle(limit_price))
    finally:
        g.__manager.work()

    if sell_order is not None:
        g.basestock_pool[index].sell_order_id = sell_order.order_id
        g.basestock_pool[index].sell_price = limit_price
        log.info("股票: %s, 以%f价格挂单，卖出%d", stock, limit_price, amount)
        return True
    else:
        g.basestock_pool[index].sell_price = 0
        return False


def sell_signal(context, stock, close_price, index):
    if g.basestock_pool[index].status == Status.WORKING:
        log.warn(" 股票: %s, 收到重复卖出信号，但不做交易", stock)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = g.adjust_scale * g.basestock_pool[index].position

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 + 0.01 挂单卖出
    limit_price = close_price + 0.01
    log.info(" sell scale: %f, src_posiont: %d, amount: %d, price: %f", g.adjust_scale,
             g.basestock_pool[index].position, amount, limit_price)

    if g.basestock_pool[index].status == Status.INIT:
        flag = sell_stock(stock, -amount, limit_price, index)
        if (False == flag):
            return

        # 以收盘价 - 价差 * expected_revenue 挂单买入
        yesterday = get_price(stock, count=1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
        limit_price = close_price - yesterday.iat[0, 0] * g.expected_revenue
        g.basestock_pool[index].t_0_type = Type.Active_Sell
        g.basestock_pool[index].delay_amount = amount
        g.basestock_pool[index].delay_price = limit_price
        g.basestock_pool[index].status = Status.WORKING  # 更新交易状态
    else:
        log.error("股票: %s, 交易状态出错", stock)


def buy_signal(context, stock, close_price, index):
    if g.basestock_pool[index].status == Status.WORKING:
        log.warn(" 股票: %s, 收到重复买入信号，但不做交易", stock)
        return

    # 每次交易量为持仓量的g.adjust_scale
    amount = floor(g.adjust_scale * g.basestock_pool[index].position)

    if amount <= 100:
        amount = 100
    else:
        if amount % 100 != 0:
            amount -= amount % 100

    # 以收盘价 - 0.01 挂单买入
    limit_price = close_price - 0.01
    log.info("buy scale: %f, src_posiont: %d, amount: %d, price: %f", g.adjust_scale,
             g.basestock_pool[index].position,
             amount, limit_price)

    if g.basestock_pool[index].status == Status.INIT:
        flag = buy_stock(stock, amount, limit_price, index)
        if (False == flag):
            return

        # 以收盘价 + 价差 * expected_revenue 挂单卖出
        yesterday = get_price(stock, count=1, end_date=str(context.current_dt), frequency='daily', fields=['close'])
        limit_price = close_price + yesterday.iat[0, 0] * g.expected_revenue
        g.basestock_pool[index].t_0_type = Type.Active_Buy
        g.basestock_pool[index].delay_amount = -amount
        g.basestock_pool[index].delay_price = limit_price
        g.basestock_pool[index].status = Status.WORKING  # 更新交易状态
        g.basestock_pool[index].start_time = context.current_dt

    else:
        log.error("股票: %s, 交易状态出错", stock)


def cancel_open_order(context):
    """
    取消所有未完成的订单（未撮合成的订单）
    :param context:
    :return:
    """
    orders = get_open_orders()
    for _order in orders.values():
        try:
            cancel_order(_order)
        finally:
            g.__manager.work()


def reset_position(context):
    """
    恢复所有股票到原有仓位
    :param context:
    :return:
    """
    for s in g.basestock_pool:
        stock = s.stock
        src_position = s.position
        cur_position = context.portfolio.positions[stock].total_amount
        if src_position != cur_position:
            try:
                order(stock, src_position - cur_position)
            finally:
                g.__manager.work()
            current_data = get_current_data()
            cur_close = current_data[stock].last_price
            delta_pos = abs(src_position - cur_position)
            if s.t_0_type == Type.Active_Buy:
                log.info("T_0 ：【先买后卖失败】股票: %s, 恢复仓位: %d, 盈利: %f元", stock, delta_pos,
                         (-1) * abs(cur_close - s.buy_price) * delta_pos)
            elif s.t_0_type == Type.Active_Sell:
                log.info("T_0 ：【先卖后买失败】股票: %s, 恢复仓位: %d, 盈利: %f元", stock, delta_pos,
                         (-1) * abs(cur_close - s.sell_price) * delta_pos)
            else:
                pass
            g.reset_order_count += 1
