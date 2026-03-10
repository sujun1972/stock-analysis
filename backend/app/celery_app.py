"""
Celery 应用配置
用于异步任务执行（如回测任务）
"""

from celery import Celery
from celery.schedules import crontab
from loguru import logger

from app.core.config import settings

# 创建 Celery 应用实例
celery_app = Celery(
    "stock_analysis",
    broker=f"{settings.REDIS_URL}",  # 使用 Redis 作为消息队列
    backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"  # 使用 Redis DB 1 存储结果
)

# Celery 配置
celery_app.conf.update(
    # 序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # 时区配置
    timezone="Asia/Shanghai",
    enable_utc=True,

    # 任务超时配置
    task_time_limit=3600,  # 硬超时：1小时
    task_soft_time_limit=3000,  # 软超时：50分钟（任务会收到 SoftTimeLimitExceeded 异常）

    # 结果过期时间
    result_expires=86400,  # 24小时后过期

    # 任务执行配置
    task_acks_late=True,  # 任务执行完成后才确认
    worker_prefetch_multiplier=1,  # 每次只预取1个任务（防止长任务阻塞）

    # 任务默认队列（所有任务都使用 default 队列）
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
)

# 手动导入任务（确保任务被注册）
# 自动发现在某些情况下可能不工作，所以我们显式导入
try:
    from app.tasks import backtest_tasks
    logger.info(f"✅ 已加载回测任务模块")
except Exception as e:
    logger.error(f"❌ 加载回测任务模块失败: {e}")

try:
    from app.tasks import ai_strategy_tasks
    logger.info(f"✅ 已加载AI策略生成任务模块")
except Exception as e:
    logger.error(f"❌ 加载AI策略生成任务模块失败: {e}")

try:
    from app.tasks import sentiment_tasks
    logger.info(f"✅ 已加载市场情绪任务模块")
except Exception as e:
    logger.error(f"❌ 加载市场情绪任务模块失败: {e}")

# 自动发现任务模块（作为备用）
celery_app.autodiscover_tasks(['app.tasks'])

# Celery Beat定时任务调度配置
celery_app.conf.beat_schedule = {
    # 每日17:30（北京时间）同步市场情绪数据
    'daily-sentiment-sync-17-30': {
        'task': 'sentiment.daily_sync_17_30',
        'schedule': crontab(
            hour=9,       # UTC 9点 = 北京时间17点
            minute=30,
            day_of_week='1-5'  # 周一到周五
        ),
        'options': {
            'expires': 3600,  # 1小时后过期
        }
    },
}
