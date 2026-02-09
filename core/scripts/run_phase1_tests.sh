#!/bin/bash

# Phase 1 测试运行脚本
# 运行所有与Phase 1相关的测试

set -e  # 遇到错误立即退出

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CORE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

echo "========================================"
echo "Phase 1 测试套件"
echo "========================================"
echo ""

cd "$CORE_DIR"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}1. 运行单元测试...${NC}"
echo "--------------------------------------"
./venv/bin/pytest tests/unit/strategies/test_database_strategy_loader.py -v --tb=short

echo ""
echo -e "${BLUE}2. 运行集成测试...${NC}"
echo "--------------------------------------"
./venv/bin/pytest tests/integration/strategies/test_builtin_strategies_integration.py -v --tb=short -m integration

echo ""
echo -e "${BLUE}3. 运行策略验证脚本...${NC}"
echo "--------------------------------------"
./venv/bin/python scripts/verify_strategy_loading.py

echo ""
echo "========================================"
echo -e "${GREEN}✓ 所有测试通过!${NC}"
echo "========================================"
echo ""
echo "测试总结:"
echo "  - 单元测试: 11 个用例"
echo "  - 集成测试: 8 个用例"
echo "  - 验证脚本: 3 个策略"
echo ""
echo "Phase 1 实施完成并通过所有测试验证!"
