# from stocklab.scheduler.data_collector_1d import collect_stock_info
from stocklab.scheduler.data_collector_1d import collect_stock_info_schd
# from stocklab.scheduler.data_collector_1d import collect_code_list
from stocklab.scheduler.data_collector_1d import collect_code_list_schd
from apscheduler.schedulers.background import BackgroundScheduler
from multiprocessing import Process
from datetime import datetime
import inspect
import time


def run_process_collect_code_list():
    print(inspect.stack()[0][3])
    # p = Process(target=collect_code_list())
    p = Process(target=collect_code_list_schd())
    p.start()
    p.join()


def run_process_collect_stock_info():
    print(inspect.stack()[0][3])
    # p = Process(target=collect_stock_info())
    p = Process(target=collect_stock_info_schd())
    p.start()
    p.join()



if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=run_process_collect_code_list, trigger="cron",
                      day_of_week="mon-fri", hour="19", minute="55", id="1")
    scheduler.add_job(func=run_process_collect_stock_info, trigger="cron",
                      day_of_week="mon-fri", hour="20", minute="00", id="2")
    scheduler.start()
    while True:
        print("running", datetime.now())
        time.sleep(10)