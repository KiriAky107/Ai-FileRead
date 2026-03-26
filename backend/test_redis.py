"""
Redis 数据库连接测试
"""
import asyncio
from app.core.database.redis_db import redis_db


async def test_redis():
    print("=" * 50)
    print("Redis 数据库连接测试")
    print("=" * 50)

    try:
        # 连接
        await redis_db.connect()
        print(f"✓ Redis 连接成功")

        # 测试写入
        await redis_db.client.set("test_key", "hello_redis")
        print(f"✓ 写入测试成功")

        # 测试读取
        value = await redis_db.client.get("test_key")
        print(f"✓ 读取测试成功: {value}")

        # 测试删除
        await redis_db.client.delete("test_key")
        print(f"✓ 删除测试成功")

        # 测试任务状态
        await redis_db.set_task_status("test_task", "processing", {"progress": 50})
        status = await redis_db.get_task_status("test_task")
        print(f"✓ 任务状态测试成功: {status}")

        print("\n✓ Redis 测试通过!")
        return True

    except Exception as e:
        print(f"\n✗ Redis 测试失败: {e}")
        return False
    finally:
        await redis_db.close()


if __name__ == "__main__":
    asyncio.run(test_redis())
