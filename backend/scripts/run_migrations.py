#!/usr/bin/env python3
"""
数据库迁移脚本
执行实验系统相关的数据库表创建
"""

import sys
import os
from pathlib import Path

# 添加core路径 - 适配Docker和本地环境
core_path = Path(__file__).parent.parent.parent / 'core'
if core_path.exists():
    sys.path.insert(0, str(core_path))
else:
    # Docker环境中core在/app/src
    sys.path.insert(0, '/app/src')

try:
    from database.db_manager import DatabaseManager
except ImportError:
    from src.database.db_manager import DatabaseManager

from loguru import logger

def run_migrations():
    """运行数据库迁移"""

    logger.info("🚀 开始执行数据库迁移...")

    # 初始化数据库管理器
    db = DatabaseManager()

    # 读取SQL文件
    migrations_dir = Path(__file__).parent.parent / 'migrations'
    sql_file = migrations_dir / 'create_experiment_tables.sql'

    if not sql_file.exists():
        logger.error(f"❌ SQL文件不存在: {sql_file}")
        return False

    logger.info(f"📄 读取SQL文件: {sql_file}")

    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # 执行SQL
    try:
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        logger.info("⚙️  执行SQL语句...")
        cursor.execute(sql_content)
        conn.commit()

        cursor.close()
        conn.close()

        logger.info("✅ 数据库迁移完成！")

        # 验证表是否创建成功
        verify_tables(db)

        return True

    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        return False

def verify_tables(db: DatabaseManager):
    """验证表是否创建成功"""

    logger.info("\n🔍 验证数据库表...")

    tables_to_check = [
        'experiment_batches',
        'experiments',
        'parameter_importance',
        'experiment_logs'
    ]

    query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = %s
    """

    for table in tables_to_check:
        result = db._execute_query(query, (table,))
        if result:
            logger.info(f"  ✓ 表 '{table}' 已创建")
        else:
            logger.warning(f"  ✗ 表 '{table}' 未找到")

    # 验证视图
    views_to_check = [
        'model_performance_comparison',
        'batch_statistics'
    ]

    view_query = """
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
        AND table_name = %s
    """

    for view in views_to_check:
        result = db._execute_query(view_query, (view,))
        if result:
            logger.info(f"  ✓ 视图 '{view}' 已创建")
        else:
            logger.warning(f"  ✗ 视图 '{view}' 未找到")

    logger.info("\n✅ 验证完成！\n")

if __name__ == '__main__':
    success = run_migrations()
    sys.exit(0 if success else 1)
