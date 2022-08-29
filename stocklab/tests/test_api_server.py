from stocklab.service.api_server import app
import unittest
import inspect


class FlaskTestCase(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.app = app.test_client()

    def test_get_codes(self):
        print(inspect.stack()[0][3])
        rv = self.app.get("/codes")
        result = rv.get_json()
        print(len(result["code_list"]))
        assert rv.status_code == 200 and len(result["code_list"]) > 0

    def test_get_codes_with_parameter(self):
        print(inspect.stack()[0][3
              ])
        rv = self.app.get("/codes?market=2")
        result = rv.get_json()
        print(len(result["code_list"]))
        assert rv.status_code == 200 and len(result["code_list"]) > 0

    def test_get_code(self):
        print(inspect.stack()[0][3])
        rv = self.app.get("/codes/005930")
        # print(rv.data, rv.status_code)
        result = rv.get_json()
        print(result)
        assert rv.status_code == 200

    def test_get_prices(self):
        print(inspect.stack()[0][3])
        rv = self.app.get("/codes/002170/price")  # today
        result = rv.get_json()
        print(result)
        assert rv.status_code == 200

    def test_get_prices_with_parameter(self):
        print(inspect.stack()[0][3])
        rv = self.app.get("/codes/002170/price?start_date20190228&end_date=20190228")
        result = rv.get_json()
        # print(result["count"])
        print(result)
        assert rv.status_code == 200

    def test_get_orders(self):
        print(inspect.stack()[0][3])
        rv = self.app.get("/orders?status=buy_ordered")
        result = rv.get_json()
        print(result)
        assert rv.status_code == 200

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
