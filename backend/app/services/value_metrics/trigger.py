"""价值度量重算触发器

三层防护：
  1. Redis Set 合批去重：5 个同步源完成后把脏股票塞进 value_metrics:dirty，
     Celery Beat 每 5 分钟 flush 一次批量重算
  2. 全市场触发冷却锁：daily_basic/report_rc 同步完成会触发全量重算，
     用 Redis 分布式锁 + 10 分钟 TTL 防雪崩
  3. Redis 不可用时优雅降级（只记日志，不阻塞主同步链路）

触发场景（5 源）：
  - stock_income 同步完成         → mark_dirty(ts_codes=[...])
  - stock_balancesheet 同步完成   → mark_dirty(ts_codes=[...])
  - stock_fina_indicator 同步完成 → mark_dirty(ts_codes=[...])
  - daily_basic 同步完成          → trigger_full()  (市值变化影响 EV)
  - report_rc 同步完成            → trigger_full()  (券商预期变化影响 IV)
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from loguru import logger

from app.core.redis_lock import redis_client


DIRTY_SET_KEY = "value_metrics:dirty"
FULL_RECOMPUTE_LOCK_KEY = "value_metrics:full_recompute:cooldown"
FULL_RECOMPUTE_COOLDOWN_SEC = 600  # 10 分钟冷却，防 daily_basic 被多次点触发雪崩


class ValueMetricsTrigger:
    """Redis Set / 冷却锁的薄封装。静态方法，无状态。"""

    @staticmethod
    def mark_dirty(ts_codes: Iterable[str], source: str = "unknown") -> int:
        """把一批股票塞进 dirty set，等待 flush 时批量重算。"""
        codes = [c for c in dict.fromkeys(ts_codes) if c]
        if not codes:
            return 0
        if redis_client is None:
            logger.warning(f"[value_metrics] Redis 不可用，跳过 mark_dirty(source={source}, n={len(codes)})")
            return 0
        try:
            added = redis_client.sadd(DIRTY_SET_KEY, *codes)
            logger.debug(
                f"[value_metrics] mark_dirty source={source} received={len(codes)} new={added}"
            )
            return int(added or 0)
        except Exception as e:
            logger.warning(f"[value_metrics] mark_dirty 失败 source={source}: {e}")
            return 0

    @staticmethod
    def pop_dirty_batch(max_size: int = 5000) -> List[str]:
        """原子地捞出 dirty set 的全部成员并清空。Celery flush 任务用。"""
        if redis_client is None:
            return []
        try:
            # SPOP + count 原子出队（空集合返回 []）
            codes = redis_client.spop(DIRTY_SET_KEY, max_size)
            if codes is None:
                return []
            if isinstance(codes, (str, bytes)):
                codes = [codes]
            return [c.decode() if isinstance(c, bytes) else c for c in codes]
        except Exception as e:
            logger.warning(f"[value_metrics] pop_dirty_batch 失败: {e}")
            return []

    @staticmethod
    def trigger_full(source: str = "unknown") -> bool:
        """请求全市场重算。有 10 分钟冷却锁，避免多源同步日触发雪崩。
        返回 True 表示成功派发任务（或已在冷却中、被合并）。
        """
        if redis_client is None:
            logger.warning(f"[value_metrics] Redis 不可用，跳过 trigger_full(source={source})")
            return False
        try:
            # SET NX EX：只有不存在时才设置（即"获得冷却锁"）
            acquired = redis_client.set(
                FULL_RECOMPUTE_LOCK_KEY, source,
                nx=True, ex=FULL_RECOMPUTE_COOLDOWN_SEC,
            )
            if not acquired:
                logger.debug(f"[value_metrics] trigger_full 冷却中，合并 source={source}")
                return True
            # 延迟导入，避免循环依赖
            from app.celery_app import celery_app
            celery_app.send_task("tasks.recompute_value_metrics_all", kwargs={"source": source})
            logger.info(f"[value_metrics] 已派发全市场重算任务 source={source}")
            return True
        except Exception as e:
            logger.warning(f"[value_metrics] trigger_full 失败 source={source}: {e}")
            return False

    @staticmethod
    def dirty_set_size() -> int:
        if redis_client is None:
            return 0
        try:
            return int(redis_client.scard(DIRTY_SET_KEY) or 0)
        except Exception:
            return 0

    @staticmethod
    def full_cooldown_remaining() -> Optional[int]:
        """返回全市场重算冷却锁剩余秒数；无锁返回 None。"""
        if redis_client is None:
            return None
        try:
            ttl = redis_client.ttl(FULL_RECOMPUTE_LOCK_KEY)
            return int(ttl) if ttl and ttl > 0 else None
        except Exception:
            return None
