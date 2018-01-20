import numpy as np
def evaluate_activeVolBuy(np_close, vol):
    """
    主动性买盘成交量
    :return:
    :param np_close:  3~4 sampleSize
    :param vol:
    :return:
    """
    diff_a1 = np.diff(np_close)
    comp_vol = vol[1:]
    activeVolBuy = []
    activeVolSell = []
    swingVol = []
    accumulateNetVol = 0
    netVol_buySell = []

    for i in range(len(diff_a1)):
        if diff_a1[i] > 0:
            activeVolBuy.append(comp_vol[i])
            activeVolSell.append(0)
        elif diff_a1[i] < 0:
            activeVolSell.append(comp_vol[i])
            activeVolBuy.append(0)
        else:
            swingVol.append(comp_vol[i])
            activeVolBuy.append(0)
            activeVolSell.append(0)

    for k in range(len(activeVolBuy)):
        netVol = activeVolBuy[k] - activeVolSell[k]
        accumulateNetVol += netVol
        netVol_buySell.append(float(accumulateNetVol))

    netVol_buySell_sum = np.sum(np.array(activeVolBuy)) - np.sum(np.array(activeVolSell))

    threshold_netVol = np.average(netVol_buySell[-g.sampleSize:])
    # print('netVol_buySell_sum=%d, threshold_netvol=%d' % (netVol_buySell_sum, threshold_netVol))
    if netVol_buySell[-1] > 0 and netVol_buySell_sum > 0 and netVol_buySell[-1] > (threshold_netVol * g.scale):
        g.signal_buy_dict['signal_netVol_buySell'] = 1

    elif netVol_buySell[-1] < 0 and threshold_netVol < 0 and abs(netVol_buySell[-1]) > (
                abs(threshold_netVol) * g.scale):
        g.signal_buy_dict['signal_netVol_buySell'] = -1
    else:
        g.signal_buy_dict['signal_netVol_buySell'] = 0

    return activeVolBuy, activeVolSell, netVol_buySell