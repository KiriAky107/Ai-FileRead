"""
MySQL 数据库连接测试
"""
import asyncio
from sqlalchemy import text
from app.core.database.mysql import mysql_db


async def test_mysql():
    print("=" * 50)
    print("MySQL 数据库连接测试")
    print("=" * 50)

    try:
        # 测试连接
        async with mysql_db.async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            print(f"✓ MySQL 连接成功: {result.fetchone()}")

        # 测试查询数据库
        async with mysql_db.async_session_factory() as session:
            result = await session.execute(text("SHOW DATABASES"))
            dbs = result.fetchall()
            print(f"✓ 数据库列表: {[db[0] for db in dbs]}")

        print("\n✓ MySQL 测试通过!")
        return True

    except Exception as e:
        print(f"\n✗ MySQL 测试失败: {e}")
        return False
    finally:
        await mysql_db.close()


if __name__ == "__main__":
    asyncio.run(test_mysql())
