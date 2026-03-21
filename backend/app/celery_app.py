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

    # 结果持久化配置
    result_backend=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1",  # 确保结果被保存
    result_persistent=True,  # 持久化任务结果

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

try:
    from app.tasks import sentiment_ai_analysis_task
    logger.info(f"✅ 已加载情绪AI分析任务模块")
except Exception as e:
    logger.error(f"❌ 加载情绪AI分析任务模块失败: {e}")

try:
    from app.tasks import premarket_tasks
    logger.info(f"✅ 已加载盘前预期管理任务模块")
except Exception as e:
    logger.error(f"❌ 加载盘前任务模块失败: {e}")

try:
    from app.tasks import sync_tasks
    logger.info(f"✅ 已加载数据同步任务模块")
except Exception as e:
    logger.error(f"❌ 加载数据同步任务模块失败: {e}")

try:
    from app.tasks import extended_sync_tasks
    logger.info(f"✅ 已加载扩展数据同步任务模块")
except Exception as e:
    logger.error(f"❌ 加载扩展数据同步任务模块失败: {e}")

try:
    from app.tasks import notification_tasks
    logger.info(f"✅ 已加载通知发送任务模块")
except Exception as e:
    logger.error(f"❌ 加载通知发送任务模块失败: {e}")

try:
    from app.tasks import moneyflow_hsgt_tasks
    logger.info(f"✅ 已加载沪深港通资金流向任务模块")
except Exception as e:
    logger.error(f"❌ 加载沪深港通资金流向任务模块失败: {e}")

try:
    from app.tasks import moneyflow_mkt_dc_tasks
    logger.info(f"✅ 已加载大盘资金流向任务模块")
except Exception as e:
    logger.error(f"❌ 加载大盘资金流向任务模块失败: {e}")

try:
    from app.tasks import moneyflow_ind_dc_tasks
    logger.info(f"✅ 已加载板块资金流向任务模块")
except Exception as e:
    logger.error(f"❌ 加载板块资金流向任务模块失败: {e}")

try:
    from app.tasks import moneyflow_stock_dc_tasks
    logger.info(f"✅ 已加载个股资金流向（DC）任务模块")
except Exception as e:
    logger.error(f"❌ 加载个股资金流向（DC）任务模块失败: {e}")

try:
    from app.tasks import moneyflow_tasks
    logger.info(f"✅ 已加载个股资金流向（Tushare）任务模块")
except Exception as e:
    logger.error(f"❌ 加载个股资金流向（Tushare）任务模块失败: {e}")

try:
    from app.tasks import margin_tasks
    logger.info(f"✅ 已加载融资融券交易汇总任务模块")
except Exception as e:
    logger.error(f"❌ 加载融资融券交易汇总任务模块失败: {e}")

try:
    from app.tasks import slb_len_tasks
    logger.info(f"✅ 已加载转融资交易汇总任务模块")
except Exception as e:
    logger.error(f"❌ 加载转融资交易汇总任务模块失败: {e}")

try:
    from app.tasks import margin_detail_tasks
    logger.info(f"✅ 已加载融资融券交易明细任务模块")
except Exception as e:
    logger.error(f"❌ 加载融资融券交易明细任务模块失败: {e}")

try:
    from app.tasks import top_list_tasks
    logger.info(f"✅ 已加载龙虎榜每日明细任务模块")
except Exception as e:
    logger.error(f"❌ 加载龙虎榜每日明细任务模块失败: {e}")

try:
    from app.tasks import top_inst_tasks
    logger.info(f"✅ 已加载龙虎榜机构明细任务模块")
except Exception as e:
    logger.error(f"❌ 加载龙虎榜机构明细任务模块失败: {e}")

try:
    from app.tasks import limit_list_tasks
    logger.info(f"✅ 已加载涨跌停列表任务模块")
except Exception as e:
    logger.error(f"❌ 加载涨跌停列表任务模块失败: {e}")

try:
    from app.tasks import limit_step_tasks
    logger.info(f"✅ 已加载连板天梯任务模块")
except Exception as e:
    logger.error(f"❌ 加载连板天梯任务模块失败: {e}")

try:
    from app.tasks import limit_cpt_tasks
    logger.info(f"✅ 已加载最强板块统计任务模块")
except Exception as e:
    logger.error(f"❌ 加载最强板块统计任务模块失败: {e}")

# 自动发现任务模块（作为备用）
celery_app.autodiscover_tasks(['app.tasks'])

# 注册Celery信号处理器（自动更新任务历史）
try:
    import app.celery_signals
    logger.info(f"✅ 已注册Celery信号处理器")
except Exception as e:
    logger.error(f"❌ 注册Celery信号处理器失败: {e}")

# ==========================================
# Celery Beat 定时任务调度配置
# ==========================================
# 使用自定义DatabaseScheduler从数据库动态加载定时任务
# 支持在Admin界面实时修改任务配置，无需重启服务

# 设置使用数据库调度器
celery_app.conf.beat_scheduler = 'app.scheduler.database_scheduler:DatabaseScheduler'

# 保留原有的硬编码定时任务作为fallback（可选）
# 如果数据库中没有配置，将使用以下默认配置
celery_app.conf.beat_schedule = {
    # 以下任务已迁移到数据库配置，默认禁用
    # 请在Admin管理后台的"系统设置 -> 定时任务"页面中启用和配置

    # 示例：每日17:30（北京时间）同步市场情绪数据
    # 'daily-sentiment-sync-17-30': {
    #     'task': 'sentiment.daily_sync_17_30',
    #     'schedule': crontab(hour=9, minute=30, day_of_week='1-5'),  # UTC时间
    #     'options': {'expires': 3600}
    # },
}
