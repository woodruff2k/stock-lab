// use stocklab
db.createCollection("code_info")
db.createCollection("price_info")
db.createCollection("corp_info")
db.createCollection("credit_info")
db.createCollection("short_info")
db.createCollection("agent_info")
db.createCollection("order")
db.price_info.insertOne({"code": "1", "name": "SAMSUNG", "price": 123, "time":new Timestamp()})
db.price_info.insertMany([{"code": "2", "name": "LG", "price": 234, "time":new Timestamp()},
{"code": "3", "name": "SK", "price": 345, "time":new Timestamp()}]);
db.price_info.find()
db.price_info.find({code: "1"})
db.price_info.find({price: {$gt: 300}})
db.price_info.find({price: {$in: [123, 345]}}, {_id:0})
db.price_info.find({price: {$in: [123, 345]}}, {_id:1})

db.price_info.updateOne({code: "2"}, {$set: {price: 456}})
db.price_info.find({code: "2"})

db.price_info.updateMany({$or: [{code: "2"}, {code: "3"}]}, {$set: {price: 111}})
db.price_info.find()

db.corp_info.insertMany([
{"item": "SamSung SDS",   "related": "SamSung", "qty": 25,  "tags": ["blank", "red"],          "account": [14, 21]},
{"item": "LG CNS",        "related": "LG",      "qty": 50,  "tags": ["red", "blank"],          "account": [14, 21]},
{"item": "SK Telecom",    "related": "SK",      "qty": 100, "tags": ["red", "blank", "plain"], "account": [14, 21]},
{"item": "HYUNDAI MOBIS", "related": "HYUNDAI", "qty": 75,  "tags": ["blank", "red"],          "account": [22.85, 30]},
{"item": "SamSung SDI",   "related": "SamSung", "qty": 25,  "tags": ["blank", "red"],          "account": [14, 21]},
{"item": "LG Telecom",    "related": "LG",      "qty": 50,  "tags": ["red", "blank"],          "account": [14, 21]},
{"item": "SK Innovation", "related": "SK",      "qty": 50,  "tags": ["red", "blank"],          "account": [14, 21]}]);
db.corp_info.find()
db.corp_info.find({tags: ["red", "blank"]})
db.corp_info.find({tags: "red"})
db.corp_info.find({account: {$gt: 15, $lt: 20}})
db.corp_info.find({account: {$elemMatch: {$gt: 22, $lt: 30}}})
db.corp_info.find({"account.1": {$gt: 25}})
db.corp_info.find({tags: {$size: 2}})
db.corp_info.updateOne({related: "HYUNDAI"}, {$push: {tags: "white"}})
db.corp_info.find({item: "HYUNDAI MOBIS"})
db.corp_info.aggregate([{$match: {"account.1": {$gt: 20}}}, {$group: {_id:"$related", total: {$sum: "$qty"}}}])
db.corp_info.aggregate([{$match: {item: "SamSung SDS"}}, {$unwind: "$tags"}])

// db.corp_info.createIndex({"$**": "text"})
db.corp_info.createIndex({item: "text", related: "text", tags: "text"})
db.corp_info.find({$text: {$search: "CNS"}})
db.corp_info.find({$text: {$search: "red"}})
db.corp_info.find({$text: {$search: "SamSung LG"}})
db.corp_info.find({$text: {$search: "\"LG CNS\""}})
db.corp_info.find({$text: {$search: "SamSung -SDS"}})