#!/bin/bash

# 开发环境启动脚本
# 用途：一键启动支持热重载的开发环境

set -e

echo "🚀 启动Stock Analysis开发环境..."
echo ""

# 检查Docker是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ 错误: Docker未运行，请先启动Docker Desktop"
    exit 1
fi

echo "✅ Docker正在运行"
echo ""

# 停止旧的服务
echo "📦 停止旧的服务..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down 2>/dev/null || true
echo ""

# 启动开发环境
echo "🔨 启动开发环境（支持热重载）..."
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
echo ""

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5
echo ""

# 显示服务状态
echo "📊 服务状态:"
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
echo ""

# 显示访问地址
echo "🎉 开发环境启动成功！"
echo ""
echo "📱 访问地址:"
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API文档:   http://localhost:8000/api/docs"
echo ""
echo "📝 查看日志:"
echo "  所有服务:  docker-compose logs -f"
echo "  Frontend:  docker-compose logs -f frontend"
echo "  Backend:   docker-compose logs -f backend"
echo ""
echo "🔥 热重载已启用:"
echo "  ✅ Backend:  修改Python代码自动重启（1-3秒）"
echo "  ✅ Frontend: 修改React代码即时刷新（<1秒）"
echo ""
echo "🛑 停止服务:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.dev.yml down"
echo ""
