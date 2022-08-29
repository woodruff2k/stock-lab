import quandl

quandl.ApiConfig.api_key = 'auyJg-xBxLzD5nZsgZgs'

if __name__ == "__main__":
    # data = quandl.get("BCHAIN/MKPRU", start_date='2022-07-01', end_date='2022-07-31')
    # print(data)

    data = quandl.get('BCHARTS/BITFLYERUSD', start_date='2019-03-07', end_date='2019-03-07')
    print(data)
