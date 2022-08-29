from pymongo.cursor import CursorType
from pymongo import MongoClient
import configparser


class MongoDBHandler:

    def __init__(self):
        config = configparser.ConfigParser()
        config.read("../conf/config.ini")
        # config.sections()
        host = config["MONGODB"]["host"]
        port = config["MONGODB"]["port"]
        self._client = MongoClient(host, int(port))

    def insertOne(self, data, db_name=None, collection_name=None):
        if not isinstance(data, dict):
            raise Exception("data type should be dict")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].insert_one(data).inserted_id

    def insertMany(self, data, db_name=None, collection_name=None):
        if not isinstance(data, list):
            raise Exception("data type should be list")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].insert_many(data).inserted_ids

    def findOne(self, condition=None, db_name=None, collection_name=None):
        if condition is None or not isinstance(condition, dict):
            condition = {}
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].find_one(condition)

    def find(self, condition=None, db_name=None, collection_name=None):
        if condition is None or not isinstance(condition, dict):
            condition = {}
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        # no_cursor_timeout=True, cursor_type=CursorType.EXHAUST for BigData
        return self._client[db_name][collection_name].find(condition, no_cursor_timeout=True,
                                                           cursor_type=CursorType.EXHAUST)

    def deleteMany(self, condition=None, db_name=None, collection_name=None):
        if condition is None or not isinstance(condition, dict):
            raise Exception("Need to condition")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].delete_many(condition)

    def updateOne(self, condition=None, update_value=None, db_name=None, collection_name=None, upsert=True):
        if condition is None or not isinstance(condition, dict):
            raise Exception("Need to condition")
        if update_value is None:
            raise Exception("Need to update value")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].update_one(filter=condition, update=update_value, upsert=upsert)

    def updateMany(self, condition=None, update_value=None, db_name=None, collection_name=None, upsert=True):
        if condition is None or not isinstance(condition, dict):
            raise Exception("Need to condition")
        if update_value is None:
            raise Exception("Need to update value")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].update_many(filter=condition, update=update_value, upsert=upsert)

    def aggregate(self, pipeline=None, db_name=None, collection_name=None):
        if pipeline is None or not isinstance(pipeline, list):
            raise Exception("Need to condition")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].aggregate(pipeline)

    def text_search(self, text=None, db_name=None, collection_name=None):
        if text is None or not isinstance(text, str):
            raise Exception("Need to condition")
        if db_name is None or collection_name is None:
            raise Exception("Need to param db_name, collection_name")
        return self._client[db_name][collection_name].find({"$text": {"$search": text}})
