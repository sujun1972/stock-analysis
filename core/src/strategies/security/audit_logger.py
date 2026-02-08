"""
审计日志记录器

记录所有策略加载和执行的详细信息
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from loguru import logger


class AuditLogger:
    """
    审计日志记录器

    记录所有策略加载和执行的详细信息
    """

    def __init__(self, log_dir: str = "logs/audit"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 配置专门的审计日志
        self.audit_file = self.log_dir / f"audit_{datetime.now():%Y%m%d}.jsonl"

        logger.info(f"审计日志已初始化: {self.audit_file}")

    def log_strategy_load(
        self,
        strategy_id: int,
        strategy_type: str,
        strategy_class: str,
        code_hash: str,
        validation_result: Dict[str, Any],
        user: Optional[str] = None
    ):
        """
        记录策略加载事件

        Args:
            strategy_id: 策略ID
            strategy_type: 策略类型 ('predefined' | 'configured' | 'dynamic')
            strategy_class: 策略类名
            code_hash: 代码哈希值
            validation_result: 验证结果
            user: 用户标识
        """
        event = {
            'event_type': 'strategy_load',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'strategy_type': strategy_type,
            'strategy_class': strategy_class,
            'code_hash': code_hash,
            'validation': validation_result,
            'user': user,
        }

        self._write_event(event)
        logger.info(f"审计: 策略加载 - ID={strategy_id}, 类型={strategy_type}")

    def log_strategy_execution(
        self,
        strategy_id: int,
        execution_type: str,
        execution_params: Dict[str, Any],
        execution_result: Dict[str, Any],
        duration_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """
        记录策略执行事件

        Args:
            strategy_id: 策略ID
            execution_type: 执行类型 ('backtest' | 'live' | 'test')
            execution_params: 执行参数
            execution_result: 执行结果
            duration_ms: 执行耗时(毫秒)
            success: 是否成功
            error: 错误信息
        """
        event = {
            'event_type': 'strategy_execution',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'execution_type': execution_type,
            'params': execution_params,
            'result': execution_result,
            'duration_ms': duration_ms,
            'success': success,
            'error': error,
        }

        self._write_event(event)
        logger.info(f"审计: 策略执行 - ID={strategy_id}, 成功={success}")

    def log_security_violation(
        self,
        strategy_id: int,
        violation_type: str,
        details: Dict[str, Any]
    ):
        """
        记录安全违规事件

        Args:
            strategy_id: 策略ID
            violation_type: 违规类型
            details: 详细信息
        """
        event = {
            'event_type': 'security_violation',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'violation_type': violation_type,
            'details': details,
            'severity': 'high',  # 所有安全违规都是高严重度
        }

        self._write_event(event)
        logger.warning(f"审计: 安全违规 - ID={strategy_id}, 类型={violation_type}")

    def log_cache_event(
        self,
        event_type: str,
        strategy_id: int,
        cache_key: str,
        hit: Optional[bool] = None
    ):
        """
        记录缓存事件

        Args:
            event_type: 事件类型 ('hit' | 'miss' | 'invalidate')
            strategy_id: 策略ID
            cache_key: 缓存键
            hit: 是否命中
        """
        event = {
            'event_type': f'cache_{event_type}',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'cache_key': cache_key,
            'hit': hit,
        }

        self._write_event(event)
        logger.debug(f"审计: 缓存{event_type} - ID={strategy_id}")

    def log_resource_usage(
        self,
        strategy_id: int,
        resource_type: str,
        usage: Dict[str, Any]
    ):
        """
        记录资源使用情况

        Args:
            strategy_id: 策略ID
            resource_type: 资源类型 ('memory' | 'cpu' | 'time')
            usage: 使用情况
        """
        event = {
            'event_type': 'resource_usage',
            'timestamp': datetime.now().isoformat(),
            'strategy_id': strategy_id,
            'resource_type': resource_type,
            'usage': usage,
        }

        self._write_event(event)
        logger.debug(f"审计: 资源使用 - ID={strategy_id}, 类型={resource_type}")

    def query_events(
        self,
        event_type: Optional[str] = None,
        strategy_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list:
        """
        查询审计日志

        Args:
            event_type: 事件类型过滤
            strategy_id: 策略ID过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 最大返回数量

        Returns:
            事件列表
        """
        events = []

        try:
            with open(self.audit_file, 'r') as f:
                for line in f:
                    if len(events) >= limit:
                        break

                    try:
                        event = json.loads(line.strip())

                        # 应用过滤器
                        if event_type and event.get('event_type') != event_type:
                            continue

                        if strategy_id and event.get('strategy_id') != strategy_id:
                            continue

                        if start_time:
                            event_time = datetime.fromisoformat(event['timestamp'])
                            if event_time < start_time:
                                continue

                        if end_time:
                            event_time = datetime.fromisoformat(event['timestamp'])
                            if event_time > end_time:
                                continue

                        events.append(event)

                    except json.JSONDecodeError as e:
                        logger.warning(f"解析日志行失败: {e}")
                        continue

        except FileNotFoundError:
            logger.warning(f"审计日志文件不存在: {self.audit_file}")

        return events

    def get_statistics(
        self,
        strategy_id: Optional[int] = None,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取审计统计信息

        Args:
            strategy_id: 策略ID (可选)
            time_range_hours: 时间范围(小时)

        Returns:
            统计信息
        """
        from datetime import timedelta

        start_time = datetime.now() - timedelta(hours=time_range_hours)
        events = self.query_events(
            strategy_id=strategy_id,
            start_time=start_time,
            limit=10000
        )

        # 统计各类事件
        stats = {
            'total_events': len(events),
            'strategy_loads': 0,
            'strategy_executions': 0,
            'security_violations': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0,
            'time_range_hours': time_range_hours,
        }

        for event in events:
            event_type = event.get('event_type')

            if event_type == 'strategy_load':
                stats['strategy_loads'] += 1
            elif event_type == 'strategy_execution':
                stats['strategy_executions'] += 1
                if not event.get('success'):
                    stats['errors'] += 1
            elif event_type == 'security_violation':
                stats['security_violations'] += 1
            elif event_type == 'cache_hit':
                stats['cache_hits'] += 1
            elif event_type == 'cache_miss':
                stats['cache_misses'] += 1

        return stats

    def _write_event(self, event: Dict[str, Any]):
        """写入事件到日志文件"""
        try:
            with open(self.audit_file, 'a') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"写入审计日志失败: {e}")
