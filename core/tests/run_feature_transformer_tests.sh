#!/bin/bash
# 运行 feature_transformer 测试的便捷脚本

set -e

echo "========================================"
echo "Feature Transformer 测试运行器"
echo "========================================"
echo ""

# 设置 Python 路径
export PYTHONPATH="/app/src:${PYTHONPATH}"

# 运行测试
cd /app
python /app/src/../tests/unit/test_feature_transformer.py

echo ""
echo "测试完成!"
