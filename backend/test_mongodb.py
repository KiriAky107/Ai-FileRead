"""
MongoDB 数据库连接测试
"""
import asyncio
from app.core.database.mongodb import mongodb


async def test_mongodb():
    print("=" * 50)
    print("MongoDB 数据库连接测试")
    print("=" * 50)

    try:
        # 连接
        await mongodb.connect()
        print(f"✓ MongoDB 连接成功: {mongodb.client}")

        # 测试插入
        test_doc = {"test": "hello", "value": 123}
        doc_id = await mongodb.client.test_database.test_collection.insert_one(test_doc)
        print(f"✓ 写入测试成功, ID: {doc_id.inserted_id}")

        # 测试查询
        doc = await mongodb.client.test_database.test_collection.find_one({"test": "hello"})
        print(f"✓ 读取测试成功: {doc}")

        # 删除测试数据
        await mongodb.client.test_database.test_collection.delete_one({"test": "hello"})
        print(f"✓ 删除测试数据成功")

        # 列出数据库
        dbs = await mongodb.client.list_database_names()
        print(f"✓ 数据库列表: {dbs}")

        print("\n✓ MongoDB 测试通过!")
        return True

    except Exception as e:
        print(f"\n✗ MongoDB 测试失败: {e}")
        return False
    finally:
        await mongodb.close()


if __name__ == "__main__":
    asyncio.run(test_mongodb())
