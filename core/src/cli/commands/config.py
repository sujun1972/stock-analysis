#!/usr/bin/env python3
"""
配置管理命令

提供配置模板的管理、验证和诊断功能
"""

import sys
from pathlib import Path
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
import json

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config.templates import ConfigTemplateManager
from config.validators import ConfigValidator
from config.diagnostics import ConfigDiagnostics

console = Console()


@click.group()
def config():
    """配置管理命令"""
    pass


# ==================== 模板相关命令 ====================


@config.command("templates-list")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json"], case_sensitive=False),
    default="table",
    help="输出格式",
)
def templates_list(format):
    """列出所有可用的配置模板

    示例:
        stock-cli config templates-list
        stock-cli config templates-list -f json
    """
    try:
        manager = ConfigTemplateManager()
        templates = manager.list_templates()

        if not templates:
            console.print("[yellow]未找到可用模板[/yellow]")
            return

        if format == "json":
            # JSON 格式输出
            templates_data = [
                {
                    "name": t.name,
                    "description": t.description,
                    "version": t.version,
                    "tags": t.tags,
                }
                for t in templates
            ]
            console.print_json(data=templates_data)
        else:
            # 表格格式输出
            table = Table(title="可用配置模板", show_lines=True)
            table.add_column("模板名称", style="cyan", no_wrap=True)
            table.add_column("描述", style="green")
            table.add_column("版本", style="yellow", justify="center")
            table.add_column("标签", style="magenta")

            for template in templates:
                # 提取模板文件名（不含.yaml后缀）
                template_file = Path(template.name).stem if "." in template.name else template.name
                tags = ", ".join(template.tags) if template.tags else "-"

                # 截断描述
                description = template.description
                if len(description) > 60:
                    description = description[:57] + "..."

                table.add_row(template_file, description, template.version, tags)

            console.print(table)
            console.print(
                f"\n[dim]提示: 使用 'stock-cli config templates-show <name>' 查看模板详情[/dim]"
            )

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)


@config.command("templates-show")
@click.argument("name")
@click.option("--settings", is_flag=True, help="显示完整配置内容")
def templates_show(name, settings):
    """显示模板详情

    参数:
        NAME: 模板名称（不含 .yaml 后缀）

    示例:
        stock-cli config templates-show development
        stock-cli config templates-show production --settings
    """
    try:
        manager = ConfigTemplateManager()
        template = manager.load_template(name)

        # 基本信息
        info_lines = [
            f"[bold cyan]名称:[/bold cyan] {template.name}",
            f"[bold cyan]描述:[/bold cyan] {template.description}",
            f"[bold cyan]版本:[/bold cyan] {template.version}",
        ]

        if template.tags:
            info_lines.append(
                f"[bold cyan]标签:[/bold cyan] {', '.join(template.tags)}"
            )

        if template.extends:
            info_lines.append(f"[bold cyan]继承:[/bold cyan] {template.extends}")

        info_text = "\n".join(info_lines)
        console.print(Panel(info_text, title=f"模板: {name}", border_style="cyan"))

        # 配置内容
        if settings and template.settings:
            console.print("\n[bold yellow]配置内容:[/bold yellow]")
            console.print_json(data=template.settings)

        # 使用建议
        if template.recommendations:
            console.print("\n[bold green]配置建议:[/bold green]")
            for i, rec in enumerate(template.recommendations, 1):
                console.print(f"  {i}. {rec}")

        console.print(
            f"\n[dim]提示: 使用 'stock-cli config templates-apply {name}' 应用此模板[/dim]"
        )

    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]未知错误: {e}[/red]")
        sys.exit(1)


@config.command("templates-apply")
@click.argument("name")
@click.option("--dry-run", is_flag=True, help="预览模式，不实际写入文件")
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help=".env 文件路径（默认: 当前目录/.env）",
)
def templates_apply(name, dry_run, output):
    """应用配置模板

    参数:
        NAME: 模板名称（不含 .yaml 后缀）

    示例:
        stock-cli config templates-apply development
        stock-cli config templates-apply production --dry-run
        stock-cli config templates-apply minimal -o /path/to/.env
    """
    try:
        manager = ConfigTemplateManager()

        # 确定输出路径
        env_path = Path(output) if output else None

        if dry_run:
            console.print("[yellow]预览模式（不会修改文件）[/yellow]\n")
            env_content = manager.apply_template(name, dry_run=True, env_path=env_path)

            # 语法高亮显示
            syntax = Syntax(env_content, "bash", theme="monokai", line_numbers=False)
            console.print(syntax)

            console.print(
                f"\n[dim]提示: 去掉 --dry-run 选项以实际应用模板[/dim]"
            )
        else:
            # 确认操作
            if env_path and env_path.exists():
                if not click.confirm(
                    f"文件已存在: {env_path}，是否覆盖（会自动备份）?"
                ):
                    console.print("[yellow]操作已取消[/yellow]")
                    return

            # 应用模板
            env_content = manager.apply_template(
                name, dry_run=False, env_path=env_path
            )

            target_path = env_path if env_path else Path.cwd() / ".env"
            console.print(f"\n[green]✓[/green] 已应用模板: {name}")
            console.print(f"[green]✓[/green] 配置已写入: {target_path}")

            # 显示建议
            template = manager.load_template(name)
            if template.recommendations:
                console.print("\n[bold cyan]配置建议:[/bold cyan]")
                for rec in template.recommendations:
                    console.print(f"  • {rec}")

    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]未知错误: {e}[/red]")
        sys.exit(1)


@config.command("templates-export")
@click.argument("name")
@click.option("--description", "-d", required=True, help="模板描述")
@click.option("--version", "-v", default="1.0", help="模板版本")
@click.option("--tags", "-t", help="模板标签（逗号分隔）")
@click.option(
    "--env-file", type=click.Path(exists=True), help=".env 文件路径（默认: 当前目录）"
)
def templates_export(name, description, version, tags, env_file):
    """导出当前配置为模板

    参数:
        NAME: 新模板的名称

    示例:
        stock-cli config templates-export my-template -d "我的自定义配置"
        stock-cli config templates-export my-prod -d "生产配置" -v "2.0" -t "production,custom"
    """
    try:
        manager = ConfigTemplateManager()

        # 解析标签
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        # 确定 .env 文件路径
        env_path = Path(env_file) if env_file else None

        # 导出模板
        template_path = manager.export_current_as_template(
            name=name,
            description=description,
            version=version,
            tags=tag_list,
            env_path=env_path,
        )

        console.print(f"[green]✓[/green] 已导出模板: {template_path}")
        console.print(
            f"\n[dim]提示: 使用 'stock-cli config templates-show {name}' 查看导出的模板[/dim]"
        )

    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]未知错误: {e}[/red]")
        sys.exit(1)


@config.command("templates-diff")
@click.argument("name1")
@click.argument("name2")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="输出格式",
)
def templates_diff(name1, name2, format):
    """对比两个模板

    参数:
        NAME1: 第一个模板名称
        NAME2: 第二个模板名称

    示例:
        stock-cli config templates-diff development production
        stock-cli config templates-diff minimal backtest -f json
    """
    try:
        manager = ConfigTemplateManager()
        diff_result = manager.diff_templates(name1, name2)

        if format == "json":
            console.print_json(data=diff_result)
        else:
            # 文本格式输出
            console.print(
                Panel(
                    f"[cyan]{name1}[/cyan] vs [cyan]{name2}[/cyan]",
                    title="模板对比",
                    border_style="cyan",
                )
            )

            settings_diff = diff_result["settings_diff"]

            # 新增配置
            if settings_diff["added"]:
                console.print("\n[bold green]新增配置:[/bold green]")
                for path, value in settings_diff["added"].items():
                    console.print(f"  + {path}: {value}")

            # 删除配置
            if settings_diff["removed"]:
                console.print("\n[bold red]删除配置:[/bold red]")
                for path, value in settings_diff["removed"].items():
                    console.print(f"  - {path}: {value}")

            # 修改配置
            if settings_diff["changed"]:
                console.print("\n[bold yellow]修改配置:[/bold yellow]")
                for path, change in settings_diff["changed"].items():
                    console.print(
                        f"  ~ {path}: {change['from']} → {change['to']}"
                    )

            # 统计
            total_changes = (
                len(settings_diff["added"])
                + len(settings_diff["removed"])
                + len(settings_diff["changed"])
            )
            console.print(f"\n[dim]总差异数: {total_changes}[/dim]")

    except ValueError as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]未知错误: {e}[/red]")
        sys.exit(1)


# ==================== 配置查看命令 ====================


@config.command("show")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="输出格式",
)
def show(format):
    """显示当前配置摘要

    示例:
        stock-cli config show
        stock-cli config show -f json
    """
    try:
        from config import get_settings

        settings = get_settings()

        if format == "json":
            # JSON 格式输出
            settings_dict = {
                "database": {
                    "host": settings.database.host,
                    "port": settings.database.port,
                    "database": settings.database.database,
                    "user": settings.database.user,
                },
                "data_source": {
                    "provider": settings.data_source.provider,
                    "has_tushare": settings.data_source.has_tushare,
                },
                "paths": {
                    "data_dir": settings.paths.data_dir,
                    "models_dir": settings.paths.models_dir,
                    "cache_dir": settings.paths.cache_dir,
                    "results_dir": settings.paths.results_dir,
                },
            }
            console.print_json(data=settings_dict)
        else:
            # 表格格式输出
            table = Table(title="当前配置摘要", show_lines=True)
            table.add_column("配置项", style="cyan")
            table.add_column("值", style="green")

            # 数据库配置
            table.add_row("[bold]数据库配置[/bold]", "")
            table.add_row("  主机", settings.database.host)
            table.add_row("  端口", str(settings.database.port))
            table.add_row("  数据库", settings.database.database)
            table.add_row("  用户", settings.database.user)

            # 数据源配置
            table.add_row("[bold]数据源配置[/bold]", "")
            table.add_row("  提供者", settings.data_source.provider)
            table.add_row(
                "  Tushare",
                "已配置" if settings.data_source.has_tushare else "未配置",
            )

            # 路径配置
            table.add_row("[bold]路径配置[/bold]", "")
            table.add_row("  数据目录", settings.paths.data_dir)
            table.add_row("  模型目录", settings.paths.models_dir)
            table.add_row("  缓存目录", settings.paths.cache_dir)
            table.add_row("  结果目录", settings.paths.results_dir)

            console.print(table)

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        sys.exit(1)


# ==================== 验证相关命令 ====================


@config.command("validate")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "json", "html"], case_sensitive=False),
    default="console",
    help="输出格式",
)
@click.option("--output", "-o", type=click.Path(), help="输出文件路径（JSON/HTML格式）")
def validate(format, output):
    """验证配置

    检查配置的正确性、完整性和安全性。

    示例:
        stock-cli config validate
        stock-cli config validate -f json -o report.json
        stock-cli config validate -f html -o report.html
    """
    try:
        validator = ConfigValidator()

        with console.status("[bold green]正在验证配置..."):
            report = validator.validate_all()

        if format == "console":
            report.to_console()
        elif format == "json":
            json_output = report.to_json()
            if output:
                Path(output).write_text(json_output, encoding='utf-8')
                console.print(f"[green]✓[/green] 已保存到: {output}")
            else:
                console.print(json_output)
        elif format == "html":
            html_output = report.to_html()
            if output:
                Path(output).write_text(html_output, encoding='utf-8')
                console.print(f"[green]✓[/green] 已保存到: {output}")
            else:
                console.print("[yellow]HTML 格式需要指定输出文件 (--output)[/yellow]")

        # 根据验证结果设置退出码
        if not report.passed:
            sys.exit(1)

    except Exception as e:
        console.print(f"[red]验证失败: {e}[/red]")
        sys.exit(1)


@config.command("diagnose")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["console", "markdown", "html"], case_sensitive=False),
    default="console",
    help="输出格式",
)
@click.option("--output", "-o", type=click.Path(), help="输出文件路径")
def diagnose(format, output):
    """诊断配置问题

    运行系统健康检查，提供优化建议和冲突检测。

    示例:
        stock-cli config diagnose
        stock-cli config diagnose -f markdown -o report.md
    """
    try:
        diagnostics = ConfigDiagnostics()

        with console.status("[bold green]正在诊断配置..."):
            health = diagnostics.run_health_check()
            suggestions = diagnostics.suggest_optimizations()
            conflicts = diagnostics.detect_conflicts()

        if format == "console":
            diagnostics._format_console_report(health, suggestions, conflicts)
        else:
            report = diagnostics.generate_report(format=format)
            if output:
                Path(output).write_text(report, encoding='utf-8')
                console.print(f"[green]✓[/green] 已保存到: {output}")
            else:
                console.print(report)

    except Exception as e:
        console.print(f"[red]诊断失败: {e}[/red]")
        sys.exit(1)


# ==================== 向导命令 ====================


@config.command("wizard")
@click.option(
    "--advanced", is_flag=True, help="运行高级配置向导（性能、特征、策略等）"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="配置输出路径（高级向导生成 advanced.yaml）",
)
def wizard(advanced, output):
    """运行配置向导

    默认运行基础配置向导，使用 --advanced 运行高级配置向导。

    示例:
        stock-cli config wizard                 # 基础向导
        stock-cli config wizard --advanced      # 高级向导
    """
    try:
        if advanced:
            # 运行高级配置向导
            from config.advanced_wizard import run_advanced_wizard

            output_path = Path(output) if output else None
            console.print("[cyan]启动高级配置向导...[/cyan]\n")
            config_data = run_advanced_wizard(output_path)

            if config_data:
                console.print("\n[green]✓ 高级配置向导完成![/green]")
        else:
            # 运行基础配置向导
            from cli.config_wizard import run_config_wizard

            console.print("[cyan]启动基础配置向导...[/cyan]\n")
            run_config_wizard()

            console.print("\n[green]✓ 基础配置向导完成![/green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]向导已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]向导执行失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


@config.command("migrate")
@click.option(
    "--from",
    "from_version",
    type=click.Choice(["v1.0", "v1.5", "v2.0", "auto"], case_sensitive=False),
    default="auto",
    help="源版本（auto表示自动检测）",
)
@click.option(
    "--to",
    "to_version",
    type=click.Choice(["v1.5", "v2.0"], case_sensitive=False),
    default="v2.0",
    help="目标版本",
)
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help=".env 文件路径（默认: 当前目录/.env）",
)
def migrate(from_version, to_version, config_file):
    """迁移配置到新版本

    自动检测配置版本并迁移到目标版本，迁移前会自动备份。

    示例:
        stock-cli config migrate                    # 自动检测并迁移到v2.0
        stock-cli config migrate --from v1.0 --to v2.0
        stock-cli config migrate -c /path/to/.env
    """
    try:
        from config.migration_wizard import (
            run_migration_wizard,
            ConfigVersion,
        )

        console.print("[cyan]启动配置迁移向导...[/cyan]\n")

        # 转换版本参数
        target_version = {
            "v1.5": ConfigVersion.V1_5,
            "v2.0": ConfigVersion.V2_0,
        }[to_version]

        config_path = Path(config_file) if config_file else None

        # 运行迁移向导
        report = run_migration_wizard(config_path, target_version)

        # 根据迁移结果设置退出码
        if not report.success:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]迁移已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]迁移失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


@config.command("rollback")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(),
    help=".env 文件路径（默认: 当前目录/.env）",
)
def rollback(config_file):
    """回滚到之前的配置版本

    从备份文件中恢复配置。

    示例:
        stock-cli config rollback
        stock-cli config rollback -c /path/to/.env
    """
    try:
        from config.migration_wizard import run_rollback_wizard

        console.print("[yellow]启动配置回滚向导...[/yellow]\n")

        config_path = Path(config_file) if config_file else None

        # 运行回滚向导
        success = run_rollback_wizard(config_path)

        if not success:
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]回滚已取消[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]回滚失败: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


@config.command("version")
@click.option(
    "--config-file",
    "-c",
    type=click.Path(exists=True),
    help=".env 文件路径（默认: 当前目录/.env）",
)
def version(config_file):
    """检测配置文件版本

    示例:
        stock-cli config version
        stock-cli config version -c /path/to/.env
    """
    try:
        from config.migration_wizard import ConfigMigrator

        config_path = Path(config_file) if config_file else None
        migrator = ConfigMigrator(config_path)

        detected_version = migrator.detect_version()

        console.print(
            Panel(
                f"[bold cyan]配置版本:[/bold cyan] {detected_version.value}",
                title="配置版本检测",
                border_style="cyan",
            )
        )

    except Exception as e:
        console.print(f"[red]版本检测失败: {e}[/red]")
        sys.exit(1)


# ==================== 帮助命令 ====================


@config.command("help")
def help_cmd():
    """显示配置管理帮助

    示例:
        stock-cli config help
    """
    help_text = """
[bold cyan]配置管理命令使用指南[/bold cyan]

[bold yellow]配置向导:[/bold yellow]
  wizard                      运行基础配置向导
  wizard --advanced           运行高级配置向导（性能、特征、策略等）

[bold yellow]配置迁移:[/bold yellow]
  migrate                     迁移配置到新版本（自动检测源版本）
  migrate --from v1.0 --to v2.0  指定版本迁移
  rollback                    回滚到之前的配置版本
  version                     检测配置文件版本

[bold yellow]模板管理:[/bold yellow]
  templates-list              列出所有可用模板
  templates-show <name>       显示模板详情
  templates-apply <name>      应用模板到 .env 文件
  templates-export <name>     导出当前配置为模板
  templates-diff <n1> <n2>    对比两个模板

[bold yellow]配置验证:[/bold yellow]
  validate                    验证配置正确性和安全性
  diagnose                    诊断配置问题并提供优化建议

[bold yellow]配置查看:[/bold yellow]
  show                        显示当前配置摘要

[bold green]常用示例:[/bold green]
  # 运行基础配置向导（首次使用）
  stock-cli config wizard

  # 运行高级配置向导（性能优化）
  stock-cli config wizard --advanced

  # 检测配置版本
  stock-cli config version

  # 迁移配置到v2.0
  stock-cli config migrate

  # 回滚到之前的配置
  stock-cli config rollback

  # 查看所有可用模板
  stock-cli config templates-list

  # 应用生产环境模板
  stock-cli config templates-apply production

  # 预览应用模板（不写入文件）
  stock-cli config templates-apply development --dry-run

  # 验证当前配置
  stock-cli config validate

  # 诊断配置并获取优化建议
  stock-cli config diagnose

  # 生成 HTML 验证报告
  stock-cli config validate -f html -o report.html

  # 导出当前配置为自定义模板
  stock-cli config templates-export my-config -d "我的配置"

  # 对比两个模板
  stock-cli config templates-diff development production

  # 查看当前配置
  stock-cli config show

[bold cyan]内置模板:[/bold cyan]
  • minimal      - 最小配置（快速上手）
  • development  - 开发环境
  • production   - 生产环境
  • research     - 研究环境
  • backtest     - 回测优化
  • training     - 模型训练

更多信息请访问文档: https://github.com/yourusername/stock-analysis
    """
    console.print(Panel(help_text.strip(), border_style="cyan"))


if __name__ == "__main__":
    config()
