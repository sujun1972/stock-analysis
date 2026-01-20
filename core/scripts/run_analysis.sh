#!/bin/bash

# 激活虚拟环境
source stock_env/bin/activate

# 运行主程序
python src/main.py

# 保持终端打开
echo "分析完成！按任意键继续..."
read -n 1