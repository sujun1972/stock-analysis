# 配置文件
import os
from dotenv import load_dotenv

# 项目根目录和数据存储路径
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_PATH = os.path.join(BASE_DIR, "data")

# 从 .env 加载环境变量（如果存在）
ENV_PATH = os.path.join(BASE_DIR, ".env")
if os.path.exists(ENV_PATH):
    load_dotenv(ENV_PATH)

# Tushare token (可选，如果需要使用Tushare的高级功能)
TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN", "")  # 从环境变量读取，避免硬编码到仓库中

# 默认分析参数
DEFAULT_PERIOD = "1y"  # 默认数据期间
DEFAULT_INTERVAL = "1d"  # 默认数据间隔
