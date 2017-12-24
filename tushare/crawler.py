# -*- coding: utf-8 -*-
"""
Created on Sunday Dec 24 21:53:00 2017
@author: Yangpei
"""

import tushare as ts

import pymysql

'''
CREATE TABLE stock.stock_list (
	`code` varchar(20) not null,
	`name` varchar(64) not null,
	`industry` varchar(64) not null,
    `area` varchar(64) not null,
    `pe` 	float(20,2),
    `outstanding` 	float(20,2),
    `totals` 	float(20,2),
    `totalAssets` 	float(20,2),
    `liquidAssets` 	float(20,2),
    `fixedAssets` 	float(20,2),
    `reserved` 	float(20,2),
    `reservedPerShare` 	float(20,2),
    `esp` 	float(20,2),
    `bvps` 	float(20,2),
    `pb` 	float(20,2),
    `timeToMarket`  DATE,
    `undp` 	float(20,2),
    `perundp` 	float(20,2),
    `rev` 	float(20,2),
    `profit` 	float(20,2),
    `gpr` 	float(20,2),
    `npr` 	float(20,2),
    `holders` int
)
COMMENT = `股票列表`;
'''

insert_sql = "INSERT INTO stock_info (code, tick, volume, open, close, high, low) VALUES ('%s', '%s', %s, %s, %s, %s, %s);"


def get_5min_tick(code):
    return ts.get_k_data(code, ktype='5')


def write_data(conn, data):
    cur = conn.cursor()
    for index, row in data.iterrows():
        row_tulpe = (row['code'], row['date'], row['volume'], row['open'], row['close'], row['high'], row['low'])
        wsql = insert_sql % row_tulpe
        try:
            cur.execute(wsql)
        except:
            pass
    conn.commit()


def run():
    conn = pymysql.connect("localhost", "root", "root", "stock")
    stock_list_df = ts.get_stock_basics()

    for code, info in stock_list_df.iterrows():
        print("Trying:" + code)

        for i in range(5):
            try:
                df = get_5min_tick(code)
                write_data(conn, df)
                print("Written:" + code)
                print(df)
                break
            except:
                print("Retrying..." + code)
    conn.close()


if "__main__" == __name__:
    run()
