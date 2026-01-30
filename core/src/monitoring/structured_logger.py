"""
结构化日志系统

提供JSON格式日志、日志聚合和查询功能。
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path
import traceback
from collections import defaultdict

from loguru import logger


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(
        self,
        log_dir: Path,
        service_name: str = "stock-analysis",
        enable_json_logs: bool = True,
        enable_console: bool = True
    ):
        """
        初始化结构化日志记录器

        Args:
            log_dir: 日志目录
            service_name: 服务名称
            enable_json_logs: 是否启用JSON格式日志
            enable_console: 是否启用控制台输出
        """
        self.log_dir = Path(log_dir)
        self.service_name = service_name
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 移除默认的控制台输出
        logger.remove()

        # 设置日志记录器
        if enable_console:
            self._setup_console_logger()

        if enable_json_logs:
            self._setup_file_loggers()

    def _setup_console_logger(self) -> None:
        """设置控制台日志"""
        logger.add(
            sink=lambda msg: print(msg, end=""),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO",
            colorize=True
        )

    def _setup_file_loggers(self) -> None:
        """设置文件日志记录器"""
        # JSON格式应用日志
        logger.add(
            self.log_dir / "app_{time:YYYY-MM-DD}.json",
            serialize=True,  # 使用serialize而不是自定义format
            rotation="00:00",
            retention="30 days",
            compression="zip",
            level="INFO",
            encoding="utf-8"
        )

        # 错误日志单独存储
        logger.add(
            self.log_dir / "errors_{time:YYYY-MM-DD}.json",
            serialize=True,
            rotation="00:00",
            retention="90 days",
            compression="zip",
            level="ERROR",
            encoding="utf-8"
        )

        # 性能日志
        logger.add(
            self.log_dir / "performance_{time:YYYY-MM-DD}.json",
            serialize=True,
            rotation="00:00",
            retention="7 days",
            compression="zip",
            filter=lambda record: "performance" in record["extra"],
            encoding="utf-8"
        )

    def _json_formatter(self, record: Dict[str, Any]) -> str:
        """
        JSON格式化器

        Args:
            record: 日志记录

        Returns:
            JSON格式字符串
        """
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "service": self.service_name,
                "level": record["level"].name,
                "message": record["message"],
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
            }

            # 添加额外字段
            if record["extra"]:
                log_entry["extra"] = record["extra"]

            # 添加异常信息
            if record["exception"]:
                exc_type, exc_value, exc_tb = record["exception"]
                log_entry["exception"] = {
                    "type": exc_type.__name__ if exc_type else "Unknown",
                    "value": str(exc_value) if exc_value else "",
                    "traceback": "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                }

            return json.dumps(log_entry, ensure_ascii=False) + "\n"
        except Exception:
            # 如果格式化失败，返回简单格式
            return json.dumps({"message": str(record.get("message", ""))}) + "\n"

    def log_operation(
        self,
        operation: str,
        level: str = "INFO",
        **context
    ) -> None:
        """
        记录操作日志

        Args:
            operation: 操作名称
            level: 日志级别
            **context: 上下文信息
        """
        logger.bind(**context).log(level, f"Operation: {operation}")

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        **metrics
    ) -> None:
        """
        记录性能日志

        Args:
            operation: 操作名称
            duration_ms: 持续时间(毫秒)
            **metrics: 性能指标
        """
        logger.bind(
            performance=True,
            operation=operation,
            duration_ms=duration_ms,
            **metrics
        ).info(f"Performance: {operation} completed in {duration_ms:.2f}ms")

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        记录错误日志

        Args:
            error: 异常对象
            context: 上下文信息
        """
        logger.bind(**(context or {})).exception(
            f"Error occurred: {type(error).__name__}"
        )

    def log_data_quality(
        self,
        dataset: str,
        quality_metrics: Dict[str, Any]
    ) -> None:
        """
        记录数据质量日志

        Args:
            dataset: 数据集名称
            quality_metrics: 质量指标
        """
        logger.bind(
            data_quality=True,
            dataset=dataset,
            **quality_metrics
        ).info(f"Data quality check for {dataset}")

    def log_model_training(
        self,
        model_name: str,
        metrics: Dict[str, float],
        **context
    ) -> None:
        """
        记录模型训练日志

        Args:
            model_name: 模型名称
            metrics: 训练指标
            **context: 上下文信息
        """
        logger.bind(
            model_training=True,
            model_name=model_name,
            metrics=metrics,
            **context
        ).info(f"Model training: {model_name}")

    def log_backtest(
        self,
        strategy_name: str,
        performance_metrics: Dict[str, float],
        **context
    ) -> None:
        """
        记录回测日志

        Args:
            strategy_name: 策略名称
            performance_metrics: 回测指标
            **context: 上下文信息
        """
        logger.bind(
            backtest=True,
            strategy_name=strategy_name,
            performance=performance_metrics,
            **context
        ).info(f"Backtest completed: {strategy_name}")


class LogQueryEngine:
    """日志查询引擎"""

    def __init__(self, log_dir: Path):
        """
        初始化日志查询引擎

        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)

    def query(
        self,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        module: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询日志

        Args:
            level: 日志级别筛选
            start_time: 开始时间
            end_time: 结束时间
            module: 模块名称筛选
            search_text: 搜索文本
            limit: 返回数量限制

        Returns:
            日志记录列表
        """
        results = []

        # 遍历日志文件
        log_files = sorted(self.log_dir.glob("app_*.json"), reverse=True)

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())

                            # 应用过滤条件
                            if level and entry.get("level") != level:
                                continue

                            if module and entry.get("module") != module:
                                continue

                            if search_text and search_text not in entry.get("message", ""):
                                continue

                            # 时间过滤
                            entry_time_str = entry.get("timestamp", "")
                            if entry_time_str:
                                # 移除末尾的'Z'并解析
                                entry_time = datetime.fromisoformat(entry_time_str.rstrip('Z'))
                                if start_time and entry_time < start_time:
                                    continue
                                if end_time and entry_time > end_time:
                                    continue

                            results.append(entry)

                            if len(results) >= limit:
                                return results

                        except (json.JSONDecodeError, ValueError):
                            continue

            except FileNotFoundError:
                continue

        return results

    def aggregate_errors(
        self,
        window_hours: int = 24
    ) -> Dict[str, int]:
        """
        聚合错误统计

        Args:
            window_hours: 时间窗口(小时)

        Returns:
            错误类型计数字典
        """
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        error_counts = defaultdict(int)

        error_files = sorted(self.log_dir.glob("errors_*.json"), reverse=True)

        for log_file in error_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time_str = entry.get("timestamp", "")

                            if entry_time_str:
                                entry_time = datetime.fromisoformat(entry_time_str.rstrip('Z'))

                                if entry_time >= cutoff:
                                    if "exception" in entry:
                                        error_type = entry["exception"]["type"]
                                        error_counts[error_type] += 1

                        except (json.JSONDecodeError, ValueError):
                            continue

            except FileNotFoundError:
                continue

        return dict(error_counts)

    def get_performance_summary(
        self,
        operation: Optional[str] = None,
        window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        获取性能摘要

        Args:
            operation: 操作名称筛选
            window_hours: 时间窗口(小时)

        Returns:
            性能摘要统计
        """
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        performance_data = []

        perf_files = sorted(self.log_dir.glob("performance_*.json"), reverse=True)

        for log_file in perf_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())
                            entry_time_str = entry.get("timestamp", "")

                            if entry_time_str:
                                entry_time = datetime.fromisoformat(entry_time_str.rstrip('Z'))

                                if entry_time >= cutoff:
                                    extra = entry.get("extra", {})
                                    if operation is None or extra.get("operation") == operation:
                                        duration = extra.get("duration_ms")
                                        if duration is not None:
                                            performance_data.append({
                                                "operation": extra.get("operation"),
                                                "duration_ms": duration,
                                                "timestamp": entry_time_str
                                            })

                        except (json.JSONDecodeError, ValueError):
                            continue

            except FileNotFoundError:
                continue

        if not performance_data:
            return {}

        durations = [p["duration_ms"] for p in performance_data]

        return {
            "count": len(durations),
            "min_ms": min(durations),
            "max_ms": max(durations),
            "mean_ms": sum(durations) / len(durations),
            "operations": performance_data
        }

    def search_logs(
        self,
        pattern: str,
        log_type: str = "app",
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        搜索日志内容

        Args:
            pattern: 搜索模式
            log_type: 日志类型 (app, errors, performance)
            max_results: 最大结果数

        Returns:
            匹配的日志记录列表
        """
        results = []
        log_pattern = f"{log_type}_*.json"
        log_files = sorted(self.log_dir.glob(log_pattern), reverse=True)

        for log_file in log_files:
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line.strip())

                            # 在消息和额外字段中搜索
                            message = entry.get("message", "")
                            extra = json.dumps(entry.get("extra", {}))

                            if pattern.lower() in message.lower() or pattern.lower() in extra.lower():
                                results.append(entry)

                                if len(results) >= max_results:
                                    return results

                        except (json.JSONDecodeError, ValueError):
                            continue

            except FileNotFoundError:
                continue

        return results
