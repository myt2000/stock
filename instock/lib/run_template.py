#!/usr/local/bin/python
# -*- coding: utf-8 -*-


import logging
import datetime
import concurrent.futures
import sys
import time
import instock.lib.trade_time as trd

__author__ = 'myh '
__date__ = '2023/3/10 '


# 通用函数，获得日期参数，支持批量作业。
def run_with_args(run_fun, *args):
    if len(sys.argv) == 3:
        # 区间作业 python xxx.py 2023-03-01 2023-03-21
        tmp_year, tmp_month, tmp_day = sys.argv[1].split("-")
        start_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
        tmp_year, tmp_month, tmp_day = sys.argv[2].split("-")
        end_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
        run_date = start_date
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                while run_date <= end_date:
                    if trd.is_trade_date(run_date):
                        executor.submit(run_fun, run_date, *args)
                        time.sleep(2)
                    run_date += datetime.timedelta(days=1)
        except Exception as e:
            logging.debug("{}处理异常：{}{}{}".format('run_template.run_with_args', run_fun, sys.argv, e))
    elif len(sys.argv) == 2:
        # N个时间作业 python xxx.py 2023-03-01,2023-03-02
        dates = sys.argv[1].split(',')
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for date in dates:
                    tmp_year, tmp_month, tmp_day = date.split("-")
                    run_date = datetime.datetime(int(tmp_year), int(tmp_month), int(tmp_day)).date()
                    if trd.is_trade_date(run_date):
                        executor.submit(run_fun, run_date, *args)
                        time.sleep(2)
        except Exception as e:
            logging.debug("{}处理异常：{}{}{}".format('run_template.run_with_args', run_fun, sys.argv, e))
    else:
        # 当前时间作业 python xxx.py
        try:
            now_time = datetime.datetime.now()
            run_date = now_time.date()
            run_date_nph = run_date
            if trd.is_trade_date(run_date):
                if not trd.is_close(now_time):
                    run_date = trd.get_previous_trade_date(run_date)
            else:
                run_date = trd.get_previous_trade_date(run_date)
                run_date_nph = run_date

            if run_fun.__name__.startswith('save_nph'):
                run_fun(run_date_nph, False)
            else:
                run_fun(run_date, *args)
        except Exception as e:
            logging.debug("{}处理异常：{}{}{}".format('run_template.run_with_args', run_fun, sys.argv, e))
