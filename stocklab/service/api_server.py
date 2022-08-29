from flask_restful import Api, Resource, reqparse, abort, fields, marshal_with
from stocklab.db_handler.mongodb_handler import MongoDBHandler
from flask import Flask, request
from flask_cors import CORS
import datetime


app = Flask(__name__)
CORS(app)
api = Api(app)
mongodb = MongoDBHandler()


"""
response fields for code
"""
code_hname_to_eng = {
    "단축코드": "code",
    "확자코드": "extend_code",
    "종목명": "name",
    "시장구분": "market",
    "ETF구분": "is_etf",
    "주문수량단위": "memedan",
    "기업인수목적회사여부": "is_spac"
}


# Schema for Code Marshal (Full Version)
code_fields = {
    "code": fields.String,
    "extend_code": fields.String,
    "name": fields.String,
    "memedan": fields.Integer,
    "market": fields.String,
    "is_etf": fields.String,
    "is_spac": fields.String,
    "uri": fields.Url("code")
}


# Schema for CodeList (Short Version)
code_short_fields = {
    "code": fields.String,
    "name": fields.String
}


# Schema for CodeList Marshal (Short Version)
code_list_fields = {
    "count": fields.Integer,
    # "code_list": fields.List(fields.Nested(code_fields)),      # Full Version
    "code_list": fields.List(fields.Nested(code_short_fields)),  # Short Version
    "uri": fields.Url("codes")
}


# /codes?market=0
class CodeList(Resource):

    @marshal_with(code_list_fields)
    def get(self):
        market = request.args.get("market", default="0", type=str)
        # results = []
        if market == "0":
            results = list(mongodb.find({}, "stocklab", "code_info"))
        elif market == "1" or market == "2":
            results = list(mongodb.find({"시장구분": market}, "stocklab", "code_info"))

        result_list = []
        for item in results:
            # code_info = {}
            code_info = {code_hname_to_eng[field]: item[field] for field in item.keys() if field in code_hname_to_eng}
            result_list.append(code_info)

        return {"code_list": result_list, "count": len(result_list)}, 200


# /codes/<code>
class Code(Resource):

    @marshal_with(code_fields)
    def get(self, code):
        result = mongodb.findOne({"단축코드": code}, "stocklab", "code_info")
        # if result is None:
        if not result:
            return {}, 404
        # code_info = {}
        code_info = {code_hname_to_eng[field]: result[field] for field in result.keys() if field in code_hname_to_eng}
        return code_info


"""
response fields for price
"""
price_hname_to_eng = {
    "날짜": "date",
    "종가": "close",
    "시가": "open",
    "고가": "high",
    "저가": "low",
    "전일대비": "diff",
    "전일대비구분": "diff_type"
}


# Schema for Price (Full Version)
price_fields = {
    "date": fields.String,
    "start": fields.Integer,
    "close": fields.String,
    "open": fields.String,
    "high": fields.String,
    "low": fields.String,
    "diff": fields.String,
    "diff_type": fields.String
}


# Schema for Price Marshal (Full Version)
price_list_fields = {
    "count": fields.Integer,
    "price_list": fields.List(fields.Nested(price_fields))
}


# /codes/<code>/price?start_date="2022-07-01"&end_date="2022-07-31"
class Price(Resource):

    @marshal_with(price_list_fields)
    def get(self, code):
        today = datetime.datetime.now().strftime("%Y%m%d")
        default_start_date = datetime.datetime.now() - datetime.timedelta(days=7)
        start_date = request.args.get("start_date", default=default_start_date.strftime("%Y%m%d"), type=str)
        end_date = request.args.get("end_date", default=today, type=str)
        results = list(mongodb.find({"code": code, "날짜": {"$gte": start_date, "$lte": end_date}},
                                    "stocklab", "price_info"))
        # result_object = {}
        price_info_list = []
        for item in results:
            price_info={price_hname_to_eng[field]: item[field] for field in item.keys() if field in price_hname_to_eng}
            price_info_list.append(price_info)
        # result_object["price_list"] = price_info_list
        # result_object["count"] = len(price_info_list)
        result_object = {"price_list": price_info_list, "count": len(price_info_list)}
        return result_object, 200


"""
response fields for orders
"""
# Schema for OrderList (Marshal)
# N/A


# /orders?status=all
class OrderList(Resource):

    # def get(self):
    @staticmethod
    def get():
        status = request.args.get("status", default="all", type=str)
        if status == "all":
            result_list = list(mongodb.find({}, "stocklab_demo", "order"))
        elif status in ["buy_ordered", "buy_completed", "sell_ordered", "sell_completed"]:
            result_list = list(mongodb.find({"status": status}, "stocklab_demo", "order"))
        else:
            return {}, 404

        return {"count": len(result_list), "order_list": result_list}, 200


api.add_resource(CodeList, "/codes", endpoint="codes")
api.add_resource(Code, "/codes/<string:code>", endpoint="code")
api.add_resource(Price, "/codes/<string:code>/price", endpoint="price")
api.add_resource(OrderList, "/orders", endpoint="orders")


@app.route("/")
def hello():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True)
