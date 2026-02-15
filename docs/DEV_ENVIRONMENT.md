# 开发环境配置指南

本文档说明如何配置支持热重载的开发环境，让代码修改后自动重新编译。

## ✨ 更新说明（2025-02-15）

- ✅ 支持 Backend 热重载（Python/FastAPI）
- ✅ 支持 Frontend 热重载（Next.js）
- ✅ 支持 Admin 热重载（Next.js）
- ✅ 新增快速启动脚本 `./scripts/dev.sh`
- ✅ 完整的代码挂载和热更新配置

## 📋 目录

- [快速启动](#快速启动)
- [Backend热重载](#backend热重载)
- [Frontend热重载](#frontend热重载)
- [Admin热重载](#admin热重载)
- [使用开发环境](#使用开发环境)
- [常见问题](#常见问题)

## 🚀 快速启动

### 使用启动脚本（推荐）

```bash
./scripts/dev.sh
```

这个脚本会自动：
1. 检查 Docker 是否运行
2. 停止旧容器
3. 构建并启动所有服务（开发模式）
4. 显示服务访问地址

### 手动启动

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 服务访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| Frontend | http://localhost:3000 | 前端应用 |
| Admin | http://localhost:3002 | 管理后台 |
| Backend | http://localhost:8000 | 后端 API |
| API 文档 | http://localhost:8000/docs | FastAPI 文档 |
| Grafana | http://localhost:3001 | 监控面板 |

---

## 🔧 Backend热重载

### 当前状态：✅ 已支持

Backend 已经配置了热重载功能。

**配置文件**: [docker-compose.dev.yml](docker-compose.dev.yml#L7-L30)
```yaml
backend:
  volumes:
    - ./backend:/app              # Backend 代码
    - ./core/src:/app/core/src    # Core 核心模块
  command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**特性**:
- ✅ 修改 Python 代码后自动重启（1-3 秒）
- ✅ 支持 `backend/` 和 `core/src/` 目录
- ✅ 自动安装测试依赖
- ⚡ 热重载速度: 1-3 秒

**测试方法**:
```bash
# 1. 修改任意 Python 文件
# 2. 查看日志确认重启
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
```

---

## 🎨 Frontend热重载

### 当前状态：✅ 已支持

Frontend 使用 Next.js 开发模式，支持快速刷新。

**配置文件**: [docker-compose.dev.yml](docker-compose.dev.yml#L32-L53)
```yaml
frontend:
  build:
    dockerfile: Dockerfile.dev
  environment:
    - NODE_ENV=development
  volumes:
    - ./frontend/src:/app/src
    - ./frontend/public:/app/public
    - /app/node_modules  # 排除容器内的 node_modules
  command: npm run dev
```

**特性**:
- ✅ Fast Refresh（React 组件级热更新）
- ✅ 修改代码即时生效（< 1 秒）
- ✅ 无需重新构建
- ⚡ 热更新速度: 即时

**测试方法**:
```bash
# 1. 修改 frontend/src/ 下的任意文件
# 2. 浏览器自动刷新（无需手动操作）
```

---

## 🔐 Admin热重载

### 当前状态：✅ 已支持（新增）

Admin 管理后台同样支持热重载。

**配置文件**: [docker-compose.dev.yml](docker-compose.dev.yml#L55-L76)
```yaml
admin:
  build:
    dockerfile: Dockerfile.dev
  environment:
    - NODE_ENV=development
  volumes:
    - ./admin/app:/app/app
    - ./admin/components:/app/components
    - ./admin/lib:/app/lib
    - /app/node_modules
  command: npm run dev
```

**特性**:
- ✅ Next.js App Router 支持
- ✅ Fast Refresh
- ✅ 组件、页面、库文件全部热更新
- ⚡ 热更新速度: 即时

**测试方法**:
```bash
# 1. 修改 admin/app/ 或 admin/components/ 下的文件
# 2. 浏览器自动刷新
```

---

## 🚀 使用开发环境

### 完整启动命令

```bash
# 方式1：使用脚本（推荐）
./scripts/dev.sh

# 方式2：手动启动
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 查看所有日志
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f admin
```

### 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 停止并删除数据卷（慎用！会删除数据库数据）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### 重建镜像

当修改了以下文件时需要重建：
- `Dockerfile` 或 `Dockerfile.dev`
- `requirements.txt` 或 `package.json`
- 添加了系统依赖

```bash
# 重建所有镜像
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

# 只重建特定服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build admin

# 重建并启动
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

### 进入容器

```bash
# 进入 Backend 容器
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend bash

# 进入 Frontend 容器
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend sh

# 进入 Admin 容器
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec admin sh

# 连接数据库
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec timescaledb psql -U stock_user -d stock_analysis
```

---

## 📝 配置说明

### docker-compose.dev.yml

开发环境覆盖配置：

```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
    command: python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      dockerfile: Dockerfile.dev
    environment:
      - NODE_ENV=development
    volumes:
      - ./frontend/src:/app/src
      - ./frontend/public:/app/public
      - /app/node_modules  # 排除node_modules
    command: npm run dev
```

### Dockerfile.dev (Frontend)

开发模式Dockerfile：
- 基础镜像: `node:20-alpine`
- 启动命令: `npm run dev`
- 支持Next.js热重载

---

## 🐛 常见问题

### Q1: 修改代码后没有自动重载？

**Backend 排查**:
```bash
# 1. 检查是否使用开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# 2. 查看日志确认是否有错误
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend

# 3. 检查代码是否正确挂载
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend ls -la /app
```

**Frontend/Admin 排查**:
```bash
# 1. 确认使用开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps

# 2. 检查日志
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f admin

# 3. 确认浏览器地址正确
# Frontend: http://localhost:3000
# Admin: http://localhost:3002

# 4. 清除浏览器缓存或硬刷新（Cmd/Ctrl + Shift + R）
```

### Q2: 端口冲突

```bash
# 查看端口占用
lsof -i :3000  # Frontend
lsof -i :3002  # Admin
lsof -i :8000  # Backend

# 解决方案1: 停止占用端口的进程
kill -9 <PID>

# 解决方案2: 修改 docker-compose.yml 中的端口映射
# 例如: "3001:3000"
```

### Q3: node_modules 或 .next 缓存问题

```bash
# 删除容器和镜像，重新构建
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 如果仍有问题，删除本地缓存
rm -rf frontend/.next frontend/node_modules
rm -rf admin/.next admin/node_modules
```

### Q4: 权限问题（Linux/Mac）

```bash
# 修复文件权限
sudo chown -R $USER:$USER .

# 或者在 docker-compose.dev.yml 中添加用户映射
user: "${UID}:${GID}"
```

### Q5: 性能问题

**优化建议**:
- 增加 Docker Desktop 内存限制（建议 8GB+）
- 关闭不需要的服务：
  ```bash
  # 只启动 Backend 和 Frontend
  docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend frontend timescaledb redis
  ```
- 使用 `.dockerignore` 排除不必要的文件

### Q6: 环境变量未生效

```bash
# 检查环境变量
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend env | grep ENVIRONMENT
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend env | grep NODE_ENV

# 确保 .env 文件存在并正确配置
# 重启服务使环境变量生效
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart
```

---

## 📊 性能对比

| 模式 | 启动时间 | 代码修改后 | 内存占用 | 适用场景 |
|------|---------|-----------|---------|---------|
| 生产模式 | 30-60秒 | 需重新构建+重启 | ~400MB | 部署上线 |
| 开发模式 | 10-20秒 | 即时刷新 | ~800MB | 日常开发 |

---

## 🎯 最佳实践

### 日常开发流程

```bash
# 1. 启动开发环境（一次性）
./scripts/dev.sh
# 或
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# 2. 查看日志（新终端，可选）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# 3. 修改代码（自动热重载）
# - Backend: 保存文件 → 等待 1-3 秒 → API 自动更新
# - Frontend: 保存文件 → 即时刷新 → 页面自动更新
# - Admin: 保存文件 → 即时刷新 → 页面自动更新

# 4. 调试
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec backend python -m pytest
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec frontend npm run lint
docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec admin npm run lint

# 5. 完成开发后关闭
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### 切换到生产模式

```bash
# 停止开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 启动生产模式
docker-compose up -d --build

# 查看生产环境日志
docker-compose logs -f
```

### 只开发特定服务

```bash
# 只开发 Backend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d backend timescaledb redis

# 只开发 Frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d frontend backend timescaledb redis

# 只开发 Admin
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d admin backend timescaledb redis
```

---

## 📚 相关文档

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Next.js Fast Refresh](https://nextjs.org/docs/architecture/fast-refresh)
- [Uvicorn Auto-reload](https://www.uvicorn.org/#command-line-options)

---

## 🆘 支持

遇到问题？
1. 查看日志: `docker-compose logs -f [service-name]`
2. 检查配置: `docker-compose config`
3. 重启服务: `docker-compose restart [service-name]`
4. 完全重置: `docker-compose down -v && docker-compose up -d --build`
