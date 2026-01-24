#!/bin/bash
# 快速验证自动化实验系统是否正常工作

echo "========================================="
echo "自动化实验系统 - 快速验证"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. 检查数据库表
echo "1. 检查数据库表..."
docker exec stock_backend python -c "
import sys
sys.path.insert(0, '/app/src')
from database.db_manager import DatabaseManager
db = DatabaseManager()
result = db._execute_query(
    \"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'experiment%' ORDER BY table_name\"
)
print('找到的表:')
for row in result:
    print(f'  ✓ {row[0]}')
" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 数据库表检查通过${NC}"
else
    echo -e "${RED}✗ 数据库表检查失败${NC}"
    exit 1
fi
echo ""

# 2. 检查API端点
echo "2. 检查API端点..."
http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/experiment/templates)
if [ "$http_code" -eq "200" ]; then
    echo -e "${GREEN}✓ API端点正常 (HTTP $http_code)${NC}"
else
    echo -e "${RED}✗ API端点异常 (HTTP $http_code)${NC}"
    exit 1
fi
echo ""

# 3. 检查CLI工具
echo "3. 检查CLI工具..."
docker exec stock_backend python scripts/experiment_cli.py --help > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CLI工具可用${NC}"
else
    echo -e "${RED}✗ CLI工具不可用${NC}"
    exit 1
fi
echo ""

# 4. 列出现有批次
echo "4. 列出现有批次..."
docker exec stock_backend python scripts/experiment_cli.py list 2>/dev/null
echo ""

# 5. 显示可用模板
echo "5. 可用的实验模板:"
echo "  • minimal_test  - 1个实验（验证流程，10分钟）"
echo "  • small_grid    - ~100个实验（初步探索，2-4小时）"
echo "  • medium_grid   - ~500个实验（全面评估，1-2天）"
echo "  • large_random  - 1000+实验（大规模搜索，2-3天）"
echo ""

# 6. 显示快速开始命令
echo "========================================="
echo "快速开始命令："
echo "========================================="
echo ""
echo -e "${YELLOW}# 创建测试批次（推荐第一次使用）${NC}"
echo "docker exec stock_backend python scripts/experiment_cli.py create \\"
echo "  --name \"快速测试\" \\"
echo "  --template minimal \\"
echo "  --workers 1"
echo ""
echo -e "${YELLOW}# 创建小规模批次${NC}"
echo "docker exec stock_backend python scripts/experiment_cli.py create \\"
echo "  --name \"Grid搜索v1\" \\"
echo "  --template small \\"
echo "  --workers 3"
echo ""
echo -e "${YELLOW}# 查看批次状态${NC}"
echo "docker exec stock_backend python scripts/experiment_cli.py status --batch-id 1"
echo ""
echo -e "${YELLOW}# 显示Top模型${NC}"
echo "docker exec stock_backend python scripts/experiment_cli.py top --batch-id 1"
echo ""
echo -e "${YELLOW}# Web界面${NC}"
echo "http://localhost:3000/auto-experiment"
echo ""
echo -e "${YELLOW}# API文档${NC}"
echo "http://localhost:8000/api/docs"
echo ""

echo "========================================="
echo -e "${GREEN}✓ 所有检查通过！系统可以使用${NC}"
echo "========================================="
