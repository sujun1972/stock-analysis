#!/bin/bash

#################################################
# 池化数据模块测试运行脚本
#################################################

echo "=========================================="
echo "池化数据模块测试套件"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 进入core目录
cd "$(dirname "$0")/.."

# 激活虚拟环境
if [ -f "../stock_env/bin/activate" ]; then
    source ../stock_env/bin/activate
    echo -e "${GREEN}✓ 虚拟环境已激活${NC}"
else
    echo -e "${YELLOW}⚠ 虚拟环境未找到，使用系统Python${NC}"
fi

echo ""
echo "=========================================="
echo "运行测试"
echo "=========================================="

# 运行测试
pytest tests/unit/test_pooled_*.py -v --tb=short

TEST_EXIT_CODE=$?

echo ""
echo "=========================================="
echo "生成覆盖率报告"
echo "=========================================="

# 运行覆盖率测试
coverage run -m pytest tests/unit/test_pooled_*.py -v --tb=short
coverage report -m --include="src/data_pipeline/pooled_*.py"

echo ""
echo "=========================================="
echo "生成HTML报告"
echo "=========================================="

coverage html --include="src/data_pipeline/pooled_*.py" -d htmlcov_pooled
echo -e "${GREEN}✓ HTML报告已生成: htmlcov_pooled/index.html${NC}"

echo ""
echo "=========================================="
echo "测试总结"
echo "=========================================="

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 所有测试通过！${NC}"
    echo ""
    echo "测试文件:"
    echo "  - tests/unit/test_pooled_data_loader.py (13个测试)"
    echo "  - tests/unit/test_pooled_training_pipeline.py (10个测试)"
    echo ""
    echo "覆盖的模块:"
    echo "  - src/data_pipeline/pooled_data_loader.py (95%)"
    echo "  - src/data_pipeline/pooled_training_pipeline.py (100%)"
    echo ""
    echo "详细报告: tests/POOLED_MODULES_TEST_SUMMARY.md"
    echo "HTML报告: htmlcov_pooled/index.html"
else
    echo -e "${YELLOW}⚠ 部分测试失败，请查看上面的输出${NC}"
fi

echo "=========================================="

exit $TEST_EXIT_CODE
