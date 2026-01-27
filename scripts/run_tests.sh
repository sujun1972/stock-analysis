#!/bin/bash
# 测试运行脚本 - 在 Docker 环境中运行测试套件
# 使用方式: ./scripts/run_tests.sh [选项] [测试类型]
# 详细文档: docs/TESTING_GUIDE.md

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 终端颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

show_help() {
    cat << EOF
测试运行脚本 - 在 Docker 环境中运行测试套件

用法: $0 [选项] [测试类型]

测试类型:
    model_evaluator         ModelEvaluator 基础测试（37个用例，~0.04s）
    model_evaluator_full    ModelEvaluator 综合测试（63个用例，~0.3s）
    all_unit               所有单元测试
    all                    所有测试（单元+集成）
    custom <path>          自定义测试文件

选项:
    -h, --help            显示帮助信息
    -v, --verbose         详细输出
    -k <pattern>          只运行匹配模式的测试

示例:
    $0 model_evaluator                    # 基础测试
    $0 model_evaluator_full               # 综合测试
    $0 -k IC model_evaluator             # 只运行 IC 相关测试
    $0 custom tests/unit/test_features.py # 自定义测试

详细文档: docs/TESTING_GUIDE.md
EOF
}

# 参数解析
VERBOSE=""
PATTERN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE="-v"
            shift
            ;;
        -k)
            PATTERN="-k $2"
            shift 2
            ;;
        *)
            TEST_TYPE="$1"
            shift
            ;;
    esac
done

TEST_TYPE="${TEST_TYPE:-model_evaluator}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}运行测试: $TEST_TYPE${NC}"
echo -e "${GREEN}========================================${NC}"

cd "$PROJECT_ROOT"

# 执行测试
case $TEST_TYPE in
    model_evaluator)
        echo -e "${YELLOW}运行 ModelEvaluator 基础测试 (37 用例)...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
            python /app/core/tests/unit/test_model_evaluator.py $VERBOSE
        ;;

    model_evaluator_full)
        echo -e "${YELLOW}运行 ModelEvaluator 综合测试 (63 用例)...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
            python /app/core/tests/unit/test_model_evaluator_comprehensive.py $VERBOSE
        ;;

    all_unit)
        echo -e "${YELLOW}运行所有单元测试...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
            sh -c "cd /app/core && python -m pytest tests/unit/ $VERBOSE $PATTERN"
        ;;

    all)
        echo -e "${YELLOW}运行所有测试（单元 + 集成）...${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
            sh -c "cd /app/core && python -m pytest tests/ $VERBOSE $PATTERN"
        ;;

    custom)
        if [ -z "$2" ]; then
            echo -e "${RED}错误: 请指定测试文件路径${NC}"
            echo "示例: $0 custom tests/unit/test_features.py"
            exit 1
        fi
        TEST_FILE="$2"
        echo -e "${YELLOW}运行自定义测试: $TEST_FILE${NC}"
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
            python "/app/core/$TEST_FILE" $VERBOSE
        ;;

    *)
        echo -e "${RED}错误: 未知的测试类型 '$TEST_TYPE'${NC}"
        show_help
        exit 1
        ;;
esac

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✓ 测试通过！${NC}"
else
    echo -e "\n${RED}✗ 测试失败！${NC}"
fi

exit $EXIT_CODE
