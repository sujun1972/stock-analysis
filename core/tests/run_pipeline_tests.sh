#!/bin/bash
# DataPipeline 测试运行脚本
#
# 运行所有 pipeline 相关的测试
# 使用方法:
#   chmod +x run_pipeline_tests.sh
#   ./run_pipeline_tests.sh [unit|integration|all]

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/../.."

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DataPipeline 测试套件${NC}"
echo -e "${BLUE}========================================${NC}"

# 确保在项目根目录
cd "$PROJECT_ROOT"

# 默认运行所有测试
TEST_TYPE="${1:-all}"

# 初始化计数器
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 运行单元测试
run_unit_tests() {
    echo -e "\n${YELLOW}[1/3] 运行单元测试...${NC}"
    echo "----------------------------------------"

    # 测试配置类
    echo -e "${BLUE}测试 PipelineConfig...${NC}"
    if python3 tests/unit/test_pipeline_config.py; then
        echo -e "${GREEN}✓ PipelineConfig 测试通过${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ PipelineConfig 测试失败${NC}"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    # 测试 Pipeline 主类
    echo -e "\n${BLUE}测试 DataPipeline...${NC}"
    if python3 tests/unit/test_pipeline.py; then
        echo -e "${GREEN}✓ DataPipeline 测试通过${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ DataPipeline 测试失败${NC}"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# 运行集成测试
run_integration_tests() {
    echo -e "\n${YELLOW}[2/3] 运行集成测试...${NC}"
    echo "----------------------------------------"

    echo -e "${BLUE}测试 DataPipeline 集成...${NC}"
    if python3 tests/integration/test_pipeline_integration.py; then
        echo -e "${GREEN}✓ Pipeline 集成测试通过${NC}"
        ((PASSED_TESTS++))
    else
        echo -e "${RED}✗ Pipeline 集成测试失败${NC}"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# 使用 pytest 运行（如果可用）
run_pytest() {
    echo -e "\n${YELLOW}[3/3] 使用 pytest 运行（可选）...${NC}"
    echo "----------------------------------------"

    if command -v pytest &> /dev/null; then
        echo -e "${BLUE}运行 pytest...${NC}"
        if pytest tests/unit/test_pipeline*.py tests/integration/test_pipeline*.py -v --tb=short; then
            echo -e "${GREEN}✓ pytest 测试通过${NC}"
        else
            echo -e "${RED}✗ pytest 测试失败${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ pytest 未安装，跳过${NC}"
    fi
}

# 根据参数运行测试
case "$TEST_TYPE" in
    unit)
        echo -e "${YELLOW}运行单元测试...${NC}"
        run_unit_tests
        ;;
    integration)
        echo -e "${YELLOW}运行集成测试...${NC}"
        run_integration_tests
        ;;
    all)
        echo -e "${YELLOW}运行所有测试...${NC}"
        run_unit_tests
        run_integration_tests
        run_pytest
        ;;
    *)
        echo -e "${RED}错误: 未知的测试类型 '$TEST_TYPE'${NC}"
        echo "使用方法: $0 [unit|integration|all]"
        exit 1
        ;;
esac

# 打印总结
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}测试总结${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "总计: ${TOTAL_TESTS}"
echo -e "${GREEN}通过: ${PASSED_TESTS}${NC}"
echo -e "${RED}失败: ${FAILED_TESTS}${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}✓ 所有测试通过！${NC}"
    exit 0
else
    echo -e "\n${RED}✗ 有测试失败${NC}"
    exit 1
fi
