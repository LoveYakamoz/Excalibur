#  -*- coding: utf-8 -*- 
"""
    模块名：zw_talib调用demo脚本
    本demo是zw_talib函数库v0.5的配套测试脚本
    v0.5版，所有33个函数，均已测试通过，
    运行平台：python3.5，zwPython2016m2

     zw量化，py量化第一品牌
     网站:http://www.ziwang.com zw网站
     py量化QQ总群  124134140   千人大群 zwPython量化&大数据

     开发：zw量化开源团队 2016.03.28

"""

import pandas as pd

#  import cPickle as pickle
import matplotlib as mpl
import zw_talib as zwta


# ----

# ---------------    init.stkLib
# mpl.style.use('seaborn-whitegrid')
pd.set_option('display.width', 350)
# -----------------------
ohlcExtLst = ['date', 'open', 'high', 'low', 'close', 'volume']
xcod = '600401'
xnam = 'hairun'
xcam = 'ST海润'
fss = xcod + '.csv'
df = pd.read_csv(fss, index_col=0, encoding='gbk', usecols=ohlcExtLst)
# df=df[df['date']>'2012']
df = df[df.index > '2015']
# df5=df
# -----zwta.MA
df8 = zwta.MA(df, 30)
# ------# -----zwta.xxx
df8 = zwta.EMA(df8, 30)
# df8=zwta.MOM(df8,30)
# df8=zwta.ACCDIST(df8,30)
# df8=zwta.ADX(df8,30,5)
# df8=zwta.ATR(df8,30)
# df8=zwta.BBANDS(df8,30)
# df8=zwta.BBANDS_UpLow(df8,30)
# df8=zwta.CCI(df8,30)
# df8=zwta.COPP(df8,30)
# df8=zwta.CHAIKIN(df8)
# df8=zwta.DONCH(df8,30)
# df8=zwta.EOM(df8,30)
# df8=zwta.FORCE(df8,30)
# df8=zwta.KELCH(df8,30)
# df8=zwta.KST(df8,1, 2, 3, 4, 6, 7, 9, 9)
# df8=zwta.KST4(df8,12,20,30,40)
# df8=zwta.MACD(df8,12,26)
# df8=zwta.MFI(df8,30)
# df8=zwta.MASS(df8)
# df8=zwta.OBV(df8,30)
# df8=zwta.PPSR(df8)
# df8=zwta.ROC(df8,30)
# df8=zwta.RSI2(df8,30)
# df8=zwta.STOD(df8,30)
# df8=zwta.STOK(df8)
# df8=zwta.TRIX(df8,30)
# df8=zwta.TSI(df8,2,4)
# df8=zwta.ULTOSC(df8)
# df8=zwta.VORTEX(df8,30)
# ---ok

# xlst=['ma','ema','mom','ad','atr','boll','cci','copp','ck','donch']
# xlst=['eom','force','kc','kst','macd','msign','mdiff','mfi','mass']
# xlst=['obv','pp','roc','rsi','trix','tsi','uos','vortex']

print(df8.tail(30))
ksgn = 'ema_30'
df8[['close', 'ma_30', ksgn]].plot()

df8 = zwta.MA(df, 30)
df8 = zwta.BBANDS_UpLow(df8, 30)
ksgn = 'boll_ma'
ksgn2 = 'boll_std'
ksgn3 = 'boll_up'
ksgn4 = 'boll_low'
df8[['close', ksgn, ksgn2, ksgn3, ksgn4]].plot()
# ------
'''
其他函数，的请参照以上脚本，自行修改相关参数调用
所有函数均已测试通过，运行平台：python3.5，zwPython2016m2
'''
