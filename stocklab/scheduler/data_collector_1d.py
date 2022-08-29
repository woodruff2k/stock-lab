from stocklab.db_handler.mongodb_handler import MongoDBHandler
from stocklab.agent.ebest import EBest
from datetime import datetime
import pythoncom
import time
"""
pythoncom.CoInitialize()
mongodb = MongoDBHandler()
ebest = EBest("DEMO")
ebest.login()
"""


def collect_code_list(ebest, mongodb):
    result = ebest.get_code_list("ALL")
    mongodb.deleteMany({}, "stocklab", "code_info")
    mongodb.insertMany(result, "stocklab", "code_info")
    # mongodb.updateMany(result, "stocklab", "code_info", upsert=True)


def collect_stock_info(ebest, mongodb):
    code_list = mongodb.find({}, "stocklab", "code_info")
    # shcode(단축코드) for ALL(KOSPI, KOSDAQ)
    target_code = set([item["단축코드"] for item in code_list])

    # old price_info (today)
    today = datetime.today().strftime("%Y%m%d")
    # print(today)
    collect_list = mongodb.find({"날짜": today}, "stocklab", "price_info").distinct("code")
    # print(len(target_code))
    # print(len(collect_list))
    for col in collect_list:
        target_code.remove(col)
    print(len(target_code))

    for code in target_code:
        time.sleep(1)
        # print("code:", code)

        # new price_info (today)
        result_price = ebest.get_stock_price_by_code(code, "1")
        if len(result_price) > 0:
            # print(result_price)
            mongodb.insertMany(result_price, "stocklab", "price_info")

        # new credit_info (today)
        result_credit = ebest.get_credit_trend_by_code(code, today)
        if len(result_credit) > 0:
            mongodb.insertMany(result_credit, "stocklab", "credit_info")

        # new agent_info (today)
        result_agent = ebest.get_agent_trend_by_code(code, fromdt=today, todt=today)
        if len(result_agent) > 0:
            mongodb.insertMany(result_agent, "stocklab", "agent_info")

        # new short_info (today)
        result_short = ebest.get_short_trend_by_code(code, sdate=today, edate=today)
        if len(result_short) > 0:
            mongodb.insertMany(result_short, "stocklab", "short_info")


def collect_code_list_schd():
    pythoncom.CoInitialize()
    mongodb = MongoDBHandler()
    ebest = EBest("DEMO")
    ebest.login()

    # collect_code_list()
    collect_code_list(ebest, mongodb)

    ebest.logout()
    pythoncom.CoUninitialize()


def collect_stock_info_schd():
    pythoncom.CoInitialize()
    mongodb = MongoDBHandler()
    ebest = EBest("DEMO")
    ebest.login()

    # collect_stock_info()
    collect_stock_info(ebest, mongodb)

    ebest.logout()
    pythoncom.CoUninitialize()


if __name__ == '__main__':
    pythoncom.CoInitialize()
    mongodb = MongoDBHandler()
    ebest = EBest("DEMO")
    ebest.login()

    # collect_code_list()
    collect_code_list(ebest, mongodb)
    # collect_stock_info()
    collect_stock_info(ebest, mongodb)

    ebest.logout()
    pythoncom.CoUninitialize()