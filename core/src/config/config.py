# 配置文件（已废弃，建议使用 settings.py）
# 保留此文件仅为向后兼容

import os
from dotenv import load_dotenv

# 项目根目录和数据存储路径
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_PATH = os.path.join(BASE_DIR, "data")

# 从 .env 加载环境变量（如果存在）
ENV_PATH = os.path.join(BASE_DIR, "..", "..", ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

# Tushare token (可选，如果需要使用Tushare的高级功能)
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")

# 数据源配置
# 主要数据源：'akshare'(推荐，免费无限制), 'tushare'(需要Token), 'yfinance'(全球股票)
DEFAULT_DATA_SOURCE = os.getenv("DATA_SOURCE", "akshare")

# 默认分析参数
DEFAULT_PERIOD = "1y"  # 默认数据期间
DEFAULT_INTERVAL = "1d"  # 默认数据间隔

# 数据库配置（推荐使用 settings.py 中的配置）
DATABASE_CONFIG = {
    'host': os.getenv('DATABASE_HOST', 'localhost'),
    'port': int(os.getenv('DATABASE_PORT', '5432')),
    'database': os.getenv('DATABASE_NAME', 'stock_analysis'),
    'user': os.getenv('DATABASE_USER', 'stock_user'),
    'password': os.getenv('DATABASE_PASSWORD', 'stock_password_123')
}

DATA_PATH = "data"

# ==================== 新配置系统 ====================
# 建议使用新的配置管理系统：
#
#   from config.settings import get_settings
#
#   settings = get_settings()
#   db_config = settings.get_database_config()
#
# 旧代码兼容性：
#   from config.config import DATABASE_CONFIG  # 仍然可用
# ==================================================

