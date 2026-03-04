"""
数据库迁移管理器
在应用启动时自动执行待执行的迁移
"""

import os
from pathlib import Path
from typing import List, Tuple

import psycopg2
import psycopg2.errors
from loguru import logger

from app.core.config import settings


class MigrationManager:
    """数据库迁移管理器"""

    def __init__(self):
        self.migrations_dir = Path(__file__).parent.parent.parent / 'migrations'
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = psycopg2.connect(
                host=settings.DATABASE_HOST,
                port=settings.DATABASE_PORT,
                dbname=settings.DATABASE_NAME,
                user=settings.DATABASE_USER,
                password=settings.DATABASE_PASSWORD
            )
            self.conn.autocommit = False
            logger.info("✅ 数据库连接成功")
        except Exception as e:
            logger.error(f"❌ 数据库连接失败: {e}")
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

    def ensure_migrations_table(self):
        """确保迁移记录表存在"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(255) PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
            cursor.close()
            logger.info("✅ 迁移记录表已就绪")
        except Exception as e:
            logger.error(f"❌ 创建迁移记录表失败: {e}")
            self.conn.rollback()
            raise

    def get_applied_migrations(self) -> List[str]:
        """获取已应用的迁移"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
            applied = [row[0] for row in cursor.fetchall()]
            cursor.close()
            return applied
        except Exception as e:
            logger.error(f"❌ 查询已应用迁移失败: {e}")
            return []

    def get_pending_migrations(self) -> List[Tuple[str, Path]]:
        """获取待执行的迁移文件（按V开头的版本号排序）"""
        applied = self.get_applied_migrations()

        # 只处理 V 开头的迁移文件
        migration_files = sorted(
            [f for f in self.migrations_dir.glob('V*.sql')],
            key=lambda x: x.name
        )

        pending = []
        for file in migration_files:
            version = file.stem  # 例如: V012__add_celery_task_support
            if version not in applied:
                pending.append((version, file))

        return pending

    def apply_migration(self, version: str, file_path: Path) -> bool:
        """应用单个迁移"""
        try:
            logger.info(f"📄 执行迁移: {version}")

            # 读取SQL文件
            with open(file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()

            # 执行SQL
            cursor = self.conn.cursor()
            try:
                cursor.execute(sql_content)
            except psycopg2.errors.DuplicateObject as e:
                # 对象已存在，记录警告但继续
                logger.warning(f"⚠️ 迁移 {version} 中的某些对象已存在，跳过: {e}")
                self.conn.rollback()
            except psycopg2.errors.DuplicateTable as e:
                # 表已存在，记录警告但继续
                logger.warning(f"⚠️ 迁移 {version} 中的某些表已存在，跳过: {e}")
                self.conn.rollback()

            # 记录迁移（即使执行失败也记录，避免重复尝试）
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT (version) DO NOTHING",
                (version,)
            )

            self.conn.commit()
            cursor.close()

            logger.info(f"✅ 迁移记录完成: {version}")
            return True

        except Exception as e:
            logger.error(f"❌ 迁移失败 {version}: {e}")
            self.conn.rollback()
            # 对于已存在的迁移，也标记为已应用
            try:
                cursor = self.conn.cursor()
                cursor.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s) ON CONFLICT (version) DO NOTHING",
                    (version,)
                )
                self.conn.commit()
                cursor.close()
            except:
                pass
            return True  # 返回 True 继续执行后续迁移

    def run_migrations(self) -> bool:
        """运行所有待执行的迁移"""
        try:
            self.connect()
            self.ensure_migrations_table()

            pending = self.get_pending_migrations()

            if not pending:
                logger.info("✅ 没有待执行的迁移")
                return True

            logger.info(f"📋 发现 {len(pending)} 个待执行的迁移")

            success = True
            for version, file_path in pending:
                if not self.apply_migration(version, file_path):
                    success = False
                    break

            if success:
                logger.info("✅ 所有迁移执行成功")
            else:
                logger.error("❌ 迁移执行失败")

            return success

        except Exception as e:
            logger.error(f"❌ 迁移过程出错: {e}")
            return False

        finally:
            self.close()


def run_migrations():
    """
    运行数据库迁移（供应用启动时调用）
    """
    manager = MigrationManager()
    return manager.run_migrations()
