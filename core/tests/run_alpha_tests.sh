#!/bin/bash
# Alpha因子测试运行脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "Alpha因子模块测试套件"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检测Python环境
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo -e "${RED}错误: 找不到Python环境${NC}"
    exit 1
fi

echo "使用Python: $PYTHON_CMD"
echo ""

# 检测pytest
if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
    echo -e "${RED}错误: pytest未安装${NC}"
    echo "请运行: pip install pytest pytest-cov"
    exit 1
fi

# 切换到core目录
cd "$(dirname "$0")/.."
echo "工作目录: $(pwd)"
echo ""

# ========================================
# 1. 基础测试
# ========================================
echo -e "${YELLOW}[1/5] 运行基础测试...${NC}"
$PYTHON_CMD -m pytest tests/unit/test_alpha_factors.py \
    -v \
    --tb=short \
    --maxfail=5 \
    || echo -e "${RED}基础测试失败${NC}"

echo ""

# ========================================
# 2. 扩展测试
# ========================================
echo -e "${YELLOW}[2/5] 运行扩展测试...${NC}"
$PYTHON_CMD -m pytest tests/unit/test_alpha_factors_extended.py \
    -v \
    --tb=short \
    --maxfail=5 \
    || echo -e "${RED}扩展测试失败${NC}"

echo ""

# ========================================
# 3. 代码覆盖率测试
# ========================================
echo -e "${YELLOW}[3/5] 运行覆盖率测试...${NC}"
$PYTHON_CMD -m pytest tests/unit/test_alpha_factors*.py \
    --cov=src/features/alpha_factors \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    || echo -e "${RED}覆盖率测试失败${NC}"

echo ""

# ========================================
# 4. 性能测试
# ========================================
echo -e "${YELLOW}[4/5] 运行性能测试...${NC}"
$PYTHON_CMD -m pytest tests/unit/test_alpha_factors_extended.py::TestPerformanceDeep \
    -v \
    --tb=short \
    || echo -e "${RED}性能测试失败${NC}"

echo ""

# ========================================
# 5. 数据质量测试
# ========================================
echo -e "${YELLOW}[5/5] 运行数据质量测试...${NC}"
$PYTHON_CMD -m pytest tests/unit/test_alpha_factors_extended.py::TestDataQuality \
    -v \
    --tb=short \
    || echo -e "${RED}数据质量测试失败${NC}"

echo ""

# ========================================
# 测试总结
# ========================================
echo "=========================================="
echo -e "${GREEN}测试完成！${NC}"
echo "=========================================="
echo ""
echo "查看详细覆盖率报告: htmlcov/index.html"
echo ""
echo "测试统计:"
echo "  - 基础测试: 46+ 用例"
echo "  - 扩展测试: 35+ 用例"
echo "  - 总计: 80+ 测试用例"
echo ""
