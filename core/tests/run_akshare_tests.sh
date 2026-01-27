#!/bin/bash
# AkShareProvider 测试运行脚本

cd /Volumes/MacDriver/stock-analysis

# 激活虚拟环境
source stock_env/bin/activate

# 设置 Python 路径 - 关键：同时包含 core 和 core/src
export PYTHONPATH=/Volumes/MacDriver/stock-analysis:/Volumes/MacDriver/stock-analysis/core/src:$PYTHONPATH

echo "PYTHONPATH=$PYTHONPATH"

echo "======================================================================"
echo "Running AkShareProvider Unit Tests"
echo "======================================================================"

echo ""
echo "----------------------------------------------------------------------"
echo "Test 1: AkShareAPIClient"
echo "----------------------------------------------------------------------"
python core/tests/unit/providers/akshare/test_api_client.py

TEST1_EXIT=$?

echo ""
echo "----------------------------------------------------------------------"
echo "Test 2: AkShareDataConverter"
echo "----------------------------------------------------------------------"
python core/tests/unit/providers/akshare/test_data_converter.py

TEST2_EXIT=$?

echo ""
echo "----------------------------------------------------------------------"
echo "Test 3: AkShareProvider"
echo "----------------------------------------------------------------------"
python core/tests/unit/providers/akshare/test_provider.py

TEST3_EXIT=$?

echo ""
echo "======================================================================"
echo "Test Results Summary"
echo "======================================================================"
echo "API Client Tests: $([ $TEST1_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "Data Converter Tests: $([ $TEST2_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
echo "Provider Tests: $([ $TEST3_EXIT -eq 0 ] && echo '✓ PASS' || echo '✗ FAIL')"
