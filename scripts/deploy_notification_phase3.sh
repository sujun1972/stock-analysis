#!/bin/bash

# ========================================
# 通知系统 Phase 3 部署脚本
# ========================================
# 描述: 自动执行 Phase 3 数据库迁移和服务重启
# 使用: bash scripts/deploy_notification_phase3.sh
# ========================================

set -e  # 遇到错误立即退出

echo "========================================="
echo "通知系统 Phase 3 部署开始"
echo "========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否运行
echo -e "\n${YELLOW}[1/5] 检查 Docker 环境...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${RED}错误: Docker 服务未运行，请先启动 docker-compose${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker 环境正常${NC}"

# 执行数据库迁移
echo -e "\n${YELLOW}[2/5] 执行数据库迁移...${NC}"
docker-compose exec -T timescaledb psql -U stock_user -d stock_analysis -f /docker-entrypoint-initdb.d/phase3_notification_monitoring_tasks.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 数据库迁移成功${NC}"
else
    echo -e "${RED}✗ 数据库迁移失败${NC}"
    exit 1
fi

# 验证定时任务配置
echo -e "\n${YELLOW}[3/5] 验证定时任务配置...${NC}"
TASK_COUNT=$(docker-compose exec -T timescaledb psql -U stock_user -d stock_analysis -t -c "SELECT COUNT(*) FROM scheduler_tasks WHERE name IN ('notification_health_check', 'cleanup_expired_notifications', 'reset_daily_rate_limits');" | tr -d ' ')

if [ "$TASK_COUNT" -eq "3" ]; then
    echo -e "${GREEN}✓ 定时任务配置验证成功（共 3 个任务）${NC}"
    docker-compose exec -T timescaledb psql -U stock_user -d stock_analysis -c "SELECT name, cron_expression, is_enabled FROM scheduler_tasks WHERE name IN ('notification_health_check', 'cleanup_expired_notifications', 'reset_daily_rate_limits') ORDER BY name;"
else
    echo -e "${RED}✗ 定时任务配置验证失败（预期 3 个，实际 $TASK_COUNT 个）${NC}"
    exit 1
fi

# 重启 Celery 服务
echo -e "\n${YELLOW}[4/5] 重启 Celery 服务...${NC}"
docker-compose restart celery_worker celery_beat

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Celery 服务重启成功${NC}"
    sleep 3
else
    echo -e "${RED}✗ Celery 服务重启失败${NC}"
    exit 1
fi

# 检查 Celery Beat 日志
echo -e "\n${YELLOW}[5/5] 检查 Celery Beat 日志...${NC}"
echo -e "${YELLOW}最近 30 行日志:${NC}"
docker-compose logs --tail=30 celery_beat | grep -E "(notification|beat|task)" || true

echo -e "\n========================================="
echo -e "${GREEN}✓ Phase 3 部署完成！${NC}"
echo "========================================="

echo -e "\n${YELLOW}后续步骤:${NC}"
echo "1. 访问 Admin 后台: http://localhost:3002"
echo "2. 导航到"监控" → "通知系统监控""
echo "3. 查看实时监控数据"
echo ""
echo "定时任务列表:"
echo "  • notification_health_check    - 每小时执行健康检查"
echo "  • cleanup_expired_notifications - 每天凌晨 2:00 清理过期消息"
echo "  • reset_daily_rate_limits      - 每天凌晨 0:00 重置频率限制"
echo ""
echo -e "${GREEN}部署成功！${NC}"
