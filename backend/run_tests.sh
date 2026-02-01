#!/bin/bash

#######################################################
# Backend 测试运行脚本
#
# 用法:
#   ./run_tests.sh              # 运行所有测试
#   ./run_tests.sh unit         # 只运行单元测试
#   ./run_tests.sh integration  # 只运行集成测试
#   ./run_tests.sh coverage     # 生成覆盖率报告
#
# 作者: Backend Team
# 创建日期: 2026-02-01
#######################################################

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    echo -e "${BLUE}激活虚拟环境...${NC}"
    source venv/bin/activate
elif [ -d "../stock_env" ]; then
    echo -e "${BLUE}激活项目虚拟环境...${NC}"
    source ../stock_env/bin/activate
else
    echo -e "${YELLOW}警告: 未找到虚拟环境${NC}"
fi

# 检查 pytest 是否安装
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}错误: pytest 未安装${NC}"
    echo "请运行: pip install -r requirements-dev.txt"
    exit 1
fi

# 测试类型
TEST_TYPE="${1:-all}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Backend Stocks API 测试${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

case "$TEST_TYPE" in
    unit)
        echo -e "${BLUE}运行单元测试...${NC}"
        pytest tests/unit/ -v --tb=short
        ;;

    integration)
        echo -e "${BLUE}运行集成测试...${NC}"
        echo -e "${YELLOW}注意: 集成测试需要数据库连接${NC}"
        pytest tests/integration/ -v -m integration --tb=short
        ;;

    stocks)
        echo -e "${BLUE}运行 Stocks API 测试...${NC}"
        pytest tests/unit/api/test_stocks_api.py tests/integration/api/test_stocks_api_integration.py -v --tb=short
        ;;

    coverage)
        echo -e "${BLUE}生成覆盖率报告...${NC}"
        pytest tests/unit/ --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
        ;;

    quick)
        echo -e "${BLUE}快速测试（只运行单元测试，无覆盖率）...${NC}"
        pytest tests/unit/ -v --tb=short --no-cov
        ;;

    all|*)
        echo -e "${BLUE}运行所有测试...${NC}"
        pytest tests/ -v --tb=short
        ;;
esac

# 测试结果
TEST_RESULT=$?

echo ""
echo -e "${GREEN}========================================${NC}"
if [ $TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✅ 测试通过!${NC}"
else
    echo -e "${RED}❌ 测试失败!${NC}"
fi
echo -e "${GREEN}========================================${NC}"

exit $TEST_RESULT
