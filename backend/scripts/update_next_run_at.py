#!/usr/bin/env python
"""
更新所有定时任务的 next_run_at 字段
使用 croniter 库计算每个任务的下次执行时间
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, '/app')

import psycopg2
from croniter import croniter
from loguru import logger

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'timescaledb'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_DATABASE', 'stock_analysis'),
    'user': os.getenv('DB_USER', 'stock_user'),
    'password': os.getenv('DB_PASSWORD', 'stock_password_123')
}

def calculate_next_run_time(cron_expr: str) -> datetime:
    """计算下次执行时间"""
    try:
        cron = croniter(cron_expr, datetime.now())
        return cron.get_next(datetime)
    except Exception as e:
        logger.error(f"Failed to calculate next run time for cron: {cron_expr}, error: {e}")
        return None

def update_all_tasks():
    """更新所有任务的 next_run_at 字段"""
    conn = None
    cursor = None
    try:
        # 连接数据库
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 获取所有启用的任务
        cursor.execute("SELECT id, task_name, cron_expression FROM scheduled_tasks WHERE enabled = TRUE")
        tasks = cursor.fetchall()

        logger.info(f"Found {len(tasks)} enabled tasks to update")

        # 更新每个任务的 next_run_at
        updated_count = 0
        for task_id, task_name, cron_expr in tasks:
            next_run = calculate_next_run_time(cron_expr)
            if next_run:
                cursor.execute(
                    "UPDATE scheduled_tasks SET next_run_at = %s WHERE id = %s",
                    (next_run, task_id)
                )
                logger.info(f"Updated task {task_name} (ID: {task_id}) - next run: {next_run}")
                updated_count += 1
            else:
                logger.warning(f"Failed to update task {task_name} (ID: {task_id}) - invalid cron: {cron_expr}")

        # 提交事务
        conn.commit()
        logger.success(f"Successfully updated {updated_count} tasks")

    except Exception as e:
        logger.error(f"Database error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting next_run_at update script...")
    update_all_tasks()
    logger.info("Script completed")