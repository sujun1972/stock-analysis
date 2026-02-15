#!/bin/bash
# 开发环境启动脚本
# 支持前后端代码热重载

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  启动开发环境 (支持热重载)${NC}"
echo -e "${GREEN}================================${NC}"

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}错误: Docker 未运行，请先启动 Docker${NC}"
    exit 1
fi

# 停止并移除旧容器
echo -e "${YELLOW}停止旧容器...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 构建并启动服务
echo -e "${YELLOW}构建并启动服务...${NC}"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 等待服务启动
echo -e "${YELLOW}等待服务启动...${NC}"
sleep 5

# 显示日志
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  服务已启动！${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Frontend:  ${GREEN}http://localhost:3000${NC}"
echo -e "Admin:     ${GREEN}http://localhost:3002${NC}"
echo -e "Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "Grafana:   ${GREEN}http://localhost:3001${NC} (admin/admin123)"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${YELLOW}查看日志:${NC}"
echo "  docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f [service_name]"
echo ""
echo -e "${YELLOW}停止服务:${NC}"
echo "  docker-compose -f docker-compose.yml -f docker-compose.dev.yml down"
echo ""
echo -e "${GREEN}代码修改会自动触发热重载！${NC}"
