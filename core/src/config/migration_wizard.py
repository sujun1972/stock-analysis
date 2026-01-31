#!/usr/bin/env python3
"""
配置迁移向导

帮助用户从旧版本配置迁移到新版本，支持：
- 自动检测配置版本
- 兼容性检查和报告
- 自动迁移和转换
- 备份和回滚
"""

import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class ConfigVersion(str, Enum):
    """配置版本枚举"""
    V1_0 = "v1.0"
    V1_5 = "v1.5"
    V2_0 = "v2.0"
    UNKNOWN = "unknown"


@dataclass
class MigrationIssue:
    """迁移问题"""
    severity: str  # "info", "warning", "error"
    field: str
    message: str
    suggestion: Optional[str] = None


@dataclass
class MigrationReport:
    """迁移报告"""
    from_version: str
    to_version: str
    success: bool
    issues: List[MigrationIssue]
    changes_made: List[str]
    backup_path: Optional[Path] = None
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


# 迁移规则定义
MIGRATION_RULES = {
    "v1.0_to_v1.5": {
        "renames": {
            "DATA_PATH": "PATH_DATA_DIR",
        },
        "removes": [],
        "additions": {
            "ML_CACHE_FEATURES": "true",
        },
        "transforms": {},
    },
    "v1.5_to_v2.0": {
        "renames": {
            "MODELS_PATH": "PATH_MODELS_DIR",
            "CACHE_PATH": "PATH_CACHE_DIR",
            "RESULTS_PATH": "PATH_RESULTS_DIR",
        },
        "removes": [
            "OLD_FEATURE_ENGINE",
        ],
        "additions": {
            "ML_FEATURE_VERSION": "v2.0",
            "APP_ENVIRONMENT": "development",
        },
        "transforms": {
            "DEBUG": lambda v: str(v).lower(),  # True -> "true"
        },
    },
    "v1.0_to_v2.0": {
        # 组合v1.0->v1.5和v1.5->v2.0的规则
        "renames": {
            "DATA_PATH": "PATH_DATA_DIR",
            "MODELS_PATH": "PATH_MODELS_DIR",
            "CACHE_PATH": "PATH_CACHE_DIR",
            "RESULTS_PATH": "PATH_RESULTS_DIR",
        },
        "removes": [
            "OLD_FEATURE_ENGINE",
        ],
        "additions": {
            "ML_CACHE_FEATURES": "true",
            "ML_FEATURE_VERSION": "v2.0",
            "APP_ENVIRONMENT": "development",
        },
        "transforms": {
            "DEBUG": lambda v: str(v).lower(),
        },
    },
}


class ConfigMigrator:
    """配置迁移器"""

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化迁移器

        Args:
            config_path: 配置文件路径，默认为当前目录的 .env
        """
        if config_path is None:
            config_path = Path.cwd() / ".env"
        self.config_path = config_path

    def detect_version(self) -> ConfigVersion:
        """
        检测配置文件版本

        Returns:
            检测到的配置版本
        """
        if not self.config_path.exists():
            return ConfigVersion.UNKNOWN

        config = self._load_env_file()

        # 版本检测规则
        # v2.0: 有 ML_FEATURE_VERSION 或 APP_ENVIRONMENT
        if "ML_FEATURE_VERSION" in config or "APP_ENVIRONMENT" in config:
            return ConfigVersion.V2_0

        # v1.5: 有 ML_CACHE_FEATURES 且有 PATH_DATA_DIR
        if "ML_CACHE_FEATURES" in config or "PATH_DATA_DIR" in config:
            return ConfigVersion.V1_5

        # v1.0: 有 DATA_PATH 或 MODELS_PATH
        if "DATA_PATH" in config or "MODELS_PATH" in config:
            return ConfigVersion.V1_0

        # 如果有任何DATABASE_*配置，认为是v1.0
        if any(k.startswith("DATABASE_") for k in config.keys()):
            return ConfigVersion.V1_0

        return ConfigVersion.UNKNOWN

    def check_compatibility(
        self, from_version: ConfigVersion, to_version: ConfigVersion
    ) -> List[MigrationIssue]:
        """
        检查版本兼容性

        Args:
            from_version: 源版本
            to_version: 目标版本

        Returns:
            兼容性问题列表
        """
        issues = []

        if from_version == ConfigVersion.UNKNOWN:
            issues.append(MigrationIssue(
                severity="error",
                field="version",
                message="无法检测配置文件版本",
                suggestion="请检查配置文件是否存在且格式正确"
            ))
            return issues

        if from_version == to_version:
            issues.append(MigrationIssue(
                severity="info",
                field="version",
                message=f"配置已经是目标版本 {to_version}",
                suggestion="无需迁移"
            ))
            return issues

        # 加载当前配置
        config = self._load_env_file()

        # 获取迁移规则
        migration_key = f"{from_version}_{to_version}".replace(".", "_")
        if migration_key not in MIGRATION_RULES:
            issues.append(MigrationIssue(
                severity="error",
                field="migration",
                message=f"不支持从 {from_version} 到 {to_version} 的直接迁移",
                suggestion=f"请先迁移到中间版本"
            ))
            return issues

        rules = MIGRATION_RULES[migration_key]

        # 检查需要重命名的字段
        for old_name, new_name in rules["renames"].items():
            if old_name in config:
                issues.append(MigrationIssue(
                    severity="info",
                    field=old_name,
                    message=f"字段将被重命名: {old_name} -> {new_name}",
                ))

        # 检查需要删除的字段
        for field in rules["removes"]:
            if field in config:
                issues.append(MigrationIssue(
                    severity="warning",
                    field=field,
                    message=f"字段将被删除: {field}",
                    suggestion="请确认此字段不再需要"
                ))

        # 检查需要添加的字段
        for field, default_value in rules["additions"].items():
            if field not in config:
                issues.append(MigrationIssue(
                    severity="info",
                    field=field,
                    message=f"将添加新字段: {field} = {default_value}",
                ))

        return issues

    def migrate(
        self,
        from_version: Optional[ConfigVersion] = None,
        to_version: ConfigVersion = ConfigVersion.V2_0,
        backup: bool = True,
    ) -> MigrationReport:
        """
        执行配置迁移

        Args:
            from_version: 源版本，None表示自动检测
            to_version: 目标版本
            backup: 是否备份原配置

        Returns:
            迁移报告
        """
        # 检测源版本
        if from_version is None:
            from_version = self.detect_version()

        # 检查兼容性
        issues = self.check_compatibility(from_version, to_version)

        # 检查是否有致命错误
        has_errors = any(issue.severity == "error" for issue in issues)
        if has_errors:
            return MigrationReport(
                from_version=from_version.value,
                to_version=to_version.value,
                success=False,
                issues=issues,
                changes_made=[],
            )

        # 备份原配置
        backup_path = None
        if backup:
            backup_path = self._backup_config()

        # 加载当前配置
        config = self._load_env_file()
        changes_made = []

        # 获取迁移规则
        migration_key = f"{from_version}_{to_version}".replace(".", "_")
        rules = MIGRATION_RULES[migration_key]

        # 应用重命名
        for old_name, new_name in rules["renames"].items():
            if old_name in config:
                config[new_name] = config.pop(old_name)
                changes_made.append(f"重命名: {old_name} -> {new_name}")

        # 删除废弃字段
        for field in rules["removes"]:
            if field in config:
                del config[field]
                changes_made.append(f"删除: {field}")

        # 添加新字段
        for field, default_value in rules["additions"].items():
            if field not in config:
                config[field] = default_value
                changes_made.append(f"添加: {field} = {default_value}")

        # 应用值转换
        for field, transform in rules["transforms"].items():
            if field in config:
                old_value = config[field]
                config[field] = transform(old_value)
                changes_made.append(f"转换: {field} = {old_value} -> {config[field]}")

        # 保存新配置
        self._save_env_file(config)

        return MigrationReport(
            from_version=from_version.value,
            to_version=to_version.value,
            success=True,
            issues=issues,
            changes_made=changes_made,
            backup_path=backup_path,
        )

    def rollback(self, backup_path: Path) -> bool:
        """
        回滚到备份配置

        Args:
            backup_path: 备份文件路径

        Returns:
            是否成功回滚
        """
        if not backup_path.exists():
            return False

        try:
            shutil.copy(backup_path, self.config_path)
            return True
        except Exception:
            return False

    def _load_env_file(self) -> Dict[str, str]:
        """加载环境变量文件"""
        config = {}

        if not self.config_path.exists():
            return config

        with open(self.config_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()

                # 跳过注释和空行
                if not line or line.startswith('#'):
                    continue

                # 解析 KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip()

        return config

    def _save_env_file(self, config: Dict[str, str]) -> None:
        """保存环境变量文件"""
        lines = [
            "# Stock-CLI Configuration File",
            f"# Generated: {datetime.now().isoformat()}",
            "",
        ]

        # 按分组组织
        groups = {
            "APP_": "应用配置",
            "DATABASE_": "数据库配置",
            "DATA_": "数据源配置",
            "PATH_": "路径配置",
            "ML_": "机器学习配置",
        }

        for prefix, group_name in groups.items():
            group_keys = [k for k in sorted(config.keys()) if k.startswith(prefix)]
            if group_keys:
                lines.append(f"# ==================== {group_name} ====================")
                for key in group_keys:
                    lines.append(f"{key}={config[key]}")
                lines.append("")

        # 添加未分组的配置
        ungrouped = [k for k in sorted(config.keys()) if not any(k.startswith(p) for p in groups.keys())]
        if ungrouped:
            lines.append("# ==================== 其他配置 ====================")
            for key in ungrouped:
                lines.append(f"{key}={config[key]}")

        with open(self.config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _backup_config(self) -> Path:
        """备份配置文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.config_path.parent / f".env.backup.{timestamp}"
        shutil.copy(self.config_path, backup_path)
        return backup_path


def display_compatibility_report(issues: List[MigrationIssue]) -> None:
    """显示兼容性报告"""
    if not issues:
        console.print("[green]✓ 配置完全兼容，可以安全迁移[/green]")
        return

    table = Table(title="📋 兼容性检查报告")
    table.add_column("严重程度", style="cyan")
    table.add_column("字段", style="yellow")
    table.add_column("说明", style="white")
    table.add_column("建议", style="green")

    for issue in issues:
        severity_color = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
        }.get(issue.severity, "white")

        table.add_row(
            f"[{severity_color}]{issue.severity.upper()}[/{severity_color}]",
            issue.field,
            issue.message,
            issue.suggestion or "-"
        )

    console.print(table)

    # 统计
    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")
    info_count = sum(1 for i in issues if i.severity == "info")

    console.print(f"\n统计: [red]{error_count} 错误[/red], "
                  f"[yellow]{warning_count} 警告[/yellow], "
                  f"[blue]{info_count} 信息[/blue]")


def display_migration_report(report: MigrationReport) -> None:
    """显示迁移报告"""
    if report.success:
        console.print(Panel.fit(
            f"[bold green]✓ 迁移成功![/bold green]\n\n"
            f"从版本: [cyan]{report.from_version}[/cyan]\n"
            f"到版本: [cyan]{report.to_version}[/cyan]\n"
            f"时间: {report.timestamp}",
            border_style="green"
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]✗ 迁移失败[/bold red]\n\n"
            f"从版本: [cyan]{report.from_version}[/cyan]\n"
            f"到版本: [cyan]{report.to_version}[/cyan]",
            border_style="red"
        ))

    # 显示所做的更改
    if report.changes_made:
        console.print("\n[bold cyan]配置更改:[/bold cyan]")
        for i, change in enumerate(report.changes_made, 1):
            console.print(f"  {i}. {change}")

    # 显示备份信息
    if report.backup_path:
        console.print(f"\n[dim]原配置已备份到: {report.backup_path}[/dim]")
        console.print("[dim]如需回滚，请运行: stock-cli config rollback[/dim]")


def run_migration_wizard(
    config_path: Optional[Path] = None,
    target_version: ConfigVersion = ConfigVersion.V2_0,
) -> MigrationReport:
    """
    运行配置迁移向导

    Args:
        config_path: 配置文件路径
        target_version: 目标版本

    Returns:
        迁移报告
    """
    console.print(Panel.fit(
        "[bold cyan]🔄 配置迁移向导[/bold cyan]\n\n"
        "本向导将帮助您升级配置文件到新版本\n"
        "迁移前会自动备份原配置",
        border_style="cyan",
        title="Stock-CLI Migration Wizard"
    ))

    # 创建迁移器
    migrator = ConfigMigrator(config_path)

    # 检测当前版本
    console.print("\n[bold]正在检测配置版本...[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("检测中...", total=None)
        current_version = migrator.detect_version()
        progress.update(task, completed=True)

    if current_version == ConfigVersion.UNKNOWN:
        console.print("[red]✗ 无法检测配置版本[/red]")
        console.print("请确认配置文件存在且格式正确")
        return MigrationReport(
            from_version="unknown",
            to_version=target_version.value,
            success=False,
            issues=[],
            changes_made=[],
        )

    console.print(f"\n当前版本: [cyan]{current_version.value}[/cyan]")
    console.print(f"目标版本: [cyan]{target_version.value}[/cyan]")

    if current_version == target_version:
        console.print("\n[green]✓ 配置已经是最新版本，无需迁移[/green]")
        return MigrationReport(
            from_version=current_version.value,
            to_version=target_version.value,
            success=True,
            issues=[],
            changes_made=[],
        )

    # 兼容性检查
    console.print("\n[bold]正在检查兼容性...[/bold]")
    issues = migrator.check_compatibility(current_version, target_version)

    console.print()
    display_compatibility_report(issues)

    # 检查是否有致命错误
    has_errors = any(issue.severity == "error" for issue in issues)
    if has_errors:
        console.print("\n[red]✗ 存在致命错误，无法继续迁移[/red]")
        return MigrationReport(
            from_version=current_version.value,
            to_version=target_version.value,
            success=False,
            issues=issues,
            changes_made=[],
        )

    # 确认迁移
    console.print()
    if not Confirm.ask("是否开始迁移?", default=True):
        console.print("[yellow]迁移已取消[/yellow]")
        return MigrationReport(
            from_version=current_version.value,
            to_version=target_version.value,
            success=False,
            issues=issues,
            changes_made=[],
        )

    # 执行迁移
    console.print("\n[bold]正在迁移配置...[/bold]")
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("迁移中...", total=None)
        report = migrator.migrate(current_version, target_version)
        progress.update(task, completed=True)

    # 显示迁移报告
    console.print()
    display_migration_report(report)

    return report


def run_rollback_wizard(config_path: Optional[Path] = None) -> bool:
    """
    运行配置回滚向导

    Args:
        config_path: 配置文件路径

    Returns:
        是否成功回滚
    """
    console.print(Panel.fit(
        "[bold yellow]↩️  配置回滚向导[/bold yellow]\n\n"
        "本向导将帮助您回滚到之前的配置版本",
        border_style="yellow",
        title="Stock-CLI Rollback Wizard"
    ))

    if config_path is None:
        config_path = Path.cwd() / ".env"

    # 查找备份文件
    backup_files = sorted(
        config_path.parent.glob(".env.backup.*"),
        reverse=True
    )

    if not backup_files:
        console.print("\n[red]✗ 未找到备份文件[/red]")
        return False

    # 显示备份文件列表
    console.print("\n[bold]可用的备份文件:[/bold]\n")
    table = Table()
    table.add_column("编号", style="cyan")
    table.add_column("文件名", style="yellow")
    table.add_column("时间", style="green")

    for i, backup in enumerate(backup_files[:10], 1):  # 最多显示10个
        # 从文件名提取时间戳
        timestamp = backup.stem.replace(".env.backup.", "")
        try:
            dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
            time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            time_str = timestamp

        table.add_row(str(i), backup.name, time_str)

    console.print(table)

    # 选择备份
    choice = Prompt.ask(
        "\n请选择要回滚的备份（输入编号）",
        choices=[str(i) for i in range(1, min(len(backup_files) + 1, 11))],
        default="1"
    )

    selected_backup = backup_files[int(choice) - 1]

    # 确认回滚
    if not Confirm.ask(f"\n确认回滚到 {selected_backup.name}?", default=True):
        console.print("[yellow]回滚已取消[/yellow]")
        return False

    # 执行回滚
    migrator = ConfigMigrator(config_path)
    success = migrator.rollback(selected_backup)

    if success:
        console.print(f"\n[green]✓ 已成功回滚到: {selected_backup.name}[/green]")
    else:
        console.print(f"\n[red]✗ 回滚失败[/red]")

    return success


if __name__ == "__main__":
    # 测试运行
    run_migration_wizard()
