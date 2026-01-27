#!/bin/bash
# TushareProvider 测试运行脚本

cd /Volumes/MacDriver/stock-analysis

# 设置 Python 路径
export PYTHONPATH=/Volumes/MacDriver/stock-analysis/core/src:$PYTHONPATH

# 使用虚拟环境的 Python
PYTHON=/Volumes/MacDriver/stock-analysis/stock_env/bin/python

echo "======================================================================"
echo "Running TushareProvider Unit Tests"
echo "======================================================================"

echo ""
echo "----------------------------------------------------------------------"
echo "Test 1: TushareDataConverter"
echo "----------------------------------------------------------------------"
$PYTHON core/tests/unit/providers/tushare/test_data_converter.py

echo ""
echo "----------------------------------------------------------------------"
echo "Test 2: TushareAPIClient"
echo "----------------------------------------------------------------------"
$PYTHON core/tests/unit/providers/tushare/test_api_client.py

echo ""
echo "----------------------------------------------------------------------"
echo "Test 3: TushareProvider"
echo "----------------------------------------------------------------------"
$PYTHON core/tests/unit/providers/tushare/test_provider.py

echo ""
echo "======================================================================"
echo "All Unit Tests Completed"
echo "======================================================================"
