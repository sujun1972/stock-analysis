# API 使用指南

**版本**: v2.0.0
**最后更新**: 2026-02-05
**适用于**: A股AI量化交易系统 Backend API

---

## 目录

1. [快速开始](#快速开始)
2. [认证与授权](#认证与授权)
3. [通用规范](#通用规范)
4. [常见使用场景](#常见使用场景)
5. [错误处理指南](#错误处理指南)
6. [最佳实践](#最佳实践)
7. [完整示例](#完整示例)

---

## 快速开始

### 1. 启动服务

```bash
# 使用 Docker Compose 启动
cd /path/to/stock-analysis
docker-compose up -d

# 验证服务运行
curl http://localhost:8000/health
```

### 2. 访问 API 文档

服务启动后，可以通过以下 URL 访问交互式 API 文档：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### 3. 发送第一个请求

```bash
# 获取股票列表
curl http://localhost:8000/api/stocks/list

# 获取单只股票信息
curl http://localhost:8000/api/stocks/000001.SZ

# 获取日线数据
curl "http://localhost:8000/api/data/daily/000001.SZ?limit=10"
```

---

## 认证与授权

### 当前版本 (v2.0.0)

**暂无认证要求**，所有 API 端点均可直接访问。

### 未来版本 (v3.0.0 计划)

将支持以下认证方式：

- **JWT Token**: Bearer Token 认证
- **API Key**: Header 或 Query 参数传递
- **OAuth 2.0**: 第三方应用授权

示例（未来版本）：

```bash
# JWT Token 认证
curl -H "Authorization: Bearer <your-token>" \
  http://localhost:8000/api/stocks/list

# API Key 认证
curl -H "X-API-Key: <your-api-key>" \
  http://localhost:8000/api/stocks/list
```

---

## 通用规范

### 基础信息

| 项目 | 说明 |
|------|------|
| **Base URL** | `http://localhost:8000/api` |
| **响应格式** | JSON |
| **字符编码** | UTF-8 |
| **日期格式** | ISO 8601 (YYYY-MM-DD) |
| **时间格式** | ISO 8601 (YYYY-MM-DD HH:MM:SS) |

### 统一响应格式

所有 API 端点返回统一的 JSON 格式：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { /* 响应数据 */ }
}
```

#### 成功响应示例

```json
{
  "code": 200,
  "message": "获取股票信息成功",
  "data": {
    "code": "000001.SZ",
    "name": "平安银行",
    "market": "深圳主板",
    "industry": "银行"
  }
}
```

#### 错误响应示例

```json
{
  "code": 404,
  "message": "股票不存在",
  "error": "STOCK_NOT_FOUND",
  "data": null
}
```

### HTTP 状态码

| 状态码 | 说明 | 使用场景 |
|--------|------|----------|
| 200 | OK | 请求成功 |
| 201 | Created | 资源创建成功 |
| 400 | Bad Request | 请求参数错误 |
| 404 | Not Found | 资源不存在 |
| 422 | Unprocessable Entity | 参数验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 服务暂时不可用 |

### 分页参数

支持分页的接口使用以下标准参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `page` | int | 1 | 页码（从 1 开始） |
| `page_size` | int | 20 | 每页数量（1-100） |

分页响应格式：

```json
{
  "code": 200,
  "message": "获取列表成功",
  "data": {
    "items": [ /* 当前页数据 */ ],
    "total": 5000,
    "page": 1,
    "page_size": 20,
    "total_pages": 250
  }
}
```

### 股票代码格式

股票代码格式：`{6位数字}.{市场代码}`

| 市场 | 代码格式 | 示例 |
|------|----------|------|
| 上交所 | {代码}.SH | 600000.SH |
| 深交所 | {代码}.SZ | 000001.SZ |
| 北交所 | {代码}.BJ | 430047.BJ |

---

## 常见使用场景

### 场景 1: 获取股票基础信息

#### 1.1 获取所有正常上市的股票

```bash
curl "http://localhost:8000/api/stocks/list?status=正常&page=1&page_size=100"
```

#### 1.2 搜索特定股票

```bash
# 按代码搜索
curl "http://localhost:8000/api/stocks/list?search=000001"

# 按名称搜索
curl "http://localhost:8000/api/stocks/list?search=平安"
```

#### 1.3 筛选特定市场

```bash
# 只看创业板
curl "http://localhost:8000/api/stocks/list?market=创业板"

# 只看科创板
curl "http://localhost:8000/api/stocks/list?market=科创板"
```

#### 1.4 获取单只股票详情

```bash
curl http://localhost:8000/api/stocks/000001.SZ
```

**Python 示例**:

```python
import httpx
import asyncio

async def get_stock_info(code: str):
    """获取股票基础信息"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/api/stocks/{code}")
        result = response.json()

        if result["code"] == 200:
            stock = result["data"]
            print(f"股票名称: {stock['name']}")
            print(f"所属市场: {stock['market']}")
            print(f"所属行业: {stock['industry']}")
            return stock
        else:
            print(f"错误: {result['message']}")
            return None

# 运行
asyncio.run(get_stock_info("000001.SZ"))
```

---

### 场景 2: 下载和查询历史数据

#### 2.1 下载单只股票的历史数据

```bash
curl -X POST "http://localhost:8000/api/data/download" \
  -H "Content-Type: application/json" \
  -d '{
    "codes": ["000001.SZ"],
    "start_date": "2023-01-01",
    "end_date": "2024-12-31"
  }'
```

#### 2.2 批量下载多只股票数据

```bash
curl -X POST "http://localhost:8000/api/data/download" \
  -H "Content-Type: application/json" \
  -d '{
    "codes": ["000001.SZ", "600000.SH", "300001.SZ"],
    "years": 3,
    "batch_size": 50
  }'
```

#### 2.3 下载全部股票数据（限制数量）

```bash
curl -X POST "http://localhost:8000/api/data/download" \
  -H "Content-Type: application/json" \
  -d '{
    "years": 1,
    "max_stocks": 100,
    "batch_size": 20
  }'
```

#### 2.4 查询日线数据

```bash
# 获取最近一年的数据
curl "http://localhost:8000/api/data/daily/000001.SZ?limit=500"

# 指定日期范围
curl "http://localhost:8000/api/data/daily/000001.SZ?start_date=2024-01-01&end_date=2024-12-31"
```

**Python 示例**:

```python
import httpx
import asyncio

async def download_and_query_data():
    """下载数据并查询"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. 下载数据
        download_response = await client.post(
            "http://localhost:8000/api/data/download",
            json={
                "codes": ["000001.SZ"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )
        download_result = download_response.json()
        print(f"下载状态: {download_result['message']}")

        # 2. 等待几秒让数据下载完成
        await asyncio.sleep(5)

        # 3. 查询数据
        query_response = await client.get(
            "http://localhost:8000/api/data/daily/000001.SZ",
            params={"limit": 10}
        )
        query_result = query_response.json()

        if query_result["code"] == 200:
            data = query_result["data"]
            print(f"数据条数: {data['count']}")
            print(f"最新数据: {data['data'][0]}")
            return data
        else:
            print(f"错误: {query_result['message']}")
            return None

asyncio.run(download_and_query_data())
```

---

### 场景 3: 特征计算

#### 3.1 获取可用特征列表

```bash
curl http://localhost:8000/api/features/names
```

#### 3.2 计算单只股票的特征

```bash
curl -X POST "http://localhost:8000/api/features/calculate/000001.SZ" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "feature_groups": ["technical", "alpha"]
  }'
```

#### 3.3 获取已计算的特征数据

```bash
curl "http://localhost:8000/api/features/000001.SZ?start_date=2024-01-01&end_date=2024-12-31"
```

#### 3.4 特征选择

```bash
curl -X POST "http://localhost:8000/api/features/000001.SZ/select" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "variance",
    "top_k": 50,
    "start_date": "2024-01-01",
    "end_date": "2024-12-31"
  }'
```

**Python 示例**:

```python
import httpx
import asyncio

async def calculate_features(code: str):
    """计算股票特征"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        # 1. 计算特征
        calc_response = await client.post(
            f"http://localhost:8000/api/features/calculate/{code}",
            json={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "feature_groups": ["technical", "alpha", "volume"]
            }
        )
        calc_result = calc_response.json()
        print(f"计算状态: {calc_result['message']}")

        # 2. 获取特征数据
        feature_response = await client.get(
            f"http://localhost:8000/api/features/{code}",
            params={
                "start_date": "2024-01-01",
                "end_date": "2024-12-31"
            }
        )
        feature_result = feature_response.json()

        if feature_result["code"] == 200:
            features = feature_result["data"]
            print(f"特征数量: {features['feature_count']}")
            print(f"数据条数: {features['record_count']}")
            return features
        else:
            print(f"错误: {feature_result['message']}")
            return None

asyncio.run(calculate_features("000001.SZ"))
```

---

### 场景 4: 策略回测

#### 4.1 运行单策略回测

```bash
curl -X POST "http://localhost:8000/api/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["000001.SZ"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy_params": {
      "strategy_name": "momentum",
      "window": 20,
      "threshold": 0.05
    },
    "initial_capital": 1000000,
    "commission_rate": 0.0003,
    "stamp_tax_rate": 0.001
  }'
```

#### 4.2 并行回测多只股票

```bash
curl -X POST "http://localhost:8000/api/backtest/parallel" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_codes": ["000001.SZ", "600000.SH", "300001.SZ"],
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy_params": {
      "strategy_name": "mean_reversion",
      "window": 20
    },
    "initial_capital": 1000000
  }'
```

#### 4.3 参数优化

```bash
curl -X POST "http://localhost:8000/api/backtest/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "strategy_name": "momentum",
    "param_grid": {
      "window": [10, 20, 30, 60],
      "threshold": [0.03, 0.05, 0.08]
    },
    "optimize_metric": "sharpe_ratio"
  }'
```

**Python 示例**:

```python
import httpx
import asyncio

async def run_backtest():
    """运行回测并分析结果"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            "http://localhost:8000/api/backtest/run",
            json={
                "stock_codes": ["000001.SZ"],
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "strategy_params": {
                    "strategy_name": "momentum",
                    "window": 20,
                    "threshold": 0.05
                },
                "initial_capital": 1000000,
                "commission_rate": 0.0003
            }
        )
        result = response.json()

        if result["code"] == 200:
            metrics = result["data"]
            print("=" * 50)
            print("回测结果")
            print("=" * 50)
            print(f"年化收益率: {metrics.get('annual_return', 0) * 100:.2f}%")
            print(f"夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
            print(f"最大回撤: {metrics.get('max_drawdown', 0) * 100:.2f}%")
            print(f"胜率: {metrics.get('win_rate', 0) * 100:.2f}%")
            print(f"总交易次数: {metrics.get('total_trades', 0)}")
            print("=" * 50)
            return metrics
        else:
            print(f"错误: {result['message']}")
            return None

asyncio.run(run_backtest())
```

---

### 场景 5: 市场状态查询

#### 5.1 获取当前市场状态

```bash
curl http://localhost:8000/api/market/status
```

#### 5.2 检查是否需要刷新数据

```bash
curl http://localhost:8000/api/market/refresh-check
```

#### 5.3 获取下一交易时段

```bash
curl http://localhost:8000/api/market/next-session
```

**Python 示例**:

```python
import httpx
import asyncio

async def check_market_status():
    """检查市场状态并决定是否刷新数据"""
    async with httpx.AsyncClient() as client:
        # 1. 获取市场状态
        status_response = await client.get("http://localhost:8000/api/market/status")
        status_result = status_response.json()

        if status_result["code"] == 200:
            market = status_result["data"]
            print(f"当前时间: {market['current_time']}")
            print(f"是否交易日: {market['is_trading_day']}")
            print(f"市场状态: {market['market_status']}")

            # 2. 检查是否需要刷新
            refresh_response = await client.get("http://localhost:8000/api/market/refresh-check")
            refresh_result = refresh_response.json()

            if refresh_result["code"] == 200:
                refresh_info = refresh_result["data"]
                print(f"需要刷新: {refresh_info['needs_refresh']}")
                print(f"原因: {refresh_info.get('reason', 'N/A')}")

                return {
                    "market_status": market,
                    "needs_refresh": refresh_info['needs_refresh']
                }

        return None

asyncio.run(check_market_status())
```

---

## 错误处理指南

### 常见错误码

| 错误码 | HTTP 状态码 | 说明 | 解决方案 |
|--------|-----------|------|---------|
| `INVALID_STOCK_CODE` | 400 | 股票代码格式错误 | 检查股票代码格式 (如 000001.SZ) |
| `STOCK_NOT_FOUND` | 404 | 股票不存在 | 确认股票代码是否正确 |
| `DATA_NOT_AVAILABLE` | 404 | 数据不可用 | 先下载数据或检查日期范围 |
| `FEATURE_CALC_FAILED` | 500 | 特征计算失败 | 查看详细错误日志，检查数据完整性 |
| `MODEL_NOT_FOUND` | 404 | 模型不存在 | 确认模型名称或先训练模型 |
| `TRAINING_IN_PROGRESS` | 400 | 训练任务进行中 | 等待当前任务完成 |
| `DATABASE_ERROR` | 500 | 数据库错误 | 检查数据库连接和状态 |
| `INTERNAL_ERROR` | 500 | 内部错误 | 查看日志或联系技术支持 |

### 错误处理最佳实践

#### Python 错误处理示例

```python
import httpx
import asyncio
from typing import Optional, Dict, Any

class APIError(Exception):
    """API 错误基类"""
    def __init__(self, code: int, message: str, error: Optional[str] = None):
        self.code = code
        self.message = message
        self.error = error
        super().__init__(f"[{code}] {message}: {error}")

async def safe_api_call(
    url: str,
    method: str = "GET",
    **kwargs
) -> Dict[str, Any]:
    """安全的 API 调用，带错误处理"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            else:
                raise ValueError(f"不支持的方法: {method}")

            response.raise_for_status()
            result = response.json()

            # 检查业务错误
            if result.get("code") != 200:
                raise APIError(
                    code=result.get("code", 500),
                    message=result.get("message", "未知错误"),
                    error=result.get("error")
                )

            return result["data"]

        except httpx.HTTPStatusError as e:
            print(f"HTTP 错误: {e.response.status_code}")
            raise
        except httpx.RequestError as e:
            print(f"请求错误: {str(e)}")
            raise
        except APIError as e:
            print(f"API 错误: {e}")
            raise
        except Exception as e:
            print(f"未知错误: {str(e)}")
            raise

# 使用示例
async def main():
    try:
        # 成功调用
        stock = await safe_api_call("http://localhost:8000/api/stocks/000001.SZ")
        print(f"股票名称: {stock['name']}")

    except APIError as e:
        if e.code == 404:
            print("股票不存在，请检查代码")
        elif e.code == 500:
            print("服务器错误，请稍后重试")
        else:
            print(f"其他错误: {e}")

asyncio.run(main())
```

#### JavaScript 错误处理示例

```javascript
class APIError extends Error {
  constructor(code, message, error) {
    super(`[${code}] ${message}: ${error}`);
    this.code = code;
    this.message = message;
    this.error = error;
  }
}

async function safeAPICall(url, options = {}) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();

    // 检查业务错误
    if (result.code !== 200) {
      throw new APIError(
        result.code || 500,
        result.message || '未知错误',
        result.error
      );
    }

    return result.data;

  } catch (error) {
    if (error instanceof APIError) {
      console.error('API 错误:', error);
      throw error;
    } else {
      console.error('网络或其他错误:', error);
      throw error;
    }
  }
}

// 使用示例
async function main() {
  try {
    const stock = await safeAPICall('http://localhost:8000/api/stocks/000001.SZ');
    console.log('股票名称:', stock.name);

  } catch (error) {
    if (error instanceof APIError) {
      if (error.code === 404) {
        console.log('股票不存在，请检查代码');
      } else if (error.code === 500) {
        console.log('服务器错误，请稍后重试');
      }
    }
  }
}
```

---

## 最佳实践

### 1. 使用异步客户端

对于 Python，推荐使用 `httpx.AsyncClient` 而不是同步的 `requests`：

```python
# ✅ 推荐：异步
import httpx
async with httpx.AsyncClient() as client:
    response = await client.get(url)

# ❌ 不推荐：同步
import requests
response = requests.get(url)
```

### 2. 设置合理的超时

不同的操作需要不同的超时时间：

```python
# 快速查询：30秒
async with httpx.AsyncClient(timeout=30.0) as client:
    await client.get("/api/stocks/list")

# 数据下载：5分钟
async with httpx.AsyncClient(timeout=300.0) as client:
    await client.post("/api/data/download", json={...})

# 回测计算：10分钟
async with httpx.AsyncClient(timeout=600.0) as client:
    await client.post("/api/backtest/run", json={...})
```

### 3. 使用批量接口

优先使用批量接口而不是循环调用：

```python
# ❌ 不推荐：循环调用
for code in stock_codes:
    await client.get(f"/api/stocks/{code}")

# ✅ 推荐：批量查询
await client.post("/api/stocks/batch", json={"codes": stock_codes})
```

### 4. 实现重试机制

对于网络错误和临时性错误，实现指数退避重试：

```python
import asyncio
from typing import Callable, Any

async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0
) -> Any:
    """带指数退避的重试机制"""
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise

            print(f"重试 {attempt + 1}/{max_retries}，{delay}秒后重试...")
            await asyncio.sleep(delay)
            delay *= backoff_factor

# 使用示例
async def fetch_stock():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/stocks/000001.SZ")
        return response.json()

result = await retry_with_backoff(fetch_stock)
```

### 5. 缓存不变数据

对于不经常变化的数据（如股票列表），实现客户端缓存：

```python
import time
from typing import Dict, Any, Optional

class APICache:
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, tuple[Any, float]] = {}
        self.ttl = ttl

    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
        return None

    def set(self, key: str, data: Any):
        self.cache[key] = (data, time.time())

# 使用示例
cache = APICache(ttl=3600)  # 1小时

async def get_stock_list_cached():
    # 尝试从缓存获取
    cached = cache.get("stock_list")
    if cached:
        return cached

    # 从 API 获取
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/api/stocks/list")
        data = response.json()["data"]

        # 存入缓存
        cache.set("stock_list", data)
        return data
```

### 6. 并发请求控制

使用信号量限制并发请求数量：

```python
import asyncio
import httpx

async def fetch_multiple_stocks(stock_codes: list[str], max_concurrent: int = 10):
    """并发获取多只股票信息，限制并发数"""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_one(code: str):
        async with semaphore:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8000/api/stocks/{code}")
                return response.json()

    tasks = [fetch_one(code) for code in stock_codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 过滤错误
    return [r for r in results if not isinstance(r, Exception)]

# 使用
codes = ["000001.SZ", "600000.SH", "300001.SZ", ...]
results = await fetch_multiple_stocks(codes, max_concurrent=10)
```

---

## 完整示例

### 示例 1: 完整的回测流程

```python
import httpx
import asyncio
from typing import List, Dict, Any

class QuantTradingClient:
    """量化交易 API 客户端"""

    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(timeout=300.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def get_stock_list(self, market: str = None) -> List[Dict]:
        """获取股票列表"""
        params = {"page_size": 100}
        if market:
            params["market"] = market

        response = await self.client.get(f"{self.base_url}/stocks/list", params=params)
        result = response.json()
        return result["data"]["items"]

    async def download_data(self, codes: List[str], years: int = 3):
        """下载历史数据"""
        response = await self.client.post(
            f"{self.base_url}/data/download",
            json={"codes": codes, "years": years, "batch_size": 50}
        )
        result = response.json()
        return result["data"]

    async def calculate_features(self, code: str, start_date: str, end_date: str):
        """计算特征"""
        response = await self.client.post(
            f"{self.base_url}/features/calculate/{code}",
            json={
                "start_date": start_date,
                "end_date": end_date,
                "feature_groups": ["technical", "alpha", "volume"]
            }
        )
        result = response.json()
        return result["data"]

    async def run_backtest(self, code: str, strategy_params: Dict,
                          start_date: str, end_date: str):
        """运行回测"""
        response = await self.client.post(
            f"{self.base_url}/backtest/run",
            json={
                "stock_codes": [code],
                "start_date": start_date,
                "end_date": end_date,
                "strategy_params": strategy_params,
                "initial_capital": 1000000,
                "commission_rate": 0.0003
            }
        )
        result = response.json()
        return result["data"]

async def main():
    """完整的回测流程"""

    async with QuantTradingClient() as client:
        # 1. 获取股票列表（只看主板）
        print("1. 获取股票列表...")
        stocks = await client.get_stock_list(market="深圳主板")
        print(f"   找到 {len(stocks)} 只股票")

        # 选择前3只股票
        target_stocks = [s["code"] for s in stocks[:3]]
        print(f"   选择股票: {target_stocks}")

        # 2. 下载历史数据
        print("\n2. 下载历史数据...")
        await client.download_data(target_stocks, years=3)
        print("   数据下载完成")

        # 等待数据下载
        await asyncio.sleep(10)

        # 3. 对每只股票进行回测
        print("\n3. 运行回测...")
        results = []

        for code in target_stocks:
            print(f"\n   回测 {code}...")

            # 3.1 计算特征
            features = await client.calculate_features(
                code, "2023-01-01", "2024-12-31"
            )
            print(f"   - 特征计算完成: {features.get('feature_count', 0)} 个特征")

            # 3.2 运行回测
            backtest_result = await client.run_backtest(
                code,
                strategy_params={"strategy_name": "momentum", "window": 20},
                start_date="2023-01-01",
                end_date="2024-12-31"
            )

            print(f"   - 年化收益: {backtest_result.get('annual_return', 0) * 100:.2f}%")
            print(f"   - 夏普比率: {backtest_result.get('sharpe_ratio', 0):.2f}")
            print(f"   - 最大回撤: {backtest_result.get('max_drawdown', 0) * 100:.2f}%")

            results.append({
                "code": code,
                "metrics": backtest_result
            })

        # 4. 汇总结果
        print("\n" + "=" * 60)
        print("回测结果汇总")
        print("=" * 60)

        # 按夏普比率排序
        results.sort(key=lambda x: x["metrics"].get("sharpe_ratio", 0), reverse=True)

        for i, r in enumerate(results, 1):
            print(f"\n{i}. {r['code']}")
            print(f"   年化收益: {r['metrics'].get('annual_return', 0) * 100:.2f}%")
            print(f"   夏普比率: {r['metrics'].get('sharpe_ratio', 0):.2f}")
            print(f"   最大回撤: {r['metrics'].get('max_drawdown', 0) * 100:.2f}%")
            print(f"   胜率: {r['metrics'].get('win_rate', 0) * 100:.2f}%")

# 运行
if __name__ == "__main__":
    asyncio.run(main())
```

---

## 相关文档

- [API 参考文档](./README.md) - 完整的 API 端点列表
- [架构总览](../architecture/overview.md) - 系统架构说明
- [快速开始](../user_guide/quick_start.md) - 新手入门指南
- [开发指南](../developer_guide/contributing.md) - 开发者贡献指南

---

**维护团队**: Quant Team
**文档版本**: v2.0.0
**最后更新**: 2026-02-05
