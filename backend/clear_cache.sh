#!/bin/bash

#######################################################
# 清理 Python 缓存文件
#
# 用途: 修改代码后测试仍使用旧代码时运行此脚本
#
# 用法:
#   ./clear_cache.sh              # 清理所有缓存
#   ./clear_cache.sh --dry-run    # 查看将删除的文件但不实际删除
#
# 作者: Backend Team
# 创建日期: 2026-02-05
#######################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录（backend目录）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  清理 Python 缓存文件${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否为 dry-run 模式
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}[Dry Run 模式] 仅显示将删除的文件，不实际删除${NC}"
    echo ""
fi

# 统计变量
total_dirs=0
total_files=0

# 查找并处理 __pycache__ 目录
echo -e "${YELLOW}正在查找 __pycache__ 目录...${NC}"
while IFS= read -r dir; do
    if [[ $DRY_RUN == true ]]; then
        echo "  将删除: $dir"
    else
        rm -rf "$dir"
        echo "  已删除: $dir"
    fi
    ((total_dirs++))
done < <(find "$SCRIPT_DIR" -type d -name "__pycache__" 2>/dev/null)

# 查找并处理 .pyc 文件
echo ""
echo -e "${YELLOW}正在查找 .pyc 文件...${NC}"
while IFS= read -r file; do
    if [[ $DRY_RUN == true ]]; then
        echo "  将删除: $file"
    else
        rm -f "$file"
        echo "  已删除: $file"
    fi
    ((total_files++))
done < <(find "$SCRIPT_DIR" -type f -name "*.pyc" 2>/dev/null)

# 查找并处理 .pyo 文件（优化的字节码）
echo ""
echo -e "${YELLOW}正在查找 .pyo 文件...${NC}"
while IFS= read -r file; do
    if [[ $DRY_RUN == true ]]; then
        echo "  将删除: $file"
    else
        rm -f "$file"
        echo "  已删除: $file"
    fi
    ((total_files++))
done < <(find "$SCRIPT_DIR" -type f -name "*.pyo" 2>/dev/null)

# 显示统计信息
echo ""
echo -e "${GREEN}========================================${NC}"
if [[ $DRY_RUN == true ]]; then
    echo -e "${GREEN}[Dry Run] 发现:${NC}"
    echo -e "  __pycache__ 目录: ${total_dirs}"
    echo -e "  .pyc/.pyo 文件: ${total_files}"
    echo ""
    echo -e "${YELLOW}运行 ./clear_cache.sh 来实际删除这些文件${NC}"
else
    echo -e "${GREEN}✓ 清理完成!${NC}"
    echo -e "  已删除 __pycache__ 目录: ${total_dirs}"
    echo -e "  已删除 .pyc/.pyo 文件: ${total_files}"
fi
echo -e "${GREEN}========================================${NC}"
