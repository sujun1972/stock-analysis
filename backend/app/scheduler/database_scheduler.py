"""
自定义Celery Beat调度器
从PostgreSQL数据库动态读取定时任务配置，支持实时更新（无需重启）

核心功能：
- 从scheduled_tasks表读取任务配置
- 每30秒自动同步数据库配置变更
- 支持启用/禁用任务
- 支持修改Cron表达式
- 支持任务参数配置
"""

from celery.beat import Scheduler, ScheduleEntry
from celery.schedules import crontab
from datetime import datetime
from loguru import logger
import json
from typing import Dict, Any


class DatabaseScheduler(Scheduler):
    """从数据库读取定时任务配置的调度器"""

    # Celery任务名称映射表
    # 将数据库中的module字段映射到实际的Celery任务名称
    TASK_MAPPING = {
        'sentiment': 'sentiment.daily_sync_17_30',
        'sentiment_ai': 'sentiment.ai_analysis_18_00',
        'premarket': 'premarket.full_workflow_8_00',
        'stock_list': 'sync.stock_list',
        'new_stocks': 'sync.new_stocks',
        'delisted_stocks': 'sync.delisted_stocks',
        'daily': 'sync.daily_batch',
        'concept': 'sync.concept',
        'moneyflow_hsgt': 'tasks.sync_moneyflow_hsgt_daily',
        'moneyflow_mkt_dc': 'tasks.sync_moneyflow_mkt_dc_daily',
    }

    def __init__(self, *args, **kwargs):
        """初始化调度器"""
        self.last_sync = None
        self.sync_interval = 30  # 每30秒从数据库同步一次
        self._db_schedule = {}  # 数据库中的定时任务
        super().__init__(*args, **kwargs)
        logger.info("🔧 DatabaseScheduler 已初始化")

    def setup_schedule(self):
        """初始化时加载数据库中的定时任务"""
        logger.info("📋 正在从数据库加载定时任务配置...")
        self._db_schedule = self.load_schedule_from_db()
        self.merge_inplace(self._db_schedule)
        logger.info(f"✅ 定时任务加载完成，共 {len(self._db_schedule)} 个任务")

    def load_schedule_from_db(self) -> Dict[str, Dict[str, Any]]:
        """
        从数据库加载定时任务配置

        Returns:
            任务配置字典，格式:
            {
                'db-task-name': {
                    'task': 'celery.task.name',
                    'schedule': crontab(...),
                    'kwargs': {...}
                }
            }
        """
        try:
            from src.database.db_manager import DatabaseManager

            db = DatabaseManager()

            # 只查询已启用的定时任务
            query = """
                SELECT
                    task_name,
                    module,
                    cron_expression,
                    params
                FROM scheduled_tasks
                WHERE enabled = true
                ORDER BY id
            """

            result = db._execute_query(query)

            schedule = {}
            for row in result:
                task_name, module, cron_expr, params = row

                try:
                    # 解析Cron表达式 (格式: "分 时 日 月 周")
                    schedule_entry = self._parse_cron_expression(cron_expr)
                    if not schedule_entry:
                        logger.warning(f"⚠️  跳过任务 {task_name}: Cron表达式解析失败")
                        continue

                    # 从映射表获取Celery任务名称
                    celery_task = self.TASK_MAPPING.get(module)
                    if not celery_task:
                        logger.warning(f"⚠️  跳过任务 {task_name}: 模块 '{module}' 没有对应的Celery任务")
                        continue

                    # 解析任务参数
                    task_params = {}
                    if params:
                        try:
                            task_params = json.loads(params) if isinstance(params, str) else params
                        except json.JSONDecodeError:
                            logger.warning(f"⚠️  任务 {task_name}: 参数解析失败，使用空参数")

                    # 构建任务配置
                    schedule[f'db-{task_name}'] = {
                        'task': celery_task,
                        'schedule': schedule_entry,
                        'kwargs': task_params,
                        'options': {
                            'expires': 3600,  # 1小时后过期
                        }
                    }

                    logger.debug(f"  ✓ 加载任务: {task_name} -> {celery_task} ({cron_expr})")

                except Exception as e:
                    logger.error(f"❌ 解析任务 {task_name} 失败: {e}")
                    continue

            return schedule

        except Exception as e:
            logger.error(f"❌ 从数据库加载定时任务失败: {e}")
            return {}

    def _parse_cron_expression(self, cron_expr: str):
        """
        解析Cron表达式为Celery crontab对象

        Args:
            cron_expr: Cron表达式，格式: "分 时 日 月 周"

        Returns:
            celery.schedules.crontab对象，解析失败返回None
        """
        try:
            parts = cron_expr.strip().split()
            if len(parts) != 5:
                logger.warning(f"⚠️  Cron表达式格式错误: {cron_expr} (需要5个字段)")
                return None

            minute, hour, day_of_month, month_of_year, day_of_week = parts

            return crontab(
                minute=minute,
                hour=hour,
                day_of_month=day_of_month,
                month_of_year=month_of_year,
                day_of_week=day_of_week
            )
        except Exception as e:
            logger.error(f"❌ 解析Cron表达式失败 '{cron_expr}': {e}")
            return None

    def tick(self, **kwargs):
        """
        每次心跳时检查是否需要从数据库重新加载

        这个方法会在每次调度循环时被调用（通常是每几秒一次）
        我们设置了30秒的同步间隔，避免频繁查询数据库
        """
        # 每30秒从数据库同步一次配置
        now = datetime.now()
        if not self.last_sync or (now - self.last_sync).total_seconds() > self.sync_interval:
            logger.debug("⟳ 同步数据库定时任务配置...")

            # 加载最新的数据库配置
            new_schedule = self.load_schedule_from_db()

            # 检测配置是否有变化
            if new_schedule != self._db_schedule:
                logger.info("🔄 检测到定时任务配置变更，正在更新...")

                # 找出新增、删除、修改的任务
                old_keys = set(self._db_schedule.keys())
                new_keys = set(new_schedule.keys())

                added = new_keys - old_keys
                removed = old_keys - new_keys
                modified = {
                    k for k in old_keys & new_keys
                    if self._db_schedule[k] != new_schedule[k]
                }

                if added:
                    logger.info(f"  ➕ 新增任务: {', '.join(added)}")
                if removed:
                    logger.info(f"  ➖ 删除任务: {', '.join(removed)}")
                if modified:
                    logger.info(f"  🔧 修改任务: {', '.join(modified)}")

                # 更新内部缓存
                self._db_schedule = new_schedule

                # 合并到调度器
                self.merge_inplace(new_schedule)

                logger.info(f"✅ 定时任务配置已更新，当前活跃任务: {len(new_schedule)} 个")
            else:
                logger.debug(f"  ℹ️  配置无变化，当前活跃任务: {len(new_schedule)} 个")

            self.last_sync = now

        return super().tick(**kwargs)

    def merge_inplace(self, schedule):
        """
        合并新的调度配置

        这个方法会：
        1. 移除不在新配置中的任务
        2. 添加新配置中的任务
        3. 更新已存在任务的配置
        """
        # 获取当前调度器中的所有数据库任务（以 'db-' 开头）
        current_db_tasks = {
            name for name in self.schedule
            if name.startswith('db-')
        }

        # 移除不在新配置中的任务
        for task_name in current_db_tasks:
            if task_name not in schedule:
                logger.debug(f"  🗑️  移除任务: {task_name}")
                self.schedule.pop(task_name, None)

        # 添加或更新任务
        for task_name, entry in schedule.items():
            if task_name in self.schedule:
                # 更新现有任务
                self.schedule[task_name].update(ScheduleEntry(**entry))
            else:
                # 添加新任务
                self.schedule[task_name] = ScheduleEntry(**entry, name=task_name, app=self.app)
