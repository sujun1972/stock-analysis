"""
配置验证器框架

提供全面的配置验证能力，检测配置错误和潜在问题。
"""

import json
import os
import shutil
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


class SeverityLevel(str, Enum):
    """问题严重程度"""
    INFO = "info"          # 信息提示
    WARNING = "warning"    # 警告(不影响运行)
    ERROR = "error"        # 错误(可能影响运行)
    CRITICAL = "critical"  # 严重错误(无法运行)


class Category(str, Enum):
    """问题分类"""
    DATABASE = "database"
    PATHS = "paths"
    DATA_SOURCE = "data_source"
    ML_CONFIG = "ml_config"
    PERFORMANCE = "performance"
    SECURITY = "security"


@dataclass
class ValidationIssue:
    """验证问题"""
    severity: SeverityLevel
    category: Category
    code: str  # 错误代码，如 "DB001"
    message: str
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    fix_command: Optional[str] = None  # 修复命令

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "suggestion": self.suggestion,
            "auto_fixable": self.auto_fixable,
            "fix_command": self.fix_command,
        }


@dataclass
class ValidationReport:
    """验证报告"""
    passed: bool
    total_issues: int
    issues_by_severity: Dict[str, int]
    issues: List[ValidationIssue] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转为字典"""
        return {
            "passed": self.passed,
            "total_issues": self.total_issues,
            "issues_by_severity": self.issues_by_severity,
            "issues": [issue.to_dict() for issue in self.issues],
            "timestamp": self.timestamp,
        }

    def to_json(self, indent: int = 2) -> str:
        """转为 JSON"""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def to_html(self) -> str:
        """生成 HTML 报告"""
        status = "通过" if self.passed else "失败"
        status_class = "passed" if self.passed else "failed"

        # 生成问题列表 HTML
        issues_html = ""
        for issue in self.issues:
            severity_class = issue.severity.value
            issues_html += f"""
            <div class="issue {severity_class}">
                <h3>[{issue.code}] {issue.message}</h3>
                <p><strong>分类:</strong> {issue.category.value}</p>
                <p><strong>严重程度:</strong> {issue.severity.value}</p>
                {f'<p><strong>建议:</strong> {issue.suggestion}</p>' if issue.suggestion else ''}
                {f'<p><strong>修复命令:</strong> <code>{issue.fix_command}</code></p>' if issue.fix_command else ''}
                {f'<p><strong>可自动修复:</strong> 是</p>' if issue.auto_fixable else ''}
            </div>
            """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>配置验证报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .header {{
            background: #2c3e50;
            color: white;
            padding: 30px;
        }}
        .header h1 {{
            margin: 0 0 10px 0;
        }}
        .summary {{
            padding: 30px;
            background: #ecf0f1;
            border-bottom: 1px solid #bdc3c7;
        }}
        .summary h2 {{
            margin-top: 0;
        }}
        .summary ul {{
            list-style: none;
            padding: 0;
        }}
        .summary li {{
            padding: 5px 0;
        }}
        .issue {{
            border-left: 4px solid;
            padding: 20px;
            margin: 20px 30px;
            background: #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .issue h3 {{
            margin-top: 0;
        }}
        .issue code {{
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
        }}
        .critical {{
            border-color: #e74c3c;
            background: #ffe6e6 !important;
        }}
        .error {{
            border-color: #e67e22;
            background: #fff3e6 !important;
        }}
        .warning {{
            border-color: #f39c12;
            background: #fff9e6 !important;
        }}
        .info {{
            border-color: #3498db;
            background: #e6f3ff !important;
        }}
        .passed {{
            color: #27ae60;
            font-weight: bold;
        }}
        .failed {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .issues-section {{
            padding: 30px;
        }}
        .issues-section h2 {{
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>配置验证报告</h1>
            <p>生成时间: {self.timestamp}</p>
        </div>

        <div class="summary">
            <h2>摘要</h2>
            <p>状态: <span class="{status_class}">{status}</span></p>
            <p>总问题数: {self.total_issues}</p>
            <ul>
                <li>严重错误: {self.issues_by_severity.get('critical', 0)}</li>
                <li>错误: {self.issues_by_severity.get('error', 0)}</li>
                <li>警告: {self.issues_by_severity.get('warning', 0)}</li>
                <li>提示: {self.issues_by_severity.get('info', 0)}</li>
            </ul>
        </div>

        <div class="issues-section">
            <h2>问题详情</h2>
            {issues_html if issues_html else '<p>未发现任何问题。</p>'}
        </div>
    </div>
</body>
</html>
"""
        return html

    def to_console(self) -> None:
        """输出到控制台（使用 Rich）"""
        # 显示摘要
        status = "[green]✓ 通过[/green]" if self.passed else "[red]✗ 失败[/red]"
        summary_text = f"""
[bold cyan]验证状态:[/bold cyan] {status}
[bold cyan]总问题数:[/bold cyan] {self.total_issues}
[bold cyan]生成时间:[/bold cyan] {self.timestamp}

[bold yellow]问题统计:[/bold yellow]
  • 严重错误: [red]{self.issues_by_severity.get('critical', 0)}[/red]
  • 错误: [yellow]{self.issues_by_severity.get('error', 0)}[/yellow]
  • 警告: [blue]{self.issues_by_severity.get('warning', 0)}[/blue]
  • 提示: [dim]{self.issues_by_severity.get('info', 0)}[/dim]
        """
        console.print(Panel(summary_text.strip(), title="配置验证报告", border_style="cyan"))

        # 显示问题详情
        if self.issues:
            console.print("\n[bold]问题详情:[/bold]\n")
            for i, issue in enumerate(self.issues, 1):
                # 根据严重程度选择颜色
                severity_colors = {
                    SeverityLevel.CRITICAL: "red",
                    SeverityLevel.ERROR: "yellow",
                    SeverityLevel.WARNING: "blue",
                    SeverityLevel.INFO: "dim",
                }
                color = severity_colors.get(issue.severity, "white")

                console.print(f"[{color}]{i}. [{issue.code}] {issue.message}[/{color}]")
                console.print(f"   分类: {issue.category.value}")
                console.print(f"   严重程度: {issue.severity.value}")
                if issue.suggestion:
                    console.print(f"   [cyan]建议:[/cyan] {issue.suggestion}")
                if issue.fix_command:
                    console.print(f"   [green]修复命令:[/green] {issue.fix_command}")
                if issue.auto_fixable:
                    console.print(f"   [green]可自动修复[/green]")
                console.print()
        else:
            console.print("\n[green]✓ 未发现任何问题。[/green]\n")


class ConfigValidator:
    """配置验证器"""

    def __init__(self, settings=None):
        """
        初始化验证器

        Args:
            settings: 配置对象，如果为None则自动加载
        """
        if settings is None:
            from . import get_settings
            self.settings = get_settings()
        else:
            self.settings = settings
        self.issues: List[ValidationIssue] = []

    def validate_all(self) -> ValidationReport:
        """验证所有配置项"""
        self.issues.clear()

        # 执行各项验证
        logger.info("开始配置验证...")
        self.validate_database()
        self.validate_paths()
        self.validate_data_sources()
        self.validate_ml_config()
        self.validate_performance()
        self.validate_security()

        # 生成报告
        report = self._generate_report()
        logger.info(f"配置验证完成: {report.total_issues} 个问题")
        return report

    def validate_database(self) -> List[ValidationIssue]:
        """验证数据库配置"""
        issues = []

        # 1. 检查必填字段
        if not self.settings.database.host:
            issues.append(ValidationIssue(
                severity=SeverityLevel.CRITICAL,
                category=Category.DATABASE,
                code="DB001",
                message="数据库主机地址未配置",
                suggestion="请设置环境变量 DATABASE_HOST",
                auto_fixable=False
            ))

        # 2. 测试数据库连接
        try:
            conn = self._test_db_connection()
            if conn:
                conn.close()
                logger.debug("数据库连接测试成功")
        except Exception as e:
            issues.append(ValidationIssue(
                severity=SeverityLevel.ERROR,
                category=Category.DATABASE,
                code="DB002",
                message=f"数据库连接失败: {str(e)}",
                suggestion="检查数据库是否运行，用户名密码是否正确",
                auto_fixable=False
            ))

        # 3. 检查 TimescaleDB 扩展
        try:
            if not self._check_timescaledb_extension():
                issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category=Category.DATABASE,
                    code="DB003",
                    message="TimescaleDB 扩展未安装或无法检测",
                    suggestion="执行: CREATE EXTENSION IF NOT EXISTS timescaledb;",
                    auto_fixable=True,
                    fix_command="stock-cli db init"
                ))
        except Exception as e:
            logger.debug(f"检查 TimescaleDB 扩展时出错: {e}")

        self.issues.extend(issues)
        return issues

    def validate_paths(self) -> List[ValidationIssue]:
        """验证路径配置"""
        issues = []

        paths_to_check = [
            ("数据目录", self.settings.paths.data_dir, "PATH_DATA_DIR"),
            ("模型目录", self.settings.paths.models_dir, "PATH_MODELS_DIR"),
            ("缓存目录", self.settings.paths.cache_dir, "PATH_CACHE_DIR"),
            ("结果目录", self.settings.paths.results_dir, "PATH_RESULTS_DIR"),
        ]

        for name, path_str, env_var in paths_to_check:
            path = Path(path_str)

            # 1. 检查路径存在性
            if not path.exists():
                issues.append(ValidationIssue(
                    severity=SeverityLevel.WARNING,
                    category=Category.PATHS,
                    code="PATH001",
                    message=f"{name}不存在: {path}",
                    suggestion="将自动创建目录",
                    auto_fixable=True,
                    fix_command=f"mkdir -p {path}"
                ))
            else:
                # 2. 检查读权限
                if not os.access(path, os.R_OK):
                    issues.append(ValidationIssue(
                        severity=SeverityLevel.ERROR,
                        category=Category.PATHS,
                        code="PATH002",
                        message=f"{name}无读权限: {path}",
                        suggestion=f"执行: chmod +r {path}",
                        auto_fixable=False
                    ))

                # 3. 检查写权限
                if not os.access(path, os.W_OK):
                    issues.append(ValidationIssue(
                        severity=SeverityLevel.ERROR,
                        category=Category.PATHS,
                        code="PATH003",
                        message=f"{name}无写权限: {path}",
                        suggestion=f"执行: chmod +w {path}",
                        auto_fixable=False
                    ))

                # 4. 检查磁盘空间
                try:
                    stat = shutil.disk_usage(path)
                    free_gb = stat.free / (1024 ** 3)
                    if free_gb < 1:
                        issues.append(ValidationIssue(
                            severity=SeverityLevel.WARNING,
                            category=Category.PATHS,
                            code="PATH004",
                            message=f"{name}磁盘空间不足: {free_gb:.2f} GB",
                            suggestion="建议至少保留 10 GB 可用空间",
                            auto_fixable=False
                        ))
                except Exception as e:
                    logger.debug(f"检查磁盘空间时出错: {e}")

        self.issues.extend(issues)
        return issues

    def validate_data_sources(self) -> List[ValidationIssue]:
        """验证数据源配置"""
        issues = []

        provider = self.settings.data_source.provider

        # 1. 检查数据源有效性
        if provider not in ["akshare", "tushare"]:
            issues.append(ValidationIssue(
                severity=SeverityLevel.ERROR,
                category=Category.DATA_SOURCE,
                code="DS001",
                message=f"无效的数据源: {provider}",
                suggestion="支持的数据源: akshare, tushare",
                auto_fixable=False
            ))

        # 2. 检查 Tushare Token
        if provider == "tushare":
            if not self.settings.data_source.tushare_token:
                issues.append(ValidationIssue(
                    severity=SeverityLevel.ERROR,
                    category=Category.DATA_SOURCE,
                    code="DS002",
                    message="使用 Tushare 但未配置 Token",
                    suggestion="设置环境变量 DATA_TUSHARE_TOKEN",
                    auto_fixable=False
                ))
            else:
                # 测试 Token 有效性
                try:
                    if not self._test_tushare_token():
                        issues.append(ValidationIssue(
                            severity=SeverityLevel.ERROR,
                            category=Category.DATA_SOURCE,
                            code="DS003",
                            message="Tushare Token 无效或已过期",
                            suggestion="检查 Token 是否正确",
                            auto_fixable=False
                        ))
                except Exception as e:
                    logger.debug(f"测试 Tushare Token 时出错: {e}")

        # 3. 测试数据源连接
        try:
            self._test_data_source_connection(provider)
        except Exception as e:
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                category=Category.DATA_SOURCE,
                code="DS004",
                message=f"数据源连接测试失败: {str(e)}",
                suggestion="检查网络连接",
                auto_fixable=False
            ))

        self.issues.extend(issues)
        return issues

    def validate_ml_config(self) -> List[ValidationIssue]:
        """验证机器学习配置"""
        issues = []

        # 1. 检查参数合理性
        if not (1 <= self.settings.ml.default_target_period <= 60):
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                category=Category.ML_CONFIG,
                code="ML001",
                message=f"预测周期不合理: {self.settings.ml.default_target_period}",
                suggestion="建议设置为 1-60 天",
                auto_fixable=False
            ))

        if not (0.5 <= self.settings.ml.default_train_ratio <= 0.9):
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                category=Category.ML_CONFIG,
                code="ML002",
                message=f"训练集比例不合理: {self.settings.ml.default_train_ratio}",
                suggestion="建议设置为 0.5-0.9",
                auto_fixable=False
            ))

        # 2. 检查模型文件
        models_dir = Path(self.settings.paths.models_dir)
        if models_dir.exists():
            model_files = list(models_dir.glob("*.pkl")) + list(models_dir.glob("*.pth"))
            if len(model_files) > 100:
                issues.append(ValidationIssue(
                    severity=SeverityLevel.INFO,
                    category=Category.ML_CONFIG,
                    code="ML004",
                    message=f"模型文件过多: {len(model_files)} 个",
                    suggestion="建议定期清理旧模型文件",
                    auto_fixable=False
                ))

        self.issues.extend(issues)
        return issues

    def validate_performance(self) -> List[ValidationIssue]:
        """验证性能配置"""
        issues = []

        # 检查并行配置（如果存在）
        if hasattr(self.settings, 'performance'):
            perf = self.settings.performance

            # 检查 worker 数量
            try:
                import multiprocessing
                max_workers = multiprocessing.cpu_count()

                if hasattr(perf, 'n_workers') and perf.n_workers > max_workers:
                    issues.append(ValidationIssue(
                        severity=SeverityLevel.WARNING,
                        category=Category.PERFORMANCE,
                        code="PERF001",
                        message=f"worker 数量({perf.n_workers})超过 CPU 核心数({max_workers})",
                        suggestion=f"建议设置为 {max_workers - 1}",
                        auto_fixable=True
                    ))
            except Exception as e:
                logger.debug(f"检查性能配置时出错: {e}")

        self.issues.extend(issues)
        return issues

    def validate_security(self) -> List[ValidationIssue]:
        """验证安全配置"""
        issues = []

        # 1. 检查默认密码
        weak_passwords = ["stock_password_123", "password", "123456", "admin", "root"]
        if self.settings.database.password in weak_passwords:
            issues.append(ValidationIssue(
                severity=SeverityLevel.WARNING,
                category=Category.SECURITY,
                code="SEC001",
                message="使用了默认或弱密码",
                suggestion="建议修改为强密码",
                auto_fixable=False
            ))

        # 2. 检查生产环境配置
        if hasattr(self.settings.app, 'environment'):
            is_production = self.settings.app.environment == "production"

            if is_production and self.settings.app.debug:
                issues.append(ValidationIssue(
                    severity=SeverityLevel.ERROR,
                    category=Category.SECURITY,
                    code="SEC002",
                    message="生产环境不应启用调试模式",
                    suggestion="设置 APP_DEBUG=false",
                    auto_fixable=True,
                    fix_command="export APP_DEBUG=false"
                ))

        self.issues.extend(issues)
        return issues

    def _generate_report(self) -> ValidationReport:
        """生成验证报告"""
        issues_by_severity = {
            "critical": 0,
            "error": 0,
            "warning": 0,
            "info": 0,
        }

        for issue in self.issues:
            issues_by_severity[issue.severity.value] += 1

        passed = (issues_by_severity["critical"] == 0 and
                 issues_by_severity["error"] == 0)

        return ValidationReport(
            passed=passed,
            total_issues=len(self.issues),
            issues_by_severity=issues_by_severity,
            issues=self.issues,
        )

    # ==================== 辅助方法 ====================

    def _test_db_connection(self):
        """测试数据库连接"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.settings.database.host,
                port=self.settings.database.port,
                database=self.settings.database.database,
                user=self.settings.database.user,
                password=self.settings.database.password,
                connect_timeout=5
            )
            return conn
        except ImportError:
            logger.warning("psycopg2 未安装，跳过数据库连接测试")
            return None
        except Exception as e:
            raise Exception(f"连接失败: {e}")

    def _check_timescaledb_extension(self) -> bool:
        """检查 TimescaleDB 扩展"""
        try:
            conn = self._test_db_connection()
            if not conn:
                return False

            cursor = conn.cursor()
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
            )
            result = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return result
        except Exception as e:
            logger.debug(f"检查 TimescaleDB 扩展失败: {e}")
            return False

    def _test_tushare_token(self) -> bool:
        """测试 Tushare Token 有效性"""
        try:
            import tushare as ts
            ts.set_token(self.settings.data_source.tushare_token)
            pro = ts.pro_api()
            # 简单测试：获取交易日历
            df = pro.trade_cal(exchange='SSE', start_date='20240101', end_date='20240110')
            return df is not None and not df.empty
        except ImportError:
            logger.warning("tushare 未安装，跳过 Token 测试")
            return True
        except Exception as e:
            logger.debug(f"Tushare Token 测试失败: {e}")
            return False

    def _test_data_source_connection(self, provider: str) -> None:
        """测试数据源连接"""
        if provider == "akshare":
            try:
                import akshare as ak
                # 简单测试：获取股票列表
                df = ak.stock_zh_a_spot_em()
                if df is None or df.empty:
                    raise Exception("获取数据失败")
            except ImportError:
                raise Exception("akshare 未安装")
            except Exception as e:
                raise Exception(f"AkShare 连接失败: {e}")

        elif provider == "tushare":
            if not self._test_tushare_token():
                raise Exception("Tushare Token 无效")
