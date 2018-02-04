import numpy as np
from gm.api import history_n

g_sampleSize = 20  # 20 or 30
g_scale = 1.5  # 倍数1.0-5倍
g_signal_buy_dict = {}


def evaluate_activeVolBuy(np_close, vol):
    """
    主动性买盘成交量
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

    threshold_netVol = np.average(netVol_buySell[-g_sampleSize:])

    if netVol_buySell[-1] > 0 and netVol_buySell_sum > 0 and netVol_buySell[-1] > (threshold_netVol * g_scale):
        g_signal_buy_dict['signal_netVol_buySell'] = 1

    elif netVol_buySell[-1] < 0 and threshold_netVol < 0 and abs(netVol_buySell[-1]) > (
                abs(threshold_netVol) * g_scale):
        g_signal_buy_dict['signal_netVol_buySell'] = -1
    else:
        g_signal_buy_dict['signal_netVol_buySell'] = 0

    return activeVolBuy, activeVolSell, netVol_buySell
