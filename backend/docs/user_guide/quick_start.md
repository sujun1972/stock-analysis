# 快速开始指南

**版本**: v1.0.0
**最后更新**: 2026-02-01

---

## 概述

本指南将帮助你在 **15 分钟内**完成 Backend 服务的启动和基本使用。

---

## 前置要求

### 必需

- **Docker** 和 **Docker Compose** 已安装
- **8GB+** 内存
- **10GB+** 磁盘空间

### 可选

- Python 3.9+ （本地开发）
- PostgreSQL 客户端（数据库查询）

---

## 步骤 1: 启动服务 (2 分钟)

### 使用 Docker Compose（推荐）

```bash
# 1. 进入项目根目录
cd /Volumes/MacDriver/stock-analysis

# 2. 启动所有服务（Backend + TimescaleDB）
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 检查服务状态
docker-compose ps
```

#### 预期输出

```
NAME                IMAGE               STATUS
timescaledb         timescale/...       Up 30 seconds
backend             stock-backend       Up 20 seconds
```

### 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 预期输出
{
  "status": "healthy",
  "environment": "development"
}
```

---

## 步骤 2: 访问 API 文档 (1 分钟)

打开浏览器访问：

**Swagger UI**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)

你将看到完整的 API 文档，包括：
- 13 个功能模块
- 60+ API 端点
- 交互式测试界面

---

## 步骤 3: 下载股票数据 (3 分钟)

### 方法 1: 使用 Swagger UI（推荐新手）

1. 打开 [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
2. 找到 **POST /api/data/download**
3. 点击 "Try it out"
4. 输入请求参数：

```json
{
  "stock_code": "000001.SZ",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

5. 点击 "Execute"
6. 查看响应结果

### 方法 2: 使用 cURL

```bash
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'
```

#### 预期响应

```json
{
  "status": "success",
  "data": {
    "task_id": "abc123",
    "stock_code": "000001.SZ",
    "message": "数据下载成功"
  }
}
```

### 方法 3: 使用 Python

```python
import httpx
import asyncio

async def download_data():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/data/download",
            json={
                "stock_code": "000001.SZ",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )
        print(response.json())

asyncio.run(download_data())
```

---

## 步骤 4: 查询股票数据 (1 分钟)

```bash
# 查询日线数据
curl http://localhost:8000/api/data/daily/000001.SZ?start_date=2024-01-01&end_date=2024-01-31
```

#### 预期响应

```json
{
  "status": "success",
  "data": [
    {
      "code": "000001.SZ",
      "trade_date": "2024-01-02",
      "open": 12.50,
      "high": 12.80,
      "low": 12.45,
      "close": 12.75,
      "volume": 12345678
    },
    ...
  ]
}
```

---

## 步骤 5: 计算特征 (2 分钟)

### 计算 Alpha 因子

```bash
curl -X POST http://localhost:8000/api/features/calculate/000001.SZ \
  -H "Content-Type: application/json" \
  -d '{
    "feature_types": ["momentum", "reversal", "volatility"]
  }'
```

#### 预期响应

```json
{
  "status": "success",
  "data": {
    "stock_code": "000001.SZ",
    "features_calculated": 45,
    "feature_names": [
      "MOM_5", "MOM_10", "MOM_20",
      "REV_5", "REV_10",
      "VOL_20", "VOL_60",
      ...
    ]
  }
}
```

### 查询特征数据

```bash
curl http://localhost:8000/api/features/000001.SZ?start_date=2024-01-01&end_date=2024-01-31
```

---

## 步骤 6: 运行回测 (3 分钟)

### 使用动量策略回测

```bash
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy": "momentum",
    "initial_capital": 1000000,
    "strategy_params": {
      "lookback_period": 20,
      "buy_threshold": 0.02,
      "sell_threshold": -0.02
    }
  }'
```

#### 预期响应

```json
{
  "status": "success",
  "data": {
    "total_return": 0.253,
    "annual_return": 0.187,
    "sharpe_ratio": 1.85,
    "max_drawdown": -0.125,
    "win_rate": 0.58,
    "total_trades": 24,
    "profitable_trades": 14,
    "losing_trades": 10,
    "final_value": 1253000,
    "benchmark_return": 0.12
  }
}
```

---

## 步骤 7: 训练机器学习模型 (3 分钟)

### 启动训练任务

```bash
curl -X POST http://localhost:8000/api/ml/train/single \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "model_type": "lightgbm",
    "target": "return_5d",
    "features": ["MOM_20", "VOL_20", "RSI_14", "MACD"],
    "train_start": "2023-01-01",
    "train_end": "2024-06-30",
    "test_start": "2024-07-01",
    "test_end": "2024-12-31"
  }'
```

#### 预期响应

```json
{
  "status": "success",
  "data": {
    "task_id": "train_xyz789",
    "message": "训练任务已创建"
  }
}
```

### 查询训练状态

```bash
curl http://localhost:8000/api/ml/train/status/train_xyz789
```

#### 预期响应

```json
{
  "status": "success",
  "data": {
    "task_id": "train_xyz789",
    "status": "completed",
    "progress": 100,
    "metrics": {
      "train_r2": 0.65,
      "test_r2": 0.58,
      "train_ic": 0.08,
      "test_ic": 0.06
    },
    "model_path": "/models/lightgbm_000001_20260201.pkl"
  }
}
```

---

## 常用操作

### 获取股票列表

```bash
# 获取所有股票
curl http://localhost:8000/api/stocks/list

# 分页查询
curl "http://localhost:8000/api/stocks/list?page=1&page_size=50"
```

### 获取策略列表

```bash
curl http://localhost:8000/api/strategy/list
```

#### 预期响应

```json
{
  "status": "success",
  "data": [
    {
      "name": "momentum",
      "description": "动量策略",
      "parameters": {
        "lookback_period": "回看周期（天）",
        "buy_threshold": "买入阈值",
        "sell_threshold": "卖出阈值"
      }
    },
    {
      "name": "mean_reversion",
      "description": "均值回归策略",
      "parameters": {
        "lookback_period": "回看周期（天）",
        "std_multiplier": "标准差倍数"
      }
    }
  ]
}
```

### 检查是否交易日

```bash
curl "http://localhost:8000/api/market/is_trading_day?date=2024-02-01"
```

### 启动数据同步

```bash
# 同步所有股票的最新数据
curl -X POST http://localhost:8000/api/sync/start
```

### 创建定时任务

```bash
curl -X POST http://localhost:8000/api/scheduler/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "daily_sync",
    "trigger": "cron",
    "hour": 18,
    "minute": 0,
    "task": "sync_daily_data"
  }'
```

---

## 故障排查

### 问题 1: 服务无法启动

**症状**: `docker-compose up` 失败

**解决方案**:

```bash
# 查看详细日志
docker-compose logs backend

# 重启服务
docker-compose restart backend

# 重新构建镜像
docker-compose build backend --no-cache
docker-compose up -d
```

### 问题 2: 数据库连接失败

**症状**: API 返回 "Database connection failed"

**解决方案**:

```bash
# 检查 TimescaleDB 是否运行
docker-compose ps timescaledb

# 重启数据库
docker-compose restart timescaledb

# 检查数据库日志
docker-compose logs timescaledb
```

### 问题 3: 下载数据失败

**症状**: 下载接口返回错误

**解决方案**:

1. 检查网络连接
2. 确认股票代码格式正确（例如：`000001.SZ`）
3. 检查日期范围是否有效
4. 查看 Backend 日志：`docker-compose logs backend`

### 问题 4: 端口被占用

**症状**: "Address already in use"

**解决方案**:

```bash
# 查找占用 8000 端口的进程
lsof -i:8000

# 杀死进程
kill -9 <PID>

# 或修改 docker-compose.yml 中的端口映射
ports:
  - "8001:8000"  # 改为 8001
```

---

## 下一步

恭喜！你已经完成了 Backend 的快速开始。

### 进阶学习

- 📚 [API 参考文档](../api_reference/README.md) - 了解所有 API 端点
- 🎨 [架构文档](../architecture/overview.md) - 深入理解系统架构
- 🔧 [开发指南](../developer_guide/contributing.md) - 参与开发
- 🚀 [部署文档](../deployment/docker.md) - 生产环境部署

### 实战示例

- [完整交易工作流](./examples/complete_workflow.md) - 从数据到回测的完整流程
- [批量回测示例](./examples/batch_backtest.md) - 批量测试多个策略
- [自动化实验](./examples/auto_experiment.md) - 使用实验管理器

---

## 获取帮助

### 文档

- 📖 [常见问题](./faq.md)
- 📚 [API 文档](http://localhost:8000/api/docs)

### 社区

- 💬 GitHub Issues
- 📧 技术支持邮箱

---

**维护团队**: Quant Team
**文档版本**: v1.0.0
**最后更新**: 2026-02-01
