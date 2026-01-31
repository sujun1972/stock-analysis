"""
配置诊断工具

提供配置优化建议和问题诊断功能。
"""

import multiprocessing
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning("psutil 未安装，部分诊断功能不可用")


console = Console()


@dataclass
class Suggestion:
    """优化建议"""
    category: str
    message: str
    suggestion: str
    priority: str = "medium"  # low, medium, high


@dataclass
class Conflict:
    """配置冲突"""
    message: str
    conflicting_settings: List[str]
    resolution: str


@dataclass
class HealthReport:
    """健康检查报告"""
    overall_health: str  # good, warning, critical
    system_info: Dict[str, Any]
    resource_status: Dict[str, Any]
    dependencies_status: Dict[str, bool]
    config_consistency: Dict[str, bool]


class ConfigDiagnostics:
    """配置诊断工具"""

    def __init__(self, settings=None):
        """
        初始化诊断工具

        Args:
            settings: 配置对象，如果为None则自动加载
        """
        if settings is None:
            from . import get_settings
            self.settings = get_settings()
        else:
            self.settings = settings

    def run_health_check(self) -> HealthReport:
        """运行健康检查"""
        logger.info("开始健康检查...")

        # 1. 系统信息
        system_info = self._get_system_info()

        # 2. 资源状态
        resource_status = self._check_resources()

        # 3. 依赖检查
        dependencies_status = self._check_dependencies()

        # 4. 配置一致性
        config_consistency = self._check_config_consistency()

        # 确定整体健康状况
        overall_health = self._determine_overall_health(
            resource_status, dependencies_status, config_consistency
        )

        report = HealthReport(
            overall_health=overall_health,
            system_info=system_info,
            resource_status=resource_status,
            dependencies_status=dependencies_status,
            config_consistency=config_consistency,
        )

        logger.info(f"健康检查完成: {overall_health}")
        return report

    def suggest_optimizations(self) -> List[Suggestion]:
        """建议配置优化"""
        suggestions = []

        # 1. 基于硬件的优化建议
        cpu_count = multiprocessing.cpu_count()

        if HAS_PSUTIL:
            memory_gb = psutil.virtual_memory().total / (1024 ** 3)

            if cpu_count >= 8:
                suggestions.append(Suggestion(
                    category="performance",
                    message=f"检测到 {cpu_count} 核 CPU",
                    suggestion=f"建议设置 n_workers={cpu_count - 1} 以充分利用多核性能",
                    priority="high"
                ))

            if memory_gb >= 16:
                suggestions.append(Suggestion(
                    category="performance",
                    message=f"检测到 {memory_gb:.1f} GB 内存",
                    suggestion="建议启用特征缓存以提升性能",
                    priority="medium"
                ))

            if memory_gb < 8:
                suggestions.append(Suggestion(
                    category="performance",
                    message=f"可用内存较少: {memory_gb:.1f} GB",
                    suggestion="建议启用流式处理并减少批处理大小",
                    priority="high"
                ))

        # 2. 基于数据规模的优化建议
        data_dir = Path(self.settings.paths.data_dir)
        if data_dir.exists():
            try:
                # 估算数据规模
                total_size = sum(f.stat().st_size for f in data_dir.rglob('*') if f.is_file())
                total_size_gb = total_size / (1024 ** 3)

                if total_size_gb > 10:
                    suggestions.append(Suggestion(
                        category="storage",
                        message=f"数据目录较大: {total_size_gb:.1f} GB",
                        suggestion="建议定期清理旧数据或启用数据压缩",
                        priority="medium"
                    ))
            except Exception as e:
                logger.debug(f"估算数据规模时出错: {e}")

        # 3. 基于使用场景的优化建议
        if self.settings.data_source.provider == "akshare":
            suggestions.append(Suggestion(
                category="data_source",
                message="当前使用 AkShare 数据源",
                suggestion="如需更全面的数据，建议升级到 Tushare（需注册获取 Token）",
                priority="low"
            ))

        if self.settings.ml.cache_features:
            cache_dir = Path(self.settings.paths.cache_dir)
            if cache_dir.exists():
                try:
                    cache_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
                    cache_size_gb = cache_size / (1024 ** 3)

                    if cache_size_gb > 5:
                        suggestions.append(Suggestion(
                            category="storage",
                            message=f"特征缓存较大: {cache_size_gb:.1f} GB",
                            suggestion="建议定期清理缓存或调整缓存策略",
                            priority="low"
                        ))
                except Exception as e:
                    logger.debug(f"检查缓存大小时出错: {e}")

        # 4. 安全建议
        if self.settings.database.password in ["stock_password_123", "password"]:
            suggestions.append(Suggestion(
                category="security",
                message="使用默认密码",
                suggestion="强烈建议修改为强密码（8位以上，包含大小写字母、数字、特殊字符）",
                priority="high"
            ))

        return suggestions

    def detect_conflicts(self) -> List[Conflict]:
        """检测配置冲突"""
        conflicts = []

        # 1. GPU 配置冲突检测
        if hasattr(self.settings, 'performance'):
            perf = self.settings.performance
            if hasattr(perf, 'gpu') and hasattr(perf.gpu, 'enable_gpu'):
                if perf.gpu.enable_gpu:
                    # 检查是否有 GPU 可用
                    gpu_available = self._check_gpu_available()
                    if not gpu_available:
                        conflicts.append(Conflict(
                            message="GPU 已启用但系统中未检测到可用 GPU",
                            conflicting_settings=["performance.gpu.enable_gpu"],
                            resolution="设置 enable_gpu=false 或安装 CUDA/ROCm 驱动"
                        ))

        # 2. 并行后端与环境冲突
        if hasattr(self.settings, 'performance'):
            perf = self.settings.performance
            if hasattr(perf, 'parallel') and hasattr(perf.parallel, 'backend'):
                backend = perf.parallel.backend
                if backend == "ray":
                    try:
                        import ray
                    except ImportError:
                        conflicts.append(Conflict(
                            message="配置使用 Ray 后端但 Ray 未安装",
                            conflicting_settings=["performance.parallel.backend"],
                            resolution="安装 Ray: pip install ray 或使用其他后端"
                        ))

        # 3. 数据源与依赖冲突
        provider = self.settings.data_source.provider
        if provider == "akshare":
            try:
                import akshare
            except ImportError:
                conflicts.append(Conflict(
                    message="配置使用 AkShare 但 AkShare 未安装",
                    conflicting_settings=["data_source.provider"],
                    resolution="安装 AkShare: pip install akshare"
                ))

        if provider == "tushare":
            try:
                import tushare
            except ImportError:
                conflicts.append(Conflict(
                    message="配置使用 Tushare 但 Tushare 未安装",
                    conflicting_settings=["data_source.provider"],
                    resolution="安装 Tushare: pip install tushare"
                ))

        return conflicts

    def generate_report(self, format: str = "console") -> str:
        """
        生成诊断报告

        Args:
            format: 输出格式 (console, markdown, html)

        Returns:
            格式化的报告字符串
        """
        health = self.run_health_check()
        suggestions = self.suggest_optimizations()
        conflicts = self.detect_conflicts()

        if format == "console":
            return self._format_console_report(health, suggestions, conflicts)
        elif format == "markdown":
            return self._format_markdown_report(health, suggestions, conflicts)
        elif format == "html":
            return self._format_html_report(health, suggestions, conflicts)
        else:
            raise ValueError(f"不支持的格式: {format}")

    # ==================== 私有方法 ====================

    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        import platform

        info = {
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
        }

        if HAS_PSUTIL:
            info.update({
                "cpu_count": psutil.cpu_count(logical=True),
                "cpu_count_physical": psutil.cpu_count(logical=False),
                "total_memory_gb": round(psutil.virtual_memory().total / (1024 ** 3), 2),
            })
        else:
            info["cpu_count"] = multiprocessing.cpu_count()

        return info

    def _check_resources(self) -> Dict[str, Any]:
        """检查系统资源"""
        status = {}

        if HAS_PSUTIL:
            # CPU 使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            status["cpu_usage_percent"] = cpu_percent
            status["cpu_status"] = "good" if cpu_percent < 70 else "warning" if cpu_percent < 90 else "critical"

            # 内存使用率
            mem = psutil.virtual_memory()
            status["memory_usage_percent"] = mem.percent
            status["memory_available_gb"] = round(mem.available / (1024 ** 3), 2)
            status["memory_status"] = "good" if mem.percent < 70 else "warning" if mem.percent < 90 else "critical"

            # 磁盘使用率
            disk = psutil.disk_usage('/')
            status["disk_usage_percent"] = disk.percent
            status["disk_free_gb"] = round(disk.free / (1024 ** 3), 2)
            status["disk_status"] = "good" if disk.percent < 80 else "warning" if disk.percent < 95 else "critical"
        else:
            status["note"] = "psutil 未安装，无法获取详细资源信息"

        return status

    def _check_dependencies(self) -> Dict[str, bool]:
        """检查依赖包"""
        dependencies = {}

        # 核心依赖
        for package in ["pandas", "numpy", "psycopg2", "sqlalchemy", "loguru", "rich"]:
            try:
                __import__(package)
                dependencies[package] = True
            except ImportError:
                dependencies[package] = False

        # 数据源依赖
        for package in ["akshare", "tushare"]:
            try:
                __import__(package)
                dependencies[package] = True
            except ImportError:
                dependencies[package] = False

        # ML 依赖
        for package in ["scikit-learn", "xgboost", "lightgbm"]:
            try:
                __import__(package.replace("-", "_"))
                dependencies[package] = True
            except ImportError:
                dependencies[package] = False

        return dependencies

    def _check_config_consistency(self) -> Dict[str, bool]:
        """检查配置一致性"""
        consistency = {}

        # 检查路径配置
        consistency["paths_configured"] = all([
            self.settings.paths.data_dir,
            self.settings.paths.models_dir,
            self.settings.paths.cache_dir,
            self.settings.paths.results_dir,
        ])

        # 检查数据库配置
        consistency["database_configured"] = all([
            self.settings.database.host,
            self.settings.database.database,
            self.settings.database.user,
        ])

        # 检查数据源配置
        consistency["data_source_configured"] = bool(self.settings.data_source.provider)

        return consistency

    def _determine_overall_health(
        self,
        resource_status: Dict[str, Any],
        dependencies_status: Dict[str, bool],
        config_consistency: Dict[str, bool]
    ) -> str:
        """确定整体健康状况"""
        # 检查资源状态
        if HAS_PSUTIL:
            if any(resource_status.get(f"{r}_status") == "critical" for r in ["cpu", "memory", "disk"]):
                return "critical"
            if any(resource_status.get(f"{r}_status") == "warning" for r in ["cpu", "memory", "disk"]):
                return "warning"

        # 检查核心依赖
        core_deps = ["pandas", "numpy", "psycopg2", "sqlalchemy", "loguru", "rich"]
        if not all(dependencies_status.get(dep, False) for dep in core_deps):
            return "critical"

        # 检查配置一致性
        if not all(config_consistency.values()):
            return "warning"

        return "good"

    def _check_gpu_available(self) -> bool:
        """检查 GPU 是否可用"""
        # 尝试检测 CUDA
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            pass

        # 尝试检测 Apple MPS
        try:
            import torch
            return torch.backends.mps.is_available()
        except (ImportError, AttributeError):
            pass

        return False

    def _format_console_report(
        self,
        health: HealthReport,
        suggestions: List[Suggestion],
        conflicts: List[Conflict]
    ) -> None:
        """格式化控制台报告"""
        # 健康状况
        health_colors = {
            "good": "green",
            "warning": "yellow",
            "critical": "red",
        }
        health_color = health_colors.get(health.overall_health, "white")

        console.print(Panel(
            f"[bold {health_color}]整体健康状况: {health.overall_health.upper()}[/bold {health_color}]",
            title="诊断报告",
            border_style=health_color
        ))

        # 系统信息
        console.print("\n[bold cyan]系统信息:[/bold cyan]")
        table = Table(show_header=False, box=None)
        for key, value in health.system_info.items():
            table.add_row(f"  {key}", str(value))
        console.print(table)

        # 资源状态
        if health.resource_status:
            console.print("\n[bold cyan]资源状态:[/bold cyan]")
            resource_table = Table(show_header=False, box=None)
            for key, value in health.resource_status.items():
                if "status" not in key:
                    resource_table.add_row(f"  {key}", str(value))
            console.print(resource_table)

        # 优化建议
        if suggestions:
            console.print("\n[bold yellow]优化建议:[/bold yellow]")
            for i, sug in enumerate(suggestions, 1):
                priority_colors = {"high": "red", "medium": "yellow", "low": "blue"}
                color = priority_colors.get(sug.priority, "white")
                console.print(f"  [{color}]{i}. {sug.message}[/{color}]")
                console.print(f"     建议: {sug.suggestion}")

        # 配置冲突
        if conflicts:
            console.print("\n[bold red]配置冲突:[/bold red]")
            for i, conflict in enumerate(conflicts, 1):
                console.print(f"  {i}. {conflict.message}")
                console.print(f"     解决方案: {conflict.resolution}")

        if not suggestions and not conflicts:
            console.print("\n[green]✓ 未发现需要优化的地方。[/green]")

    def _format_markdown_report(
        self,
        health: HealthReport,
        suggestions: List[Suggestion],
        conflicts: List[Conflict]
    ) -> str:
        """格式化 Markdown 报告"""
        lines = [
            "# 配置诊断报告",
            "",
            f"**整体健康状况**: {health.overall_health.upper()}",
            "",
            "## 系统信息",
            "",
        ]

        for key, value in health.system_info.items():
            lines.append(f"- **{key}**: {value}")

        if health.resource_status:
            lines.extend(["", "## 资源状态", ""])
            for key, value in health.resource_status.items():
                if "status" not in key:
                    lines.append(f"- **{key}**: {value}")

        if suggestions:
            lines.extend(["", "## 优化建议", ""])
            for i, sug in enumerate(suggestions, 1):
                lines.append(f"{i}. **{sug.message}** (优先级: {sug.priority})")
                lines.append(f"   - 建议: {sug.suggestion}")

        if conflicts:
            lines.extend(["", "## 配置冲突", ""])
            for i, conflict in enumerate(conflicts, 1):
                lines.append(f"{i}. {conflict.message}")
                lines.append(f"   - 解决方案: {conflict.resolution}")

        return "\n".join(lines)

    def _format_html_report(
        self,
        health: HealthReport,
        suggestions: List[Suggestion],
        conflicts: List[Conflict]
    ) -> str:
        """格式化 HTML 报告"""
        # 简化实现
        return f"<html><body><h1>诊断报告</h1><p>健康状况: {health.overall_health}</p></body></html>"
