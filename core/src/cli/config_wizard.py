"""
配置向导

提供交互式配置初始化功能
"""

from pathlib import Path
from typing import Optional
import click
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from .utils.output import get_console, print_success, print_error, print_info
from ..utils.logger import get_logger

logger = get_logger(__name__)


def test_database_connection(host: str, port: int, database: str, user: str, password: str) -> bool:
    """
    测试数据库连接

    Args:
        host: 数据库主机
        port: 数据库端口
        database: 数据库名称
        user: 用户名
        password: 密码

    Returns:
        连接是否成功
    """
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=host, port=port, database=database, user=user, password=password, connect_timeout=5
        )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return False


def run_config_wizard():
    """运行配置向导"""
    console = get_console()

    # 显示欢迎信息
    welcome_text = """
[bold cyan]欢迎使用 Stock-CLI![/bold cyan]

这个向导将帮助您配置以下内容：
  • 数据库连接信息
  • 数据源设置
  • 存储路径配置

让我们开始吧！
    """
    console.print(Panel(welcome_text, border_style="cyan", title="配置向导"))

    # ==================== 数据库配置 ====================
    console.print("\n[bold yellow]1. 数据库配置[/bold yellow]")
    console.print("请输入 TimescaleDB 数据库连接信息：\n")

    db_host = Prompt.ask("数据库主机", default="localhost")
    db_port = Prompt.ask("数据库端口", default="5432")
    db_name = Prompt.ask("数据库名称", default="stock_analysis")
    db_user = Prompt.ask("数据库用户名", default="stock_user")
    db_password = Prompt.ask("数据库密码", password=True)

    # 测试连接
    if Confirm.ask("\n是否测试数据库连接?", default=True):
        print_info("正在测试数据库连接...")
        if test_database_connection(db_host, int(db_port), db_name, db_user, db_password):
            print_success("数据库连接成功！")
        else:
            print_error("数据库连接失败，请检查配置信息")
            if not Confirm.ask("是否继续保存配置?", default=True):
                console.print("[yellow]配置已取消[/yellow]")
                return

    # ==================== 数据源配置 ====================
    console.print("\n[bold yellow]2. 数据源配置[/bold yellow]")
    console.print("Stock-CLI 支持 AkShare 和 Tushare 两种数据源：\n")

    provider = Prompt.ask("默认数据源", choices=["akshare", "tushare"], default="akshare")

    tushare_token = ""
    if provider == "tushare" or Confirm.ask("\n是否配置 Tushare Token（可选）?", default=False):
        console.print(
            "\n[dim]获取 Tushare Token: https://tushare.pro/register?reg=127659[/dim]"
        )
        tushare_token = Prompt.ask("Tushare Token", default="")

    # DeepSeek API（可选）
    deepseek_api_key = ""
    if Confirm.ask("\n是否配置 DeepSeek API Key（可选，用于AI分析）?", default=False):
        console.print("\n[dim]获取 DeepSeek API Key: https://platform.deepseek.com/[/dim]")
        deepseek_api_key = Prompt.ask("DeepSeek API Key", default="")

    # ==================== 路径配置 ====================
    console.print("\n[bold yellow]3. 存储路径配置[/bold yellow]")
    console.print("配置数据、模型、缓存的存储路径：\n")

    data_dir = Prompt.ask("数据存储目录", default="/data")
    models_dir = Prompt.ask("模型存储目录", default=f"{data_dir}/models")
    cache_dir = Prompt.ask("缓存目录", default=f"{data_dir}/cache")
    results_dir = Prompt.ask("回测结果目录", default=f"{data_dir}/results")

    # ==================== 生成 .env 文件 ====================
    env_content = f"""# Stock-CLI 配置文件
# 自动生成时间: {click.get_current_context().meta.get('timestamp', 'unknown')}

# ==================== 数据库配置 ====================
DATABASE_HOST={db_host}
DATABASE_PORT={db_port}
DATABASE_NAME={db_name}
DATABASE_USER={db_user}
DATABASE_PASSWORD={db_password}

# ==================== 数据源配置 ====================
DATA_PROVIDER={provider}
DATA_TUSHARE_TOKEN={tushare_token}
DATA_DEEPSEEK_API_KEY={deepseek_api_key}

# ==================== 路径配置 ====================
PATH_DATA_DIR={data_dir}
PATH_MODELS_DIR={models_dir}
PATH_CACHE_DIR={cache_dir}
PATH_RESULTS_DIR={results_dir}

# ==================== 日志配置 ====================
LOG_LEVEL=INFO
LOG_FILE=logs/stock_cli.log
"""

    # 确定保存路径
    project_root = Path(__file__).parent.parent.parent.parent
    env_path = project_root / ".env"

    # 如果文件已存在，询问是否覆盖
    if env_path.exists():
        console.print(f"\n[yellow]配置文件已存在: {env_path}[/yellow]")
        if not Confirm.ask("是否覆盖现有配置?", default=False):
            # 备份
            backup_path = env_path.with_suffix(".env.backup")
            env_path.rename(backup_path)
            print_info(f"原配置已备份至: {backup_path}")

    # 保存配置
    try:
        env_path.write_text(env_content.strip())
        print_success(f"\n配置文件已保存: {env_path}")

        # 显示配置摘要
        console.print("\n[bold green]配置完成！[/bold green]")
        summary = f"""
数据库: {db_user}@{db_host}:{db_port}/{db_name}
数据源: {provider}
数据目录: {data_dir}
        """
        console.print(Panel(summary.strip(), title="配置摘要", border_style="green"))

        # 创建必要的目录
        if Confirm.ask("\n是否创建存储目录?", default=True):
            for dir_path in [data_dir, models_dir, cache_dir, results_dir]:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
                print_success(f"已创建目录: {dir_path}")

        # 显示下一步提示
        console.print("\n[bold cyan]下一步:[/bold cyan]")
        console.print("  1. 下载数据: [bold]stock-cli download --days 30[/bold]")
        console.print("  2. 查看帮助: [bold]stock-cli --help[/bold]")

    except Exception as e:
        print_error(f"保存配置文件失败: {e}")
        logger.exception("保存配置失败")
        raise
