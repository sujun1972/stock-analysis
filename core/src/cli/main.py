#!/usr/bin/env python3
"""
Stock-CLI - A股量化交易系统命令行工具

使用说明:
    stock-cli --help              查看帮助
    stock-cli download --help     查看下载命令帮助
    stock-cli features --help     查看特征计算帮助
    stock-cli train --help        查看模型训练帮助
    stock-cli backtest --help     查看回测命令帮助
    stock-cli analyze --help      查看因子分析帮助
"""

import sys
from pathlib import Path
import click

# 添加项目路径以便导入
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from cli.utils.output import create_console, print_info
from utils.logger import setup_logger, get_logger

logger = get_logger(__name__)


@click.group()
@click.version_option(version="2.0.0", prog_name="stock-cli")
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="配置文件路径（默认使用项目根目录的 .env）",
)
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    default="INFO",
    help="日志级别",
)
@click.option("--no-color", is_flag=True, help="禁用彩色输出")
@click.pass_context
def cli(ctx, config, log_level, no_color):
    """
    A股量化交易系统命令行工具

    Stock-CLI 提供便捷的命令行接口来访问核心功能：

    \b
    • download  - 下载股票历史数据
    • features  - 计算技术指标和Alpha因子
    • train     - 训练机器学习模型
    • backtest  - 运行策略回测
    • analyze   - 进行因子分析
    • config    - 配置管理（模板、验证）

    示例:

    \b
        # 下载最近30天的数据
        stock-cli download --days 30

    \b
        # 计算指定股票的特征
        stock-cli features --symbols 000001,600000

    \b
        # 训练LightGBM模型
        stock-cli train --model lightgbm

    更多信息请访问: https://github.com/yourusername/stock-analysis
    """
    # 初始化上下文
    ctx.ensure_object(dict)

    # 设置日志
    setup_logger(log_level=log_level.upper())

    # 创建控制台
    console = create_console(no_color=no_color)
    ctx.obj["console"] = console
    ctx.obj["no_color"] = no_color

    # 加载配置
    if config:
        ctx.obj["config_file"] = config
        logger.info(f"使用配置文件: {config}")
    else:
        # 使用默认配置
        default_env = project_root / ".env"
        if default_env.exists():
            ctx.obj["config_file"] = str(default_env)
            logger.debug(f"使用默认配置文件: {default_env}")

    logger.info(f"Stock-CLI v2.0.0 启动 (日志级别: {log_level})")


# 注册子命令
# 导入命令模块
try:
    from cli.commands import download, features, train, backtest, analyze, config

    cli.add_command(download.download)
    cli.add_command(features.features)
    cli.add_command(train.train)
    cli.add_command(backtest.backtest)
    cli.add_command(analyze.analyze)
    cli.add_command(config.config)
except ImportError as e:
    # 命令模块尚未完全实现，先注册一个占位命令
    logger.warning(f"部分命令模块尚未实现: {e}")


# 添加 init 命令（配置向导）
@cli.command()
@click.pass_context
def init(ctx):
    """初始化配置（交互式向导）"""
    from cli.config_wizard import run_config_wizard

    try:
        run_config_wizard()
    except Exception as e:
        logger.exception("配置初始化失败")
        from cli.utils.output import print_error

        print_error(f"配置初始化失败: {e}")
        sys.exit(1)


# 添加 version 命令（详细版本信息）
@cli.command()
def version():
    """显示详细版本信息"""
    from cli.utils.output import print_table

    version_info = {
        "Stock-CLI": "2.0.0",
        "Python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "项目路径": str(project_root),
    }

    try:
        import pandas as pd
        import numpy as np
        import torch
        import lightgbm as lgb

        version_info.update(
            {
                "Pandas": pd.__version__,
                "NumPy": np.__version__,
                "PyTorch": torch.__version__,
                "LightGBM": lgb.__version__,
            }
        )
    except ImportError:
        pass

    print_table(version_info, title="版本信息")


def main():
    """CLI主函数"""
    try:
        cli(obj={})
    except Exception as e:
        logger.exception("CLI执行失败")
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
