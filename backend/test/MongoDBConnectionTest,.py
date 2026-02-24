from pymongo import MongoClient

# 连接 MongoDB（带认证）
client = MongoClient('mongodb://admin:20060825fhy.@kronecker.cc:27017/admin')

# 切换到 test 数据库
db = client.test

print(db.name)

# 正确的列出集合的方法
print(db.list_collection_names())