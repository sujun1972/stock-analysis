#!/bin/bash

# 启动管理后台开发服务器
# Usage: ./start-admin.sh

echo "🚀 启动股票分析系统 - 管理后台..."
echo ""

# 进入admin目录
cd "$(dirname "$0")/admin" || exit 1

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📦 检测到依赖未安装，正在安装..."
    npm install
fi

# 启动开发服务器
echo "✅ 启动Admin开发服务器 (端口: 3002)..."
npm run dev
