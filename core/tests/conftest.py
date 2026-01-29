"""
Pytest配置文件

确保测试可以正确导入src模块
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
src_path = Path(__file__).parent.parent / 'src'
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
