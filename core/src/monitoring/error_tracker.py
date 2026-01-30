"""
错误追踪系统

提供错误事件记录、统计、分类和趋势分析功能。
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import hashlib
import json
import traceback


@dataclass
class ErrorEvent:
    """错误事件"""
    error_type: str
    error_message: str
    error_hash: str
    timestamp: datetime
    module: str
    function: str
    severity: str  # CRITICAL, ERROR, WARNING
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class ErrorTracker:
    """错误追踪器"""

    SEVERITY_CRITICAL = "CRITICAL"
    SEVERITY_ERROR = "ERROR"
    SEVERITY_WARNING = "WARNING"

    def __init__(self, db_manager=None):
        """
        初始化错误追踪器

        Args:
            db_manager: 数据库管理器(可选)
        """
        self.db = db_manager
        self._error_events: List[ErrorEvent] = []
        self._error_groups: Dict[str, List[ErrorEvent]] = defaultdict(list)
        self._use_database = db_manager is not None

        # 如果有数据库，初始化表
        if self._use_database:
            self._init_database()

    def _init_database(self) -> None:
        """初始化数据库表"""
        create_tables_sql = """
        -- 错误事件表
        CREATE TABLE IF NOT EXISTS error_events (
            id SERIAL PRIMARY KEY,
            error_hash VARCHAR(64) NOT NULL,
            error_type VARCHAR(255) NOT NULL,
            error_message TEXT NOT NULL,
            severity VARCHAR(20) NOT NULL,
            module VARCHAR(255),
            function VARCHAR(255),
            stack_trace TEXT,
            context JSONB,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            resolved BOOLEAN DEFAULT FALSE,
            resolved_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_error_hash ON error_events(error_hash);
        CREATE INDEX IF NOT EXISTS idx_occurred_at ON error_events(occurred_at DESC);
        CREATE INDEX IF NOT EXISTS idx_severity ON error_events(severity);
        CREATE INDEX IF NOT EXISTS idx_resolved ON error_events(resolved);

        -- 错误统计表
        CREATE TABLE IF NOT EXISTS error_statistics (
            id SERIAL PRIMARY KEY,
            error_hash VARCHAR(64) NOT NULL UNIQUE,
            occurrence_count INT NOT NULL DEFAULT 1,
            first_seen TIMESTAMPTZ NOT NULL,
            last_seen TIMESTAMPTZ NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_error_stats_hash ON error_statistics(error_hash);
        CREATE INDEX IF NOT EXISTS idx_error_stats_count ON error_statistics(occurrence_count DESC);
        """

        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(create_tables_sql)
                conn.commit()
        except Exception as e:
            # 如果数据库初始化失败，降级到内存模式
            self._use_database = False
            print(f"Warning: Failed to initialize error tracking database: {e}")

    def track_error(
        self,
        error: Exception,
        severity: str = SEVERITY_ERROR,
        module: Optional[str] = None,
        function: Optional[str] = None,
        **context
    ) -> str:
        """
        追踪错误

        Args:
            error: 异常对象
            severity: 严重程度 (CRITICAL, ERROR, WARNING)
            module: 模块名称
            function: 函数名称
            **context: 上下文信息

        Returns:
            错误哈希值
        """
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = "".join(traceback.format_exception(
            type(error), error, error.__traceback__
        ))

        # 生成错误哈希（用于分组相同错误）
        error_hash = self._generate_error_hash(
            error_type, error_message, module or "", function or ""
        )

        event = ErrorEvent(
            error_type=error_type,
            error_message=error_message,
            error_hash=error_hash,
            timestamp=datetime.now(),
            module=module or "",
            function=function or "",
            severity=severity,
            stack_trace=stack_trace,
            context=context
        )

        # 记录到内存
        self._error_events.append(event)
        self._error_groups[error_hash].append(event)

        # 持久化到数据库
        if self._use_database:
            try:
                self._persist_error(event)
            except Exception as persist_error:
                print(f"Warning: Failed to persist error to database: {persist_error}")

        return error_hash

    def _generate_error_hash(
        self,
        error_type: str,
        error_message: str,
        module: str,
        function: str
    ) -> str:
        """
        生成错误哈希

        Args:
            error_type: 错误类型
            error_message: 错误消息
            module: 模块名称
            function: 函数名称

        Returns:
            错误哈希值
        """
        # 基于错误类型、模块、函数生成唯一哈希
        # 忽略错误消息中的可变部分
        hash_input = f"{error_type}:{module}:{function}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def _persist_error(self, event: ErrorEvent) -> None:
        """
        持久化错误事件

        Args:
            event: 错误事件
        """
        insert_event_sql = """
        INSERT INTO error_events (
            error_hash, error_type, error_message, severity,
            module, function, stack_trace, context
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        update_stats_sql = """
        INSERT INTO error_statistics (error_hash, first_seen, last_seen)
        VALUES (%s, NOW(), NOW())
        ON CONFLICT (error_hash) DO UPDATE
        SET occurrence_count = error_statistics.occurrence_count + 1,
            last_seen = NOW()
        """

        with self.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(insert_event_sql, (
                    event.error_hash,
                    event.error_type,
                    event.error_message,
                    event.severity,
                    event.module,
                    event.function,
                    event.stack_trace,
                    json.dumps(event.context)
                ))

                cur.execute(update_stats_sql, (event.error_hash,))
            conn.commit()

    def get_error_statistics(
        self,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取错误统计

        Args:
            window_hours: 时间窗口(小时)

        Returns:
            错误统计信息
        """
        cutoff = datetime.now() - timedelta(hours=window_hours)

        # 从内存中统计
        recent_errors = [e for e in self._error_events if e.timestamp >= cutoff]

        if not recent_errors:
            return {
                "total_errors": 0,
                "unique_errors": 0,
                "by_type": [],
                "by_severity": {},
                "window_hours": window_hours
            }

        # 按类型统计
        by_type = defaultdict(lambda: defaultdict(int))
        by_severity = defaultdict(int)

        for error in recent_errors:
            by_type[error.error_type][error.severity] += 1
            by_severity[error.severity] += 1

        # 转换为列表格式
        type_stats = [
            {
                "error_type": error_type,
                "severity_counts": dict(severity_counts),
                "total_count": sum(severity_counts.values())
            }
            for error_type, severity_counts in by_type.items()
        ]
        type_stats.sort(key=lambda x: x["total_count"], reverse=True)

        # 计算唯一错误数
        unique_hashes = set(e.error_hash for e in recent_errors)

        return {
            "total_errors": len(recent_errors),
            "unique_errors": len(unique_hashes),
            "by_type": type_stats,
            "by_severity": dict(by_severity),
            "window_hours": window_hours
        }

    def get_error_trends(
        self,
        error_hash: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        获取错误趋势

        Args:
            error_hash: 错误哈希值
            days: 天数

        Returns:
            错误趋势数据
        """
        cutoff = datetime.now() - timedelta(days=days)

        # 从内存中获取数据
        relevant_errors = [
            e for e in self._error_groups.get(error_hash, [])
            if e.timestamp >= cutoff
        ]

        # 按小时分组
        hourly_counts = defaultdict(int)
        for error in relevant_errors:
            hour_key = error.timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_counts[hour_key] += 1

        # 转换为列表并排序
        trends = [
            {"timestamp": hour.isoformat(), "count": count}
            for hour, count in sorted(hourly_counts.items())
        ]

        return trends

    def get_top_errors(
        self,
        limit: int = 10,
        window_hours: int = 24,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取最频繁的错误

        Args:
            limit: 返回数量限制
            window_hours: 时间窗口(小时)
            severity: 严重程度筛选

        Returns:
            错误列表
        """
        cutoff = datetime.now() - timedelta(hours=window_hours)

        # 过滤错误
        recent_errors = [
            e for e in self._error_events
            if e.timestamp >= cutoff and (severity is None or e.severity == severity)
        ]

        # 按哈希分组统计
        error_counts = defaultdict(lambda: {
            "count": 0,
            "first_seen": None,
            "last_seen": None,
            "sample_event": None
        })

        for error in recent_errors:
            stats = error_counts[error.error_hash]
            stats["count"] += 1

            if stats["first_seen"] is None or error.timestamp < stats["first_seen"]:
                stats["first_seen"] = error.timestamp

            if stats["last_seen"] is None or error.timestamp > stats["last_seen"]:
                stats["last_seen"] = error.timestamp

            if stats["sample_event"] is None:
                stats["sample_event"] = error

        # 转换为列表并排序
        top_errors = [
            {
                "error_hash": error_hash,
                "error_type": stats["sample_event"].error_type,
                "error_message": stats["sample_event"].error_message,
                "severity": stats["sample_event"].severity,
                "count": stats["count"],
                "first_seen": stats["first_seen"].isoformat(),
                "last_seen": stats["last_seen"].isoformat(),
            }
            for error_hash, stats in error_counts.items()
        ]

        top_errors.sort(key=lambda x: x["count"], reverse=True)

        return top_errors[:limit]

    def get_error_details(
        self,
        error_hash: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        获取错误详情

        Args:
            error_hash: 错误哈希值
            limit: 返回事件数量限制

        Returns:
            错误详情
        """
        events = self._error_groups.get(error_hash, [])

        if not events:
            return {}

        # 获取最新的几个事件
        recent_events = sorted(events, key=lambda e: e.timestamp, reverse=True)[:limit]

        sample_event = recent_events[0]

        return {
            "error_hash": error_hash,
            "error_type": sample_event.error_type,
            "error_message": sample_event.error_message,
            "severity": sample_event.severity,
            "module": sample_event.module,
            "function": sample_event.function,
            "total_occurrences": len(events),
            "first_seen": min(e.timestamp for e in events).isoformat(),
            "last_seen": max(e.timestamp for e in events).isoformat(),
            "stack_trace": sample_event.stack_trace,
            "recent_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "context": e.context,
                }
                for e in recent_events
            ]
        }

    def mark_resolved(
        self,
        error_hash: str,
        resolved: bool = True
    ) -> None:
        """
        标记错误为已解决

        Args:
            error_hash: 错误哈希值
            resolved: 是否已解决
        """
        # 更新内存中的记录
        for event in self._error_groups.get(error_hash, []):
            event.resolved = resolved
            event.resolved_at = datetime.now() if resolved else None

        # 更新数据库
        if self._use_database:
            try:
                update_sql = """
                UPDATE error_events
                SET resolved = %s,
                    resolved_at = %s
                WHERE error_hash = %s
                """

                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(update_sql, (
                            resolved,
                            datetime.now() if resolved else None,
                            error_hash
                        ))
                    conn.commit()
            except Exception as e:
                print(f"Warning: Failed to update resolved status in database: {e}")

    def clear_old_errors(self, days: int = 30) -> int:
        """
        清理旧的错误记录

        Args:
            days: 保留天数

        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=days)

        # 清理内存中的记录
        original_count = len(self._error_events)
        self._error_events = [e for e in self._error_events if e.timestamp >= cutoff]

        # 重建分组
        self._error_groups.clear()
        for event in self._error_events:
            self._error_groups[event.error_hash].append(event)

        cleared_count = original_count - len(self._error_events)

        # 清理数据库
        if self._use_database:
            try:
                delete_sql = """
                DELETE FROM error_events
                WHERE occurred_at < %s
                """

                with self.db.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(delete_sql, (cutoff,))
                    conn.commit()
            except Exception as e:
                print(f"Warning: Failed to clear old errors from database: {e}")

        return cleared_count

    def get_error_summary(self) -> Dict[str, Any]:
        """
        获取错误总览

        Returns:
            错误总览统计
        """
        if not self._error_events:
            return {
                "total_errors": 0,
                "unique_errors": 0,
                "by_severity": {},
                "recent_errors": []
            }

        by_severity = defaultdict(int)
        for event in self._error_events:
            by_severity[event.severity] += 1

        # 最近10个错误
        recent = sorted(self._error_events, key=lambda e: e.timestamp, reverse=True)[:10]

        return {
            "total_errors": len(self._error_events),
            "unique_errors": len(self._error_groups),
            "by_severity": dict(by_severity),
            "recent_errors": [
                {
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                    "severity": e.severity,
                    "timestamp": e.timestamp.isoformat(),
                    "module": e.module,
                }
                for e in recent
            ]
        }
