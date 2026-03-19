"""
任务执行器
用于手动触发定时任务执行
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from app.celery_app import celery_app


class TaskExecutor:
    """定时任务执行器，统一处理各种任务的手动执行"""

    # 任务映射表：将数据库中的模块名映射到实际的Celery任务
    TASK_MAPPING = {
        # 数据同步任务
        'stock_list': {
            'task': 'sync.stock_list',
            'name': '股票列表同步'
        },
        'new_stocks': {
            'task': 'sync.new_stocks',
            'name': '新股同步',
            'default_params': {'days': 30}
        },
        'delisted_stocks': {
            'task': 'sync.delisted_stocks',
            'name': '退市股票同步'
        },
        'daily': {
            'task': 'sync.daily_batch',
            'name': '日线数据同步',
            'default_params': {'years': 1}
        },
        'concept': {
            'task': 'sync.concept',
            'name': '概念板块同步'
        },

        # 扩展数据同步
        'extended.sync_daily_basic': {
            'task': 'extended.sync_daily_basic',
            'name': '每日指标同步'
        },
        'extended.sync_moneyflow': {
            'task': 'extended.sync_moneyflow',
            'name': '资金流向同步'
        },
        'tasks.sync_moneyflow_hsgt': {
            'task': 'tasks.sync_moneyflow_hsgt',
            'name': '沪深港通资金流向同步'
        },
        'tasks.sync_moneyflow_mkt_dc': {
            'task': 'tasks.sync_moneyflow_mkt_dc',
            'name': '大盘资金流向同步'
        },
        'extended.sync_margin': {
            'task': 'extended.sync_margin',
            'name': '融资融券同步'
        },
        'extended.sync_stk_limit': {
            'task': 'extended.sync_stk_limit',
            'name': '涨跌停价格同步'
        },
        'extended.sync_block_trade': {
            'task': 'extended.sync_block_trade',
            'name': '大宗交易同步'
        },
        'extended.sync_adj_factor': {
            'task': 'extended.sync_adj_factor',
            'name': '复权因子同步'
        },
        'extended.sync_suspend': {
            'task': 'extended.sync_suspend',
            'name': '停复牌信息同步'
        },

        # 市场情绪任务
        'sentiment': {
            'task': 'sentiment.daily_sync_17_30',
            'name': '市场情绪数据同步'
        },
        'sentiment.ai_analysis': {
            'task': 'sentiment.ai_analysis_18_00',
            'name': 'AI情绪分析'
        },
        'sentiment.manual_sync': {
            'task': 'sentiment.manual_sync',
            'name': '手动情绪同步',
            'default_params': {'date': None}
        },
        'sentiment.batch_sync': {
            'task': 'sentiment.batch_sync',
            'name': '批量情绪同步'
        },
        'sentiment.calendar_sync': {
            'task': 'sentiment.calendar_sync',
            'name': '交易日历同步',
            'default_params': {'years': [datetime.now().year]}
        },

        # 盘前分析
        'premarket': {
            'task': 'premarket.full_workflow_8_00',
            'name': '盘前完整分析'
        },
        'premarket.sync_data': {
            'task': 'premarket.sync_data_only',
            'name': '盘前数据同步'
        },
        'premarket.generate_analysis': {
            'task': 'premarket.generate_analysis_only',
            'name': '生成AI分析'
        },

        # 通知任务
        'notification.send_email': {
            'task': 'app.tasks.notification_tasks.send_email_notification',
            'name': '发送邮件通知'
        },
        'notification.send_telegram': {
            'task': 'app.tasks.notification_tasks.send_telegram_notification',
            'name': '发送Telegram通知'
        },
        'notification.cleanup': {
            'task': 'app.tasks.notification_tasks.cleanup_expired_notifications',
            'name': '清理过期通知'
        },
        'notification.health_check': {
            'task': 'app.tasks.notification_tasks.notification_health_check',
            'name': '通知系统健康检查'
        },

        # 数据质量监控
        'quality.daily_report': {
            'task': 'app.tasks.quality_tasks.generate_daily_quality_report',
            'name': '生成每日质量报告'
        },
        'quality.weekly_report': {
            'task': 'app.tasks.quality_tasks.generate_weekly_quality_report',
            'name': '生成周度质量报告'
        },
        'quality.real_time_check': {
            'task': 'app.tasks.quality_tasks.real_time_quality_check',
            'name': '实时质量检查'
        },
        'quality.integrity_check': {
            'task': 'app.tasks.quality_tasks.data_integrity_check',
            'name': '数据完整性检查'
        },
        'quality.trend_analysis': {
            'task': 'app.tasks.quality_tasks.quality_trend_analysis',
            'name': '质量趋势分析'
        },
        'quality.cleanup_alerts': {
            'task': 'app.tasks.quality_tasks.cleanup_old_alerts',
            'name': '清理过期告警'
        }
    }

    async def execute_task(
        self,
        task_name: str,
        module: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        执行定时任务

        Args:
            task_name: 任务名称（用于日志）
            module: 模块名称（用于查找对应的Celery任务）
            params: 任务参数

        Returns:
            Celery任务ID

        Raises:
            ValueError: 如果模块没有对应的Celery任务
        """
        # 查找对应的Celery任务
        task_config = self.TASK_MAPPING.get(module)

        if not task_config:
            # 尝试根据任务名称查找（兼容旧格式）
            for key, config in self.TASK_MAPPING.items():
                if task_name in key or key in task_name:
                    task_config = config
                    break

        if not task_config:
            raise ValueError(f"未找到模块 '{module}' 对应的Celery任务")

        celery_task_name = task_config['task']
        friendly_name = task_config.get('name', task_name)

        # 过滤掉元数据参数（如priority, points_consumption等）
        metadata_params = {'priority', 'points_consumption', 'retry_count', 'timeout'}

        # 合并默认参数和用户参数，但排除元数据
        final_params = {}
        if 'default_params' in task_config:
            final_params.update(task_config['default_params'])
        if params:
            # 只保留非元数据参数
            filtered_params = {k: v for k, v in params.items() if k not in metadata_params}
            final_params.update(filtered_params)

        logger.info(f"🚀 手动执行任务: {friendly_name}")
        logger.info(f"   Celery任务: {celery_task_name}")
        logger.info(f"   参数: {final_params}")
        if params:
            logger.info(f"   原始参数: {params}")
            logger.info(f"   已过滤元数据: {[k for k in params.keys() if k in metadata_params]}")

        try:
            # 获取Celery任务
            task = celery_app.send_task(
                celery_task_name,
                kwargs=final_params,
                queue='default'
            )

            logger.info(f"✅ 任务已提交: {friendly_name} (ID: {task.id})")
            return task.id

        except Exception as e:
            logger.error(f"❌ 执行任务失败 {friendly_name}: {e}")
            raise

    def get_task_status(self, celery_task_id: str) -> Dict[str, Any]:
        """
        获取Celery任务状态

        Args:
            celery_task_id: Celery任务ID

        Returns:
            任务状态信息
        """
        from celery.result import AsyncResult

        result = AsyncResult(celery_task_id, app=celery_app)

        status_info = {
            'task_id': celery_task_id,
            'state': result.state,
            'current': 0,
            'total': 100,
            'status': 'PENDING'
        }

        if result.state == 'PENDING':
            status_info['status'] = '等待执行'
        elif result.state == 'STARTED':
            status_info['status'] = '正在执行'
        elif result.state == 'SUCCESS':
            status_info['status'] = '执行成功'
            status_info['result'] = result.result
        elif result.state == 'FAILURE':
            status_info['status'] = '执行失败'
            status_info['error'] = str(result.info)
        else:
            # 处理其他状态
            status_info['status'] = result.state
            if hasattr(result.info, 'get'):
                status_info['current'] = result.info.get('current', 0)
                status_info['total'] = result.info.get('total', 100)

        return status_info

    async def cancel_task(self, celery_task_id: str) -> bool:
        """
        取消Celery任务

        Args:
            celery_task_id: Celery任务ID

        Returns:
            是否成功取消
        """
        try:
            celery_app.control.revoke(celery_task_id, terminate=True)
            logger.info(f"✅ 已取消任务: {celery_task_id}")
            return True
        except Exception as e:
            logger.error(f"❌ 取消任务失败 {celery_task_id}: {e}")
            return False