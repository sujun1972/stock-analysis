# API 参考文档

**版本**: v1.0.0
**最后更新**: 2026-02-01

---

## API 概览

Backend 提供完整的 RESTful API 服务，涵盖股票数据管理、特征工程、模型训练、回测分析等核心功能。

### 自动文档

启动服务后，可以通过以下 URL 访问自动生成的 API 文档：

- **Swagger UI**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)
- **ReDoc**: [http://localhost:8000/api/redoc](http://localhost:8000/api/redoc)
- **OpenAPI JSON**: [http://localhost:8000/api/openapi.json](http://localhost:8000/api/openapi.json)

### 基础信息

**Base URL**: `http://localhost:8000/api`

**响应格式**: JSON

**字符编码**: UTF-8

---

## API 分类

### 1. 基础端点

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `/` | 服务根路径 | - |
| `/health` | 健康检查 | - |

### 2. 股票管理 (`/api/stocks`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /list` | 获取股票列表 | [详细](stocks.md#get-list) |
| `GET /{code}` | 获取单只股票信息 | [详细](stocks.md#get-code) |
| `POST /update` | 更新股票列表 | [详细](stocks.md#post-update) |
| `POST /update/status` | 检查更新状态 | [详细](stocks.md#post-update-status) |

### 3. 数据管理 (`/api/data`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /daily/{code}` | 获取日线数据 | [详细](data.md#get-daily) |
| `POST /download` | 下载股票数据 | [详细](data.md#post-download) |
| `GET /download/status/{task_id}` | 查询下载状态 | [详细](data.md#get-download-status) |

### 4. 特征工程 (`/api/features`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /{code}` | 获取特征数据 | [详细](features.md#get-features) |
| `POST /calculate/{code}` | 计算特征 | [详细](features.md#post-calculate) |
| `GET /list` | 获取可用特征列表 | [详细](features.md#get-list) |

### 5. 模型管理 (`/api/models`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `POST /train` | 训练模型 | [详细](models.md#post-train) |
| `GET /predict/{code}` | 获取预测结果 | [详细](models.md#get-predict) |
| `GET /evaluation/{model_name}` | 获取模型评估 | [详细](models.md#get-evaluation) |
| `GET /list` | 获取模型列表 | [详细](models.md#get-list) |

### 6. 回测引擎 (`/api/backtest`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `POST /run` | 运行回测 | [详细](backtest.md#post-run) |
| `GET /result/{task_id}` | 获取回测结果 | [详细](backtest.md#get-result) |
| `GET /history` | 获取历史回测 | [详细](backtest.md#get-history) |

### 7. 机器学习 (`/api/ml`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `POST /train/single` | 单次训练 | [详细](ml.md#post-train-single) |
| `POST /train/batch` | 批量训练 | [详细](ml.md#post-train-batch) |
| `GET /train/status/{task_id}` | 查询训练状态 | [详细](ml.md#get-train-status) |
| `GET /models/{model_id}` | 获取模型详情 | [详细](ml.md#get-model) |
| `POST /predict` | 模型预测 | [详细](ml.md#post-predict) |

### 8. 策略管理 (`/api/strategy`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /list` | 获取策略列表 | [详细](strategy.md#get-list) |
| `GET /{strategy_name}` | 获取策略详情 | [详细](strategy.md#get-strategy) |
| `POST /test` | 测试策略信号 | [详细](strategy.md#post-test) |

### 9. 数据同步 (`/api/sync`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `POST /start` | 启动同步 | [详细](sync.md#post-start) |
| `GET /status` | 获取同步状态 | [详细](sync.md#get-status) |
| `POST /stop` | 停止同步 | [详细](sync.md#post-stop) |

### 10. 定时任务 (`/api/scheduler`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /jobs` | 获取任务列表 | [详细](scheduler.md#get-jobs) |
| `POST /jobs` | 创建定时任务 | [详细](scheduler.md#post-jobs) |
| `DELETE /jobs/{job_id}` | 删除定时任务 | [详细](scheduler.md#delete-job) |
| `POST /jobs/{job_id}/run` | 立即执行任务 | [详细](scheduler.md#post-run-job) |

### 11. 配置管理 (`/api/config`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /` | 获取所有配置 | [详细](config.md#get-all) |
| `GET /{key}` | 获取单个配置 | [详细](config.md#get-key) |
| `PUT /{key}` | 更新配置 | [详细](config.md#put-key) |

### 12. 市场状态 (`/api/market`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `GET /is_trading_day` | 检查是否交易日 | [详细](market.md#get-is-trading-day) |
| `GET /trading_calendar` | 获取交易日历 | [详细](market.md#get-trading-calendar) |
| `GET /status` | 获取市场状态 | [详细](market.md#get-status) |

### 13. 自动化实验 (`/api/experiment`)

| 端点 | 说明 | 文档链接 |
|------|------|---------|
| `POST /create` | 创建实验 | [详细](experiment.md#post-create) |
| `GET /{experiment_id}` | 获取实验详情 | [详细](experiment.md#get-experiment) |
| `GET /list` | 获取实验列表 | [详细](experiment.md#get-list) |
| `POST /{experiment_id}/start` | 启动实验 | [详细](experiment.md#post-start) |
| `POST /{experiment_id}/stop` | 停止实验 | [详细](experiment.md#post-stop) |

---

## 通用规范

### 响应格式

所有 API 统一使用以下响应格式：

```json
{
  "status": "success",  // "success" | "error"
  "data": {},           // 响应数据
  "message": "操作成功",  // 可选：提示信息
  "error": null         // 可选：错误信息
}
```

#### 成功响应示例

```json
{
  "status": "success",
  "data": {
    "stock_code": "000001.SZ",
    "name": "平安银行",
    "market": "深圳主板"
  }
}
```

#### 错误响应示例

```json
{
  "status": "error",
  "data": null,
  "error": "股票代码不存在",
  "message": "请检查股票代码格式"
}
```

### HTTP 状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|---------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 分页参数

涉及列表查询的接口支持分页参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（从 1 开始） |
| `page_size` | int | 20 | 每页数量 |

### 日期格式

所有日期参数统一使用 ISO 8601 格式：

- **日期**: `YYYY-MM-DD`（例如：`2024-01-01`）
- **日期时间**: `YYYY-MM-DD HH:MM:SS`（例如：`2024-01-01 09:30:00`）

### 股票代码格式

股票代码格式：`{6位数字}.{市场代码}`

- **上交所**: `{代码}.SH`（例如：`600000.SH`）
- **深交所**: `{代码}.SZ`（例如：`000001.SZ`）

---

## 认证与授权

### 当前版本

**v1.0.0 暂不支持认证**，所有接口均可直接访问。

### 未来计划

计划在 v2.0.0 引入以下认证机制：

- **JWT Token**: 基于 JSON Web Token 的认证
- **API Key**: 基于密钥的认证
- **OAuth 2.0**: 第三方授权

---

## 限流策略

### 当前版本

**v1.0.0 暂无限流**

### 未来计划

计划在 v2.0.0 引入限流策略：

- **全局限流**: 1000 请求/分钟
- **用户限流**: 100 请求/分钟
- **IP 限流**: 200 请求/分钟

---

## 错误处理

### 错误响应格式

```json
{
  "status": "error",
  "data": null,
  "error": "错误详细信息",
  "message": "用户友好的提示信息"
}
```

### 常见错误

| 错误代码 | HTTP 状态码 | 说明 | 解决方案 |
|---------|-----------|------|---------|
| `INVALID_STOCK_CODE` | 400 | 股票代码格式错误 | 检查股票代码格式 |
| `STOCK_NOT_FOUND` | 404 | 股票不存在 | 确认股票代码是否正确 |
| `DATA_NOT_AVAILABLE` | 404 | 数据不可用 | 检查数据是否已下载 |
| `FEATURE_CALC_FAILED` | 500 | 特征计算失败 | 查看详细错误日志 |
| `MODEL_NOT_FOUND` | 404 | 模型不存在 | 确认模型名称是否正确 |
| `TRAINING_IN_PROGRESS` | 400 | 训练任务进行中 | 等待任务完成 |
| `DATABASE_ERROR` | 500 | 数据库错误 | 检查数据库连接 |
| `INTERNAL_ERROR` | 500 | 内部错误 | 联系技术支持 |

---

## 使用示例

### Python 示例

```python
import httpx

BASE_URL = "http://localhost:8000/api"

async def get_stock_list():
    """获取股票列表"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/stocks/list")
        result = response.json()

        if result["status"] == "success":
            stocks = result["data"]
            print(f"获取到 {len(stocks)} 只股票")
            return stocks
        else:
            print(f"错误: {result['error']}")
            return None

async def download_stock_data(stock_code: str, start_date: str, end_date: str):
    """下载股票数据"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/data/download",
            json={
                "stock_code": stock_code,
                "start_date": start_date,
                "end_date": end_date
            }
        )
        result = response.json()

        if result["status"] == "success":
            task_id = result["data"]["task_id"]
            print(f"下载任务已创建: {task_id}")
            return task_id
        else:
            print(f"错误: {result['error']}")
            return None

async def run_backtest(stock_code: str, strategy: str):
    """运行回测"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{BASE_URL}/backtest/run",
            json={
                "stock_code": stock_code,
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "strategy": strategy,
                "initial_capital": 1000000
            }
        )
        result = response.json()

        if result["status"] == "success":
            backtest_result = result["data"]
            print(f"年化收益: {backtest_result['annual_return']:.2%}")
            print(f"夏普比率: {backtest_result['sharpe_ratio']:.2f}")
            print(f"最大回撤: {backtest_result['max_drawdown']:.2%}")
            return backtest_result
        else:
            print(f"错误: {result['error']}")
            return None
```

### cURL 示例

```bash
# 健康检查
curl http://localhost:8000/health

# 获取股票列表
curl http://localhost:8000/api/stocks/list

# 获取单只股票信息
curl http://localhost:8000/api/stocks/000001.SZ

# 下载股票数据
curl -X POST http://localhost:8000/api/data/download \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'

# 运行回测
curl -X POST http://localhost:8000/api/backtest/run \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy": "momentum",
    "initial_capital": 1000000
  }'
```

### JavaScript 示例

```javascript
const BASE_URL = "http://localhost:8000/api";

// 获取股票列表
async function getStockList() {
  const response = await fetch(`${BASE_URL}/stocks/list`);
  const result = await response.json();

  if (result.status === "success") {
    console.log(`获取到 ${result.data.length} 只股票`);
    return result.data;
  } else {
    console.error(`错误: ${result.error}`);
    return null;
  }
}

// 运行回测
async function runBacktest(stockCode, strategy) {
  const response = await fetch(`${BASE_URL}/backtest/run`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      stock_code: stockCode,
      start_date: '2024-01-01',
      end_date: '2024-12-31',
      strategy: strategy,
      initial_capital: 1000000
    })
  });

  const result = await response.json();

  if (result.status === "success") {
    console.log(`年化收益: ${(result.data.annual_return * 100).toFixed(2)}%`);
    console.log(`夏普比率: ${result.data.sharpe_ratio.toFixed(2)}`);
    console.log(`最大回撤: ${(result.data.max_drawdown * 100).toFixed(2)}%`);
    return result.data;
  } else {
    console.error(`错误: ${result.error}`);
    return null;
  }
}
```

---

## 性能建议

### 1. 批量操作

优先使用批量接口而不是循环调用单个接口：

```python
# ❌ 不推荐：循环调用
for code in stock_codes:
    await client.get(f"/api/data/daily/{code}")

# ✅ 推荐：批量查询
await client.post("/api/data/batch_query", json={"codes": stock_codes})
```

### 2. 异步请求

使用异步客户端提高并发性能：

```python
import asyncio
import httpx

async def fetch_multiple_stocks(stock_codes):
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(f"{BASE_URL}/stocks/{code}")
            for code in stock_codes
        ]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

### 3. 缓存结果

对于不经常变化的数据（如股票列表），建议客户端缓存：

```python
import time

class APIClient:
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1小时

    async def get_stock_list(self):
        now = time.time()
        if 'stock_list' in self.cache:
            data, timestamp = self.cache['stock_list']
            if now - timestamp < self.cache_ttl:
                return data  # 返回缓存数据

        # 获取新数据
        data = await self._fetch_stock_list()
        self.cache['stock_list'] = (data, now)
        return data
```

---

## 更新日志

### v1.0.0 (2026-02-01)

**新增功能**:
- ✅ 完整的 RESTful API
- ✅ 13 个功能模块
- ✅ 60+ API 端点
- ✅ 自动生成的 Swagger 文档

**后续计划**:
- [ ] JWT 认证
- [ ] API 限流
- [ ] WebSocket 支持
- [ ] GraphQL 支持

---

## 相关文档

- [架构总览](../architecture/overview.md) - 了解系统架构
- [用户指南](../user_guide/quick_start.md) - 快速开始
- [开发指南](../developer_guide/contributing.md) - 参与开发

---

**维护团队**: Quant Team
**文档版本**: v1.0.0
**最后更新**: 2026-02-01
