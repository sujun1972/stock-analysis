"""
初始化用户系统
- 运行数据库迁移
- 创建初始超级管理员
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2 import sql
from app.core.config import settings
from app.core.security import hash_password


def execute_migration():
    """执行数据库迁移"""
    print("=" * 60)
    print("开始执行用户系统数据库迁移...")
    print("=" * 60)

    # 读取迁移SQL文件
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "V005__create_user_tables.sql"
    )

    with open(migration_file, "r", encoding="utf-8") as f:
        migration_sql = f.read()

    # 连接数据库
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        # 执行迁移
        cursor.execute(migration_sql)
        print("✅ 数据库迁移执行成功")
    except Exception as e:
        if "already exists" in str(e):
            print(f"⚠️  表已存在，跳过迁移: {e}")
        else:
            print(f"❌ 数据库迁移失败: {e}")
            conn.close()
            return False
    finally:
        cursor.close()
        conn.close()

    return True


def create_super_admin():
    """创建初始超级管理员"""
    print("\n" + "=" * 60)
    print("创建初始超级管理员...")
    print("=" * 60)

    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor()

    try:
        # 检查是否已存在超级管理员
        cursor.execute("SELECT id FROM users WHERE email = %s", (settings.INITIAL_SUPER_ADMIN_EMAIL,))
        existing = cursor.fetchone()

        if existing:
            print(f"⚠️  超级管理员已存在: {settings.INITIAL_SUPER_ADMIN_EMAIL}")
            cursor.close()
            conn.close()
            return True

        # 创建超级管理员
        password_hash = hash_password(settings.INITIAL_SUPER_ADMIN_PASSWORD)

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role, is_active, is_email_verified, full_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            settings.INITIAL_SUPER_ADMIN_USERNAME,
            settings.INITIAL_SUPER_ADMIN_EMAIL,
            password_hash,
            "super_admin",
            True,
            True,
            "系统管理员"
        ))

        user_id = cursor.fetchone()[0]
        conn.commit()

        print(f"✅ 超级管理员创建成功!")
        print(f"   用户名: {settings.INITIAL_SUPER_ADMIN_USERNAME}")
        print(f"   邮箱: {settings.INITIAL_SUPER_ADMIN_EMAIL}")
        print(f"   密码: {settings.INITIAL_SUPER_ADMIN_PASSWORD}")
        print(f"   用户ID: {user_id}")
        print(f"\n⚠️  请尽快修改默认密码！")

    except Exception as e:
        print(f"❌ 创建超级管理员失败: {e}")
        conn.rollback()
        cursor.close()
        conn.close()
        return False
    finally:
        cursor.close()
        conn.close()

    return True


def verify_installation():
    """验证安装"""
    print("\n" + "=" * 60)
    print("验证用户系统安装...")
    print("=" * 60)

    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor()

    try:
        # 检查表是否存在
        tables = ["users", "user_quotas", "login_history", "user_activity_logs", "refresh_tokens"]
        for table in tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """, (table,))
            exists = cursor.fetchone()[0]
            status = "✅" if exists else "❌"
            print(f"{status} 表 {table}: {'已创建' if exists else '不存在'}")

        # 统计用户数
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"\n📊 当前用户数: {user_count}")

        # 统计各角色用户数
        cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
        role_stats = cursor.fetchall()
        print("📊 角色分布:")
        for role, count in role_stats:
            print(f"   - {role}: {count}")

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        cursor.close()
        conn.close()
        return False
    finally:
        cursor.close()
        conn.close()

    return True


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("用户系统初始化工具")
    print("=" * 60)
    print(f"数据库: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}")
    print(f"环境: {settings.ENVIRONMENT}")
    print("=" * 60)

    # 1. 执行迁移
    if not execute_migration():
        print("\n❌ 初始化失败")
        sys.exit(1)

    # 2. 创建超级管理员
    if not create_super_admin():
        print("\n❌ 初始化失败")
        sys.exit(1)

    # 3. 验证安装
    if not verify_installation():
        print("\n❌ 初始化失败")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ 用户系统初始化完成！")
    print("=" * 60)
    print("\n接下来的步骤：")
    print("1. 访问 http://localhost:3002 进入Admin管理后台")
    print("2. 使用以下凭据登录：")
    print(f"   邮箱: {settings.INITIAL_SUPER_ADMIN_EMAIL}")
    print(f"   密码: {settings.INITIAL_SUPER_ADMIN_PASSWORD}")
    print("3. 登录后请立即修改默认密码")
    print("4. 开始创建其他管理员和用户")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
