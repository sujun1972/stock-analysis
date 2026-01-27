#!/bin/bash

# Model Trainer 测试运行脚本
# 运行 Model Trainer 模块的单元测试和集成测试

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Model Trainer 测试套件${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 激活虚拟环境
if [ -d "stock_env" ]; then
    echo -e "${GREEN}✓ 激活虚拟环境${NC}"
    source stock_env/bin/activate
else
    echo -e "${RED}✗ 虚拟环境未找到${NC}"
    exit 1
fi

# 设置 PYTHONPATH
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"
echo -e "${GREEN}✓ PYTHONPATH 已设置${NC}"
echo ""

# 测试选项
RUN_UNIT=true
RUN_INTEGRATION=true
VERBOSE=""
COVERAGE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_INTEGRATION=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            shift
            ;;
        -v|--verbose)
            VERBOSE="-v -s"
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        -h|--help)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --unit-only          只运行单元测试"
            echo "  --integration-only   只运行集成测试"
            echo "  -v, --verbose        详细输出"
            echo "  --coverage           生成测试覆盖率报告"
            echo "  -h, --help           显示帮助信息"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            exit 1
            ;;
    esac
done

# 检查依赖
echo -e "${BLUE}检查依赖...${NC}"
python -c "import pytest" 2>/dev/null || {
    echo -e "${RED}✗ pytest 未安装${NC}"
    echo "请运行: pip install pytest pytest-cov"
    exit 1
}
echo -e "${GREEN}✓ pytest 已安装${NC}"

if [ "$COVERAGE" = true ]; then
    python -c "import pytest_cov" 2>/dev/null || {
        echo -e "${YELLOW}! pytest-cov 未安装，跳过覆盖率测试${NC}"
        COVERAGE=false
    }
fi
echo ""

# 创建测试结果目录
RESULTS_DIR="${PROJECT_ROOT}/test_results"
mkdir -p "$RESULTS_DIR"

# 测试计数器
PASSED=0
FAILED=0

# 运行单元测试
if [ "$RUN_UNIT" = true ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}运行单元测试${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ "$COVERAGE" = true ]; then
        pytest core/tests/unit/test_model_trainer.py \
            $VERBOSE \
            --tb=short \
            --cov=core.src.models.model_trainer \
            --cov-report=term-missing \
            --cov-report=html:$RESULTS_DIR/coverage_unit \
            --junit-xml=$RESULTS_DIR/junit_unit.xml
    else
        pytest core/tests/unit/test_model_trainer.py \
            $VERBOSE \
            --tb=short \
            --junit-xml=$RESULTS_DIR/junit_unit.xml
    fi

    UNIT_EXIT_CODE=$?

    if [ $UNIT_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ 单元测试通过${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 单元测试失败${NC}"
        ((FAILED++))
    fi
    echo ""
fi

# 运行集成测试
if [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}运行集成测试${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    if [ "$COVERAGE" = true ]; then
        pytest core/tests/integration/test_model_trainer_integration.py \
            $VERBOSE \
            --tb=short \
            --cov=core.src.models.model_trainer \
            --cov-report=term-missing \
            --cov-report=html:$RESULTS_DIR/coverage_integration \
            --junit-xml=$RESULTS_DIR/junit_integration.xml
    else
        pytest core/tests/integration/test_model_trainer_integration.py \
            $VERBOSE \
            --tb=short \
            --junit-xml=$RESULTS_DIR/junit_integration.xml
    fi

    INTEGRATION_EXIT_CODE=$?

    if [ $INTEGRATION_EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}✓ 集成测试通过${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ 集成测试失败${NC}"
        ((FAILED++))
    fi
    echo ""
fi

# 运行快速回归测试
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}运行快速回归测试${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

python test_model_trainer_refactor.py > /dev/null 2>&1
REFACTOR_EXIT_CODE=$?

if [ $REFACTOR_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ 回归测试通过${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ 回归测试失败${NC}"
    ((FAILED++))
fi
echo ""

# 测试总结
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}测试总结${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TOTAL=$((PASSED + FAILED))
echo -e "总测试套件: $TOTAL"
echo -e "${GREEN}通过: $PASSED${NC}"

if [ $FAILED -gt 0 ]; then
    echo -e "${RED}失败: $FAILED${NC}"
fi

echo ""

# 覆盖率报告
if [ "$COVERAGE" = true ]; then
    echo -e "${BLUE}测试覆盖率报告已生成:${NC}"
    if [ "$RUN_UNIT" = true ]; then
        echo -e "  单元测试: ${RESULTS_DIR}/coverage_unit/index.html"
    fi
    if [ "$RUN_INTEGRATION" = true ]; then
        echo -e "  集成测试: ${RESULTS_DIR}/coverage_integration/index.html"
    fi
    echo ""
fi

# 退出代码
if [ $FAILED -gt 0 ]; then
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}测试失败！${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
else
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}所有测试通过！${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
fi
