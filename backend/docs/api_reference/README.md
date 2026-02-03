# API 参考文档

**版本**: v1.0.0
**最后更新**: 2026-02-01

---

## API 概览

Backend 提供完整的 RESTful API 服务，涵盖股票数据管理、特征工程、模型训练、回测分析等核心功能。

### 架构说明

**Phase 0 架构修正已完成** (2026-02-02)：
- ✅ **核心业务 API 已重写**：使用 Core Adapters 调用 Core 项目功能
- ✅ **辅助功能 API**：使用专门的 Service 类处理（不需要重写）
- Backend 现为**薄层 API 网关**，职责清晰

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

| 端点 | 说明 | 架构状态 |
|------|------|---------|
| `/` | 服务根路径 | - |
| `/health` | 健康检查 | - |

---

## 核心业务 API（已使用 Core Adapters 重写）

### 2. 股票管理 (`/api/stocks`) ✅ 已重写

**使用的 Adapter**: DataAdapter

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/` | GET | 获取股票列表（分页） | ✅ 已重写 |
| `/{code}` | GET | 获取单只股票信息 | ✅ 已重写 |
| `/search` | GET | 搜索股票 | ✅ 已重写 |
| `/update` | POST | 更新股票列表 | ✅ 已重写 |
| `/batch` | POST | 批量获取股票信息 | ✅ 已重写 |

**测试覆盖**: 40 个测试用例（24 单元 + 16 集成）
**代码减少**: 69%（业务逻辑移至 Core）

### 3. 数据管理 (`/api/data`) ✅ 已重写

**使用的 Adapter**: DataAdapter

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/daily/{code}` | GET | 获取日线数据 | ✅ 已重写 |
| `/download` | POST | 批量下载股票数据 | ✅ 已重写 |
| `/minute/{code}` | GET | 获取分钟数据 | ✅ 已重写 |
| `/check/{code}` | GET | 数据完整性检查 | ✅ 新增 |

**测试覆盖**: 31 个测试用例（17 单元 + 14 集成）
**支持功能**: 批量下载、分页查询、数据完整性检查、多种时间周期

### 4. 特征工程 (`/api/features`) ✅ 已重写

**使用的 Adapter**: FeatureAdapter, DataAdapter

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/{code}` | GET | 获取特征数据 | ✅ 已重写 |
| `/calculate/{code}` | POST | 计算特征 | ✅ 已重写 |
| `/names` | GET | 获取可用特征列表 | ✅ 新增 |
| `/{code}/select` | POST | 特征选择 | ✅ 新增 |

**测试覆盖**: 28 个测试用例（16 单元 + 12 集成）
**支持功能**: 125+ 特征（技术指标 + Alpha 因子）、特征选择、懒加载

### 5. 回测引擎 (`/api/backtest`) ✅ 已重写

**使用的 Adapter**: BacktestAdapter, DataAdapter

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/run` | POST | 运行回测 | ✅ 已重写 |
| `/metrics` | POST | 计算绩效指标 | ✅ 新增 |
| `/parallel` | POST | 并行回测 | ✅ 新增 |
| `/optimize` | POST | 参数优化 | ✅ 新增 |
| `/cost-analysis` | POST | 交易成本分析 | ✅ 新增 |
| `/risk-metrics` | POST | 风险指标计算 | ✅ 新增 |
| `/trade-statistics` | POST | 交易统计 | ✅ 新增 |

**测试覆盖**: 44 个测试用例（26 单元 + 18 集成）
**支持功能**: 策略参数优化、并行回测、20+ 绩效指标

### 6. 市场状态 (`/api/market`) ✅ 已重写

**使用的 Adapter**: MarketAdapter, DataAdapter

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/status` | GET | 获取市场状态 | ✅ 已重写 |
| `/trading-info` | GET | 获取交易时段信息 | ✅ 新增 |
| `/refresh-check` | GET | 检查是否需要刷新数据 | ✅ 已重写 |
| `/next-session` | GET | 获取下一交易时段 | ✅ 新增 |

**测试覆盖**: 33 个测试用例（19 单元 + 14 集成）
**支持功能**: 交易时段判断、数据新鲜度智能判断

---

## 辅助功能 API（使用专门的 Service，不需要重写）

### 7. 机器学习训练 (`/api/ml`) 🟡 使用 MLTrainingService

**说明**: 此 API 负责管理机器学习训练任务（任务调度、进度跟踪、模型管理），不涉及 Core 业务逻辑重复，因此使用专门的 `MLTrainingService`。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/train` | POST | 创建训练任务 | 🟡 独立实现 |
| `/tasks/{task_id}` | GET | 获取任务状态 | 🟡 独立实现 |
| `/tasks` | GET | 列出训练任务 | 🟡 独立实现 |
| `/tasks/{task_id}` | DELETE | 删除任务 | 🟡 独立实现 |
| `/tasks/{task_id}/stream` | GET | 流式推送训练进度 | 🟡 独立实现 |
| `/predict` | POST | 模型预测 | 🟡 独立实现 |
| `/models` | GET | 列出可用模型 | 🟡 独立实现 |
| `/models/{model_id}` | GET | 获取模型详情 | 🟡 独立实现 |
| `/models/{model_id}` | DELETE | 删除模型 | 🟡 独立实现 |

**实现方式**: `MLTrainingService` + `ExperimentService`
**文件大小**: 521 行

### 8. 策略管理 (`/api/strategy`) 🟡 使用 StrategyManager

**说明**: 提供策略元数据查询，使用 `StrategyManager` 管理策略注册表。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/list` | GET | 获取策略列表 | 🟡 独立实现 |
| `/metadata` | GET | 获取策略元数据 | 🟡 独立实现 |

**实现方式**: `StrategyManager`

### 9. 数据同步 (`/api/sync`) 🟡 使用专门的 Sync Services

**说明**: 负责数据同步任务调度和状态管理，使用专门的同步服务类。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/status` | GET | 获取同步状态 | 🟡 独立实现 |
| `/stock-list` | POST | 同步股票列表 | 🟡 独立实现 |
| `/daily-batch` | POST | 批量同步日线数据 | 🟡 独立实现 |
| `/minute` | POST | 同步分时数据 | 🟡 独立实现 |
| `/realtime` | POST | 同步实时行情 | 🟡 独立实现 |
| `/new-stocks` | POST | 同步新股列表 | 🟡 独立实现 |

**实现方式**: `StockListSyncService` + `DailySyncService` + `RealtimeSyncService`

### 10. 定时任务 (`/api/scheduler`) 🟡 使用 ConfigService

**说明**: 管理数据同步的定时任务配置和执行历史。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/tasks` | GET | 获取定时任务列表 | 🟡 独立实现 |
| `/tasks` | POST | 创建定时任务 | 🟡 独立实现 |
| `/tasks/{task_id}` | PUT | 更新定时任务 | 🟡 独立实现 |
| `/tasks/{task_id}` | DELETE | 删除定时任务 | 🟡 独立实现 |
| `/history` | GET | 获取执行历史 | 🟡 独立实现 |

**实现方式**: `ConfigService`

### 11. 配置管理 (`/api/config`) 🟡 使用 ConfigService

**说明**: 管理系统配置、数据源设置。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/source` | GET | 获取数据源配置 | 🟡 独立实现 |
| `/source` | POST | 更新数据源配置 | 🟡 独立实现 |

**实现方式**: `ConfigService`

### 12. 自动化实验 (`/api/experiment`) 🟡 使用 ExperimentService

**说明**: 管理自动化实验批次、参数网格搜索、模型排名。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/batch` | POST | 创建实验批次 | 🟡 独立实现 |
| `/batch/{batch_id}` | GET | 获取批次详情 | 🟡 独立实现 |
| `/batch/{batch_id}/start` | POST | 启动批次 | 🟡 独立实现 |
| `/batch/{batch_id}/stop` | POST | 停止批次 | 🟡 独立实现 |
| `/batch/{batch_id}/stream` | GET | 流式推送批次进度 | 🟡 独立实现 |
| 以及更多实验管理端点 | - | - | 🟡 独立实现 |

**实现方式**: `ExperimentService` + `BatchRepository` + `ExperimentRepository`

### 13. 模型管理 (`/api/models`) ⚠️ 占位符（未实现）

**说明**: 旧的模型管理端点，仅包含 TODO 占位符，功能已由 `/api/ml` 替代。

| 端点 | 方法 | 说明 | 架构状态 |
|------|------|------|---------|
| `/train` | POST | 训练模型 | ⚠️ 未实现（TODO） |
| `/predict/{code}` | GET | 获取预测结果 | ⚠️ 未实现（TODO） |

**建议**: 考虑删除此 API 或合并到 `/api/ml`

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

### v2.0.0 (2026-02-02) ✅ **Phase 0 架构修正完成**

**架构重大变更**:
- ✅ **6 个核心业务 API 已重写**：使用 Core Adapters 调用 Core 项目
  - Stocks API (5 个端点)
  - Data API (4 个端点)
  - Features API (4 个端点)
  - Backtest API (7 个端点)
  - Market API (4 个端点)
- ✅ **7 个辅助功能 API 保持独立**：使用专门的 Service 类
  - ML Training API (9 个端点) - `MLTrainingService`
  - Strategy API (2 个端点) - `StrategyManager`
  - Sync API (6 个端点) - 专门的 Sync Services
  - Scheduler API (5 个端点) - `ConfigService`
  - Config API (2 个端点) - `ConfigService`
  - Experiment API (15+ 个端点) - `ExperimentService`
- ⚠️ **1 个 API 待清理**：Models API（未实现的占位符）

**总计**:
- 📊 **31 个核心 API 端点**（已重写，使用 Core Adapters）
- 📦 **39+ 个辅助 API 端点**（独立实现，使用专门 Service）
- ✅ **226 个测试用例**（覆盖核心 API）
- 🎯 **测试覆盖率 90%+**（核心 API）

**关键成果**:
- 🏆 Backend 成为**薄层 API 网关**
- 🎯 职责清晰：核心业务 → Core；辅助功能 → Backend Services
- 📉 核心 API 代码减少 60%+
- ✨ 统一的 ApiResponse 格式
- 🚀 业务逻辑全部由 Core 处理

### v1.0.0 (2026-02-01)

**初始版本**:
- ✅ 完整的 RESTful API
- ✅ 13 个功能模块
- ✅ 70+ API 端点
- ✅ 自动生成的 Swagger 文档

**后续计划**:
- [ ] JWT 认证
- [ ] API 限流
- [ ] WebSocket 支持
- [ ] GraphQL 支持
- [ ] 清理未实现的 Models API

---

## 相关文档

- [架构总览](../architecture/overview.md) - 了解系统架构
- [用户指南](../user_guide/quick_start.md) - 快速开始
- [开发指南](../developer_guide/contributing.md) - 参与开发

---

**维护团队**: Quant Team
**文档版本**: v1.0.0
**最后更新**: 2026-02-01
