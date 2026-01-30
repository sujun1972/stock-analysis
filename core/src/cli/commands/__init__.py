"""CLI子命令模块"""

# 导入所有命令以便在main.py中注册
from . import download
from . import features
from . import train
from . import backtest
from . import analyze

__all__ = ["download", "features", "train", "backtest", "analyze"]
