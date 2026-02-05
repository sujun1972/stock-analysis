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

# 确定使用的 Python 和 pytest
if [ -d "venv" ]; then
    echo -e "${BLUE}使用 venv 虚拟环境...${NC}"
    PYTHON="venv/bin/python3"
    PYTEST="venv/bin/pytest"
elif [ -d "../stock_env" ]; then
    echo -e "${BLUE}使用项目虚拟环境 stock_env...${NC}"
    PYTHON="../stock_env/bin/python3.13"
    PYTEST="../stock_env/bin/pytest"
else
    echo -e "${YELLOW}警告: 未找到虚拟环境，使用系统 Python${NC}"
    PYTHON="python3"
    PYTEST="pytest"
fi

# 检查 pytest 是否存在
if ! [ -f "$PYTEST" ] && ! command -v pytest &> /dev/null; then
    echo -e "${RED}错误: pytest 未安装${NC}"
    echo "请运行: pip install -r requirements.txt"
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
        $PYTEST tests/unit/ -v --tb=short
        ;;

    integration)
        echo -e "${BLUE}运行集成测试...${NC}"
        echo -e "${YELLOW}注意: 集成测试需要数据库连接${NC}"
        $PYTEST tests/integration/ -v -m integration --tb=short
        ;;

    stocks)
        echo -e "${BLUE}运行 Stocks API 测试...${NC}"
        $PYTEST tests/unit/api/test_stocks_api.py tests/integration/api/test_stocks_api_integration.py -v --tb=short
        ;;

    coverage)
        echo -e "${BLUE}生成覆盖率报告...${NC}"
        $PYTEST tests/unit/ --cov=app --cov-report=html --cov-report=term-missing
        echo ""
        echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
        ;;

    quick)
        echo -e "${BLUE}快速测试（只运行单元测试，无覆盖率）...${NC}"
        $PYTEST tests/unit/ -v --tb=short --no-cov
        ;;

    all|*)
        echo -e "${BLUE}运行所有测试...${NC}"
        $PYTEST tests/ -v --tb=short
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
