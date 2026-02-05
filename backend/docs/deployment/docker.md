# Docker 部署指南

**版本**: v1.0.0
**最后更新**: 2026-02-01

---

## 概述

本指南介绍如何使用 Docker 和 Docker Compose 部署 Backend 服务。

---

## 快速部署

### 开发环境

```bash
# 1. 克隆项目
git clone https://github.com/your-org/stock-analysis.git
cd stock-analysis

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 访问服务
open http://localhost:8000/api/docs
```

### 生产环境

```bash
# 1. 使用生产配置
docker-compose -f docker-compose.prod.yml up -d

# 2. 查看状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f
```

---

## Docker Compose 配置

### 开发环境配置

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    container_name: timescaledb
    environment:
      POSTGRES_DB: stock_analysis
      POSTGRES_USER: stock_user
      POSTGRES_PASSWORD: stock_password_123
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stock_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: backend
    depends_on:
      timescaledb:
        condition: service_healthy
    environment:
      - ENVIRONMENT=development
      - DATABASE_HOST=timescaledb
      - DATABASE_PORT=5432
      - DATABASE_NAME=stock_analysis
      - DATABASE_USER=stock_user
      - DATABASE_PASSWORD=stock_password_123
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./core/src:/app/src
      - ./data:/data
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    restart: unless-stopped

volumes:
  timescale_data:
```

### 生产环境配置

`docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    container_name: timescaledb_prod
    environment:
      POSTGRES_DB: stock_analysis
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "5432:5432"
    volumes:
      - timescale_data_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: always

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: backend_prod
    depends_on:
      timescaledb:
        condition: service_healthy
    environment:
      - ENVIRONMENT=production
      - DATABASE_HOST=timescaledb
      - DATABASE_PORT=5432
      - DATABASE_NAME=stock_analysis
      - DATABASE_USER=${DB_USER}
      - DATABASE_PASSWORD=${DB_PASSWORD}
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
      - SECRET_KEY=${SECRET_KEY}
    ports:
      - "8000:8000"
    volumes:
      - ./data:/data
      - ./logs:/app/logs
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

volumes:
  timescale_data_prod:
```

---

## Dockerfile

### 开发环境 Dockerfile

`backend/Dockerfile`:

```dockerfile
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 生产环境 Dockerfile

`backend/Dockerfile.prod`:

```dockerfile
FROM python:3.9-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 最终镜像
FROM python:3.9-slim

WORKDIR /app

# 从 builder 复制依赖
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 复制应用代码
COPY --chown=appuser:appuser . .

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## 环境变量

### .env 文件

创建 `.env` 文件配置环境变量：

```bash
# 环境配置（development/testing/production）
ENVIRONMENT=production

# 数据库配置
DATABASE_HOST=timescaledb
DATABASE_PORT=5432
DATABASE_NAME=stock_analysis
DATABASE_USER=stock_user
DATABASE_PASSWORD=your_secure_password_here

# Redis 配置
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_redis_password_here
REDIS_ENABLED=true

# 缓存配置（秒）
CACHE_DEFAULT_TTL=300
CACHE_STOCK_LIST_TTL=300
CACHE_DAILY_DATA_TTL=3600
CACHE_FEATURES_TTL=1800
CACHE_BACKTEST_TTL=86400
CACHE_MARKET_STATUS_TTL=60

# 日志配置
LOG_LEVEL=INFO  # 生产环境建议 INFO，开发环境 DEBUG

# API 密钥
TUSHARE_TOKEN=your_tushare_token_here
DATA_SOURCE=akshare  # akshare 或 tushare

# 安全密钥
SECRET_KEY=your_secret_key_here

# CORS 配置
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

### 环境配置说明

系统支持三种环境模式：

1. **development**: 开发环境
   - 日志级别: DEBUG
   - 启用代码热重载
   - 控制台彩色日志输出
   - 允许本地跨域访问

2. **testing**: 测试环境
   - 日志级别: WARNING
   - 禁用部分外部服务调用
   - 使用测试数据库

3. **production**: 生产环境
   - 日志级别: INFO
   - 启用多 worker 进程
   - JSON 结构化日志
   - 严格的 CORS 策略
   - 资源限制和监控

### 安全注意事项

⚠️ **重要**:

- 不要将 `.env` 文件提交到版本控制
- 生产环境使用强密码
- 定期轮换密钥
- 使用密钥管理服务（如 AWS Secrets Manager）

---

## 容器管理

### 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 启动特定服务
docker-compose up -d backend

# 重新构建并启动
docker-compose up -d --build
```

### 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷
docker-compose down -v

# 停止特定服务
docker-compose stop backend
```

### 查看日志

```bash
# 查看所有日志
docker-compose logs

# 实时查看日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend

# 查看最近 100 行日志
docker-compose logs --tail=100 backend
```

### 进入容器

```bash
# 进入 backend 容器
docker-compose exec backend bash

# 进入数据库容器
docker-compose exec timescaledb psql -U stock_user -d stock_analysis
```

### 重启服务

```bash
# 重启所有服务
docker-compose restart

# 重启特定服务
docker-compose restart backend
```

---

## 数据持久化

### 数据卷

Docker Compose 自动创建数据卷：

```bash
# 查看数据卷
docker volume ls

# 查看数据卷详情
docker volume inspect stock-analysis_timescale_data

# 备份数据卷
docker run --rm -v stock-analysis_timescale_data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/timescale_backup_$(date +%Y%m%d).tar.gz /data
```

### 数据库备份

```bash
# 备份数据库
docker-compose exec timescaledb pg_dump -U stock_user stock_analysis > backup.sql

# 恢复数据库
docker-compose exec -T timescaledb psql -U stock_user stock_analysis < backup.sql
```

---

## 性能优化

### 1. 多 Worker 配置

生产环境使用多个 worker：

```bash
# 推荐：CPU 核心数 * 2 + 1
uvicorn app.main:app --workers 4
```

### 2. 资源限制

在 `docker-compose.yml` 中设置资源限制：

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 2G
```

### 3. 日志轮转

配置日志轮转避免磁盘占满：

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 监控与健康检查

### 健康检查端点

Backend 提供全面的健康检查端点，检查所有关键服务的状态：

```bash
curl http://localhost:8000/health

# 健康状态（HTTP 200）
{
  "status": "healthy",
  "environment": "production",
  "checks": {
    "database": true,
    "redis": true,
    "core": true
  },
  "circuit_breakers": {
    "database": "closed",
    "external_api": "closed"
  },
  "version": "1.0.0"
}

# 不健康状态（HTTP 503）
{
  "status": "unhealthy",
  "environment": "production",
  "checks": {
    "database": false,
    "redis": true,
    "core": true
  },
  "circuit_breakers": {
    "database": "open",
    "external_api": "closed"
  },
  "version": "1.0.0"
}
```

### Docker 健康检查

在 Dockerfile 中配置：

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 容器状态监控

```bash
# 查看容器状态
docker-compose ps

# 查看资源使用
docker stats

# 查看特定容器资源
docker stats backend
```

---

## 生产部署最佳实践

### 1. 使用反向代理

推荐使用 Nginx 作为反向代理：

`nginx.conf`:

```nginx
upstream backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # SSL 配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 启用 HTTPS

使用 Let's Encrypt 获取免费 SSL 证书：

```bash
# 安装 certbot
sudo apt-get install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d api.yourdomain.com

# 自动续期
sudo certbot renew --dry-run
```

### 3. 配置防火墙

```bash
# 仅开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 4. 定期备份

设置定时备份任务：

```bash
# 创建备份脚本
cat > /opt/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
docker-compose exec -T timescaledb pg_dump -U stock_user stock_analysis > \
  $BACKUP_DIR/db_backup_$DATE.sql

# 备份数据卷
docker run --rm -v stock-analysis_timescale_data:/data -v $BACKUP_DIR:/backup \
  ubuntu tar czf /backup/volume_backup_$DATE.tar.gz /data

# 删除 7 天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x /opt/backup.sh

# 添加定时任务（每天凌晨 2 点）
echo "0 2 * * * /opt/backup.sh" | crontab -
```

### 5. 监控告警

使用 Prometheus + Grafana 监控：

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

---

## 故障排查

### 问题 1: 容器无法启动

```bash
# 查看详细日志
docker-compose logs backend

# 检查配置
docker-compose config

# 重新构建
docker-compose build --no-cache backend
```

### 问题 2: 数据库连接失败

```bash
# 检查数据库是否运行
docker-compose ps timescaledb

# 测试数据库连接
docker-compose exec timescaledb psql -U stock_user -d stock_analysis

# 检查网络
docker network ls
docker network inspect stock-analysis_default
```

### 问题 3: 磁盘空间不足

```bash
# 清理未使用的镜像
docker image prune -a

# 清理未使用的容器
docker container prune

# 清理未使用的数据卷
docker volume prune

# 查看磁盘使用
docker system df
```

### 问题 4: 性能问题

```bash
# 查看资源使用
docker stats

# 增加资源限制
# 编辑 docker-compose.yml
deploy:
  resources:
    limits:
      memory: 8G
```

---

## 升级指南

### 滚动升级

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 备份数据
./backup.sh

# 3. 重新构建镜像
docker-compose build backend

# 4. 滚动重启
docker-compose up -d --no-deps --build backend

# 5. 验证服务
curl http://localhost:8000/health
```

### 回滚

```bash
# 1. 切换到旧版本
git checkout v1.0.0

# 2. 重新构建
docker-compose build backend

# 3. 重启服务
docker-compose up -d backend

# 4. 恢复数据库（如需要）
docker-compose exec -T timescaledb psql -U stock_user stock_analysis < backup.sql
```

---

## 相关文档

- [快速开始](../user_guide/quick_start.md)
- [架构文档](../architecture/overview.md)
- [API 参考](../api_reference/README.md)

---

**维护团队**: Quant Team
**文档版本**: v1.0.0
**最后更新**: 2026-02-01
