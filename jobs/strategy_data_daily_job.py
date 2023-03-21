#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

import logging
import concurrent.futures
import pandas as pd

import os.path
import sys
# 在项目运行时，临时将项目路径添加到环境变量
cpath = os.path.dirname(os.path.dirname(__file__))
sys.path.append(cpath)


import libs.run_template as runt
import libs.tablestructure as tbs
import libs.database as mdb
from libs.singleton import stock_hist_data
from libs.stockfetch import fetch_stock_top_entity_data

__author__ = 'myh '
__date__ = '2023/3/10 '


def prepare(date, strategy):
    try:
        stocks_data = stock_hist_data(date=date).get_data()
        if stocks_data is None:
            return
        table_name = strategy['name']
        strategy_func = strategy['func']
        results = run_check(strategy_func, stocks_data, date)
        if results is None:
            return

        # 删除老数据。
        if mdb.checkTableIsExist(table_name):
            del_sql = " DELETE FROM `" + table_name + "` WHERE `date` = '%s' " % date
            mdb.executeSql(del_sql)
            cols_type = None
        else:
            cols_type = tbs.get_cols_type(tbs.TABLE_CN_STOCK_STRATEGIES[0]['columns'])

        data = pd.DataFrame(results)
        columns = list(tbs.TABLE_CN_STOCK_FOREIGN_KEY['columns'].keys())
        data.columns = columns
        _columns_backtest = list(tbs.TABLE_CN_STOCK_BACKTEST_DATA['columns'].keys())
        data = pd.concat([data, pd.DataFrame(columns=_columns_backtest)])
        # 单例，时间段循环必须改时间
        date_str = date.strftime("%Y-%m-%d")
        if date.strftime("%Y-%m-%d") != data.iloc[0]['date']:
            data['date'] = date_str
        mdb.insert_db_from_df(data, table_name, cols_type, False, "`date`,`code`")

    except Exception as e:
        logging.debug("{}处理异常：{}策略{}".format('strategy_data_daily_job.check', strategy, e))


def run_check(strategy_fun, stocks, date, workers=40):
    is_check_high_tight = False
    if strategy_fun.__name__ == 'check_high_tight':
        stock_tops = fetch_stock_top_entity_data(date)
        if stock_tops is not None:
            is_check_high_tight = True
    data = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            if is_check_high_tight:
                future_to_data = {executor.submit(strategy_fun, k, v, date=date, istop=(k[1] in stock_tops)): k for k, v
                                  in stocks.items()}
            else:
                future_to_data = {executor.submit(strategy_fun, k, v, date=date): k for k, v
                                  in stocks.items()}
            for future in concurrent.futures.as_completed(future_to_data):
                stock = future_to_data[future]
                try:
                    if future.result():
                        data.append(stock)
                except Exception as e:
                    logging.debug(
                        "{}处理异常：{}代码{}".format('strategy_data_daily_job.run_get_indicator', stock[1], e))
    except Exception as e:
        logging.debug("{}处理异常：{}".format('strategy_data_daily_job.run_strategy', e))
    if not data:
        return None
    else:
        return data


def main():
    # 使用方法传递。
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for strategy in tbs.TABLE_CN_STOCK_STRATEGIES:
            executor.submit(runt.run_with_args, prepare, strategy)


# main函数入口
if __name__ == '__main__':
    main()