# 开发环境配置指南

本文档说明如何配置支持热重载的开发环境，让代码修改后自动重新编译。

## 📋 目录

- [Backend热重载（已支持）](#backend热重载)
- [Frontend热重载（新增）](#frontend热重载)
- [使用开发环境](#使用开发环境)
- [常见问题](#常见问题)

## 🔧 Backend热重载

### 当前状态：✅ 已支持

Backend已经配置了热重载功能：

**配置文件**: `docker-compose.yml`
```yaml
backend:
  volumes:
    - ./backend:/app          # 代码挂载
    - ./core/src:/app/src     # 核心代码挂载
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**特性**:
- ✅ 修改Python代码后自动重启
- ✅ 修改`backend/`目录下的任何文件都会触发重载
- ✅ 修改`core/src/`目录下的代码也会触发重载
- ⚡ 重启速度: 1-3秒

**测试方法**:
```bash
# 1. 修改任意Python文件，如 backend/app/api/endpoints/stocks.py
# 2. 查看日志，应该看到 "Application startup complete"
docker-compose logs -f backend
```

---

## 🎨 Frontend热重载

### 当前状态：⚠️ 生产模式（需切换到开发模式）

Frontend目前使用生产构建模式，需要切换到开发模式以支持热重载。

### 方案1：使用开发环境配置文件（推荐）

**步骤**:

1. **停止当前服务**:
   ```bash
   docker-compose down
   ```

2. **使用开发模式启动**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

3. **查看日志**:
   ```bash
   docker-compose logs -f frontend
   ```

**特性**:
- ✅ 修改`frontend/src/`下的代码自动热重载
- ✅ Fast Refresh支持（React组件级热更新）
- ⚡ 更新速度: 即时（通常<1秒）
- 📦 不需要重新构建整个应用

**测试方法**:
```bash
# 1. 修改任意React组件，如 frontend/src/app/page.tsx
# 2. 浏览器自动刷新，无需手动操作
```

### 方案2：只启动Frontend开发模式

如果只需要开发Frontend：

```bash
# 1. 确保Backend在运行
docker-compose up -d backend timescaledb

# 2. 启动Frontend开发模式
docker-compose -f docker-compose.dev.yml up frontend
```

---

## 🚀 使用开发环境

### 完整启动命令

```bash
# 启动所有服务（开发模式）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 查看所有日志
docker-compose logs -f

# 只查看Frontend日志
docker-compose logs -f frontend

# 只查看Backend日志
docker-compose logs -f backend
```

### 停止服务

```bash
# 停止所有服务
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 停止并删除数据卷（慎用）
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

### 重建镜像

当修改了Dockerfile或package.json后，需要重建镜像：

```bash
# 重建所有镜像
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

# 只重建Frontend
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build frontend

# 重建并启动
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
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

### Q1: Frontend修改后没有自动刷新？

**检查项**:
1. 确认使用了开发模式启动:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml ps
   ```

2. 检查Frontend日志:
   ```bash
   docker-compose logs frontend | grep "ready"
   ```

3. 确认浏览器地址是`http://localhost:3000`

### Q2: Backend修改后没有重启？

**检查项**:
1. 确认代码卷挂载正确:
   ```bash
   docker-compose exec backend ls -la /app
   ```

2. 检查Backend日志是否有错误:
   ```bash
   docker-compose logs backend
   ```

### Q3: 端口冲突？

如果端口已被占用：

```bash
# 查看端口占用
lsof -i :3000
lsof -i :8000

# 修改docker-compose.yml中的端口映射
# 例如: "3001:3000" 或 "8001:8000"
```

### Q4: 性能问题？

开发模式会占用更多资源：

**优化建议**:
- 增加Docker Desktop的内存限制（建议8GB+）
- 关闭不需要的服务
- 使用`.dockerignore`排除不必要的文件

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
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 2. 查看日志（新终端）
docker-compose logs -f

# 3. 修改代码（自动热重载）
# - Backend: 保存文件 → 等待1-3秒 → API自动更新
# - Frontend: 保存文件 → 即时刷新 → 页面自动更新

# 4. 调试
docker-compose exec backend python -c "print('test')"
docker-compose exec frontend npm run lint

# 5. 完成开发后关闭
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

### 切换到生产模式

```bash
# 停止开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# 启动生产模式
docker-compose up -d

# 查看生产环境日志
docker-compose logs -f
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
