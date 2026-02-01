#!/bin/bash
# Sphinx API 文档构建脚本
# 用法: ./build.sh [--clean] [--rebuild-api]

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 项目路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$SCRIPT_DIR/../../venv/bin"
SRC_DIR="$SCRIPT_DIR/../../src"
SOURCE_DIR="$SCRIPT_DIR/source"
BUILD_DIR="$SCRIPT_DIR/build"
API_DIR="$SOURCE_DIR/api"

echo -e "${GREEN}=== Sphinx API 文档构建工具 ===${NC}"
echo "项目: Stock Analysis Core v3.0.0"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 解析参数
CLEAN=false
REBUILD_API=false

for arg in "$@"; do
    case $arg in
        --clean)
            CLEAN=true
            shift
            ;;
        --rebuild-api)
            REBUILD_API=true
            shift
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --clean        清理构建缓存"
            echo "  --rebuild-api  重新生成 API RST 文件"
            echo "  --help, -h     显示帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                        # 增量构建"
            echo "  $0 --clean                # 清理后重新构建"
            echo "  $0 --rebuild-api          # 重新生成 API 文档"
            echo "  $0 --clean --rebuild-api  # 完全重新构建"
            exit 0
            ;;
    esac
done

# 步骤 1: 清理 (可选)
if [ "$CLEAN" = true ]; then
    echo -e "${YELLOW}[1/4] 清理构建缓存...${NC}"
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
        echo "  ✓ 已清理 build/ 目录"
    fi
    if [ -d "$SOURCE_DIR/_build" ]; then
        rm -rf "$SOURCE_DIR/_build"
        echo "  ✓ 已清理 source/_build/ 目录"
    fi
else
    echo -e "${YELLOW}[1/4] 跳过清理 (使用 --clean 清理缓存)${NC}"
fi

# 步骤 2: 重新生成 API RST 文件 (可选)
if [ "$REBUILD_API" = true ] || [ ! -d "$API_DIR" ]; then
    echo -e "${YELLOW}[2/4] 生成 API RST 文件...${NC}"

    # 删除旧的 API 文档
    if [ -d "$API_DIR" ]; then
        rm -rf "$API_DIR"
        echo "  ✓ 已删除旧的 API 文档"
    fi

    # 运行 sphinx-apidoc
    "$VENV_BIN/sphinx-apidoc" -f -e -o "$API_DIR" "$SRC_DIR"

    # 统计生成的文件
    API_COUNT=$(find "$API_DIR" -name "*.rst" | wc -l | tr -d ' ')
    echo "  ✓ 已生成 $API_COUNT 个 RST 文件"
else
    echo -e "${YELLOW}[2/4] 跳过 API 生成 (使用 --rebuild-api 重新生成)${NC}"
fi

# 步骤 3: 构建 HTML 文档
echo -e "${YELLOW}[3/4] 构建 HTML 文档...${NC}"

# 记录开始时间
START_TIME=$(date +%s)

# 运行 sphinx-build
cd "$SCRIPT_DIR"
"$VENV_BIN/sphinx-build" -b html "$SOURCE_DIR" "$BUILD_DIR/html" 2>&1 | \
    grep -E "(writing output|build succeeded|WARNING|ERROR)" || true

# 计算耗时
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "  ✓ 构建完成 (耗时: ${DURATION}s)"

# 步骤 4: 统计信息
echo -e "${YELLOW}[4/4] 生成统计信息...${NC}"

# HTML 文件数量
HTML_COUNT=$(find "$BUILD_DIR/html" -name "*.html" | wc -l | tr -d ' ')
echo "  ✓ HTML 页面: $HTML_COUNT 个"

# 文档大小
DOC_SIZE=$(du -sh "$BUILD_DIR/html" | cut -f1)
echo "  ✓ 文档大小: $DOC_SIZE"

# 索引文件
INDEX_FILE="$BUILD_DIR/html/index.html"
if [ -f "$INDEX_FILE" ]; then
    INDEX_SIZE=$(ls -lh "$INDEX_FILE" | awk '{print $5}')
    echo "  ✓ 首页大小: $INDEX_SIZE"
fi

# 完成
echo ""
echo -e "${GREEN}✅ 构建成功!${NC}"
echo ""
echo "查看文档:"
echo -e "  ${GREEN}open $BUILD_DIR/html/index.html${NC}"
echo ""
echo "或启动本地服务器:"
echo -e "  ${GREEN}cd $BUILD_DIR/html && python -m http.server 8000${NC}"
echo -e "  然后访问: ${GREEN}http://localhost:8000${NC}"
echo ""
