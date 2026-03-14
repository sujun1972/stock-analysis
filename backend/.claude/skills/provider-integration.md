# 数据提供者 (Provider) 集成指南

**作用**: 指导如何正确调用 core 项目的数据提供者 (Provider) API
**适用范围**: 所有需要从 core 项目获取数据的 backend 服务

---

## 📋 概述

Backend 项目通过 `src.providers` (来自 core 项目) 获取股票数据。Core 的数据提供者返回 `Response` 对象而非直接的 DataFrame，必须正确处理这些 Response 对象。

### 核心概念

```python
from src.providers import DataProviderFactory
from src.config.data_source_helper import create_provider, get_data_source_config

# 方式1: 直接创建（手动指定数据源）
provider = DataProviderFactory.create_provider(source="akshare")

# 方式2: 配置化创建（推荐，使用系统配置）
provider = create_provider("data")  # 使用主数据源配置
provider = create_provider("concept")  # 使用概念数据源配置
provider = create_provider("realtime")  # 使用实时数据源配置

# ❌ 错误：直接使用返回值
df = provider.get_daily_data(code="000001")  # 返回 Response 对象
if df.empty:  # AttributeError: 'Response' object has no attribute 'empty'
    ...

# ✅ 正确：检查 Response 并提取数据
response = provider.get_daily_data(code="000001")
if not response.is_success():
    # 处理错误
    raise ExternalAPIError(response.error_message, error_code=response.error_code)
df = response.data  # 提取 DataFrame
```

### 数据源配置系统

系统支持 7 种数据源的独立配置：

1. **主数据源** (`data`) - 日线数据、股票列表
2. **分时数据源** (`minute`) - 分钟级K线
3. **实时数据源** (`realtime`) - 实时行情
4. **涨停板池数据源** (`limit_up`) - 涨停板池数据
5. **龙虎榜数据源** (`top_list`) - 龙虎榜数据
6. **盘前数据源** (`premarket`) - 外盘/盘前数据
7. **概念数据源** (`concept`) - 概念板块数据

**配置方式**:
- Admin界面: 设置 > 数据源设置 (http://localhost:3002/settings/datasource)
- 数据库: `system_config` 表

**示例**:
```python
from src.config.data_source_helper import create_provider, get_data_source_config

# 获取当前配置
config = get_data_source_config()
print(f"主数据源: {config['data_source']}")
print(f"概念数据源: {config['concept_data_source']}")

# 使用配置创建 Provider（自动读取系统配置）
provider = create_provider("concept")  # 使用系统配置的概念数据源
response = provider.get_concept_list()
```

---

## 🎯 Response 对象结构

Core 的 `Response` 对象包含：

- **status**: 状态（success/warning/error）
- **message**: 消息文本
- **data**: 实际数据（DataFrame 或其他）
- **error_message**: 错误消息（仅错误时）
- **error_code**: 错误代码（仅错误时）
- **metadata**: 元数据字典

### 状态检查方法

```python
response.is_success()  # 是否成功
response.is_warning()  # 是否警告
response.is_error()    # 是否错误
```

---

## 📖 正确的调用模式

### 模式 1: 基本调用（同步）

```python
from src.providers import DataProviderFactory
from app.core.exceptions import ExternalAPIError

# 创建提供者
provider = DataProviderFactory.create_provider(
    source="akshare",
    token=""  # tushare 需要 token
)

# 调用 API
response = provider.get_daily_data(
    code="000001",
    start_date="20240101",
    end_date="20241231",
    adjust="qfq"
)

# 检查响应状态
if not response.is_success():
    raise ExternalAPIError(
        response.error_message or "获取日线数据失败",
        error_code=response.error_code or "API_ERROR"
    )

# 提取数据
df = response.data

# 使用数据
if df.empty:
    raise ValueError("无数据")
```

### 模式 2: 异步调用

```python
import asyncio
from src.providers import DataProviderFactory
from app.core.exceptions import ExternalAPIError

async def sync_daily_data(code: str) -> pd.DataFrame:
    """异步同步日线数据"""

    # 创建提供者
    provider = DataProviderFactory.create_provider(source="akshare")

    # 异步调用（使用 asyncio.to_thread）
    response = await asyncio.to_thread(
        provider.get_daily_data,
        code=code,
        start_date="20240101",
        end_date="20241231",
        adjust="qfq"
    )

    # 检查响应状态
    if not response.is_success():
        raise ExternalAPIError(
            response.error_message or f"{code}: 获取日线数据失败",
            error_code=response.error_code or "API_ERROR"
        )

    # 提取数据
    df = response.data

    if df.empty:
        raise ValueError(f"{code}: 无数据")

    return df
```

### 模式 3: 带超时的异步调用

```python
import asyncio
from src.providers import DataProviderFactory
from app.core.exceptions import ExternalAPIError

async def sync_with_timeout(code: str, timeout: float = 30.0):
    """带超时的异步同步"""

    provider = DataProviderFactory.create_provider(source="akshare")

    try:
        # 带超时的异步调用
        response = await asyncio.wait_for(
            asyncio.to_thread(
                provider.get_daily_data,
                code=code,
                start_date="20240101",
                end_date="20241231",
                adjust="qfq"
            ),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise TimeoutError(f"{code}: 数据获取超时（{timeout}秒）")

    # 检查响应状态
    if not response.is_success():
        raise ExternalAPIError(
            response.error_message or f"{code}: 获取日线数据失败",
            error_code=response.error_code or "API_ERROR"
        )

    df = response.data

    if df.empty:
        raise ValueError(f"{code}: 无数据")

    return df
```

---

## 🔧 常见 Provider 方法

### 1. get_stock_list()

获取股票列表

```python
response = provider.get_stock_list()

if not response.is_success():
    raise ExternalAPIError(
        response.error_message or "获取股票列表失败",
        error_code=response.error_code or "API_ERROR"
    )

stock_list_df = response.data
```

### 2. get_daily_data()

获取日线数据

```python
response = provider.get_daily_data(
    code="000001",
    start_date="20240101",
    end_date="20241231",
    adjust="qfq"  # 前复权
)

if not response.is_success():
    raise ExternalAPIError(
        response.error_message or "获取日线数据失败",
        error_code=response.error_code or "API_ERROR"
    )

daily_df = response.data
```

### 3. get_minute_data()

获取分时数据

```python
response = provider.get_minute_data(
    code="000001",
    period="5",  # 5分钟
    start_date="2024-01-01 09:30:00",
    end_date="2024-01-01 15:00:00"
)

if not response.is_success():
    raise ExternalAPIError(
        response.error_message or "获取分时数据失败",
        error_code=response.error_code or "API_ERROR"
    )

minute_df = response.data
```

### 4. get_realtime_quotes()

获取实时行情

```python
response = provider.get_realtime_quotes(
    codes=["000001", "000002"],  # None = 全部
    save_callback=None  # 可选的保存回调
)

if not response.is_success():
    raise ExternalAPIError(
        response.error_message or "获取实时行情失败",
        error_code=response.error_code or "API_ERROR"
    )

quotes_df = response.data
```

---

## 💡 最佳实践

### ✅ 推荐做法

1. **总是检查 Response 状态**
   ```python
   # ✅ 正确
   response = provider.get_daily_data(code)
   if not response.is_success():
       raise ExternalAPIError(response.error_message, error_code=response.error_code)
   df = response.data
   ```

2. **使用异步调用避免阻塞**
   ```python
   # ✅ 正确
   response = await asyncio.to_thread(provider.get_daily_data, code=code)
   ```

3. **添加超时保护**
   ```python
   # ✅ 正确
   response = await asyncio.wait_for(
       asyncio.to_thread(provider.get_daily_data, code=code),
       timeout=30.0
   )
   ```

4. **提供清晰的错误消息**
   ```python
   # ✅ 正确
   if not response.is_success():
       raise ExternalAPIError(
           response.error_message or f"{code}: 获取日线数据失败",
           error_code=response.error_code or "API_ERROR"
       )
   ```

5. **检查数据是否为空**
   ```python
   # ✅ 正确
   df = response.data
   if df.empty:
       logger.warning(f"{code}: 无数据")
       raise ValueError(f"{code}: 无数据")
   ```

### ❌ 避免做法

1. **直接使用返回值**
   ```python
   # ❌ 错误
   df = provider.get_daily_data(code)
   if df.empty:  # AttributeError: 'Response' object has no attribute 'empty'
       ...
   ```

2. **不检查状态就使用数据**
   ```python
   # ❌ 错误
   response = provider.get_daily_data(code)
   df = response.data  # 可能是 None 或空 DataFrame
   ```

3. **忽略错误信息**
   ```python
   # ❌ 错误
   if not response.is_success():
       raise Exception("失败")  # 丢失了错误详情
   ```

4. **同步调用阻塞事件循环**
   ```python
   # ❌ 错误（在异步函数中）
   async def sync_data():
       response = provider.get_daily_data(code)  # 阻塞事件循环
   ```

---

## 📊 完整示例

### 示例 1: DailySyncService

```python
import asyncio
from datetime import datetime, timedelta
from loguru import logger
from src.providers import DataProviderFactory
from app.core.exceptions import ExternalAPIError

class DailySyncService:
    """日线数据同步服务"""

    async def sync_single_stock(self, code: str, years: int = 5) -> dict:
        """同步单只股票日线数据"""

        # 创建提供者
        provider = DataProviderFactory.create_provider(source="akshare")

        # 计算日期范围
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=years * 365)).strftime("%Y%m%d")

        logger.info(f"同步 {code} 日线数据 ({start_date} - {end_date})")

        # 获取日线数据（带超时）
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    provider.get_daily_data,
                    code=code,
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"
                ),
                timeout=30.0
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"{code}: 数据获取超时")

        # 检查响应状态并提取数据
        if not response.is_success():
            raise ExternalAPIError(
                response.error_message or f"{code}: 获取日线数据失败",
                error_code=response.error_code or "API_ERROR"
            )

        df = response.data

        if df.empty:
            raise ValueError(f"{code}: 无数据")

        # 保存到数据库
        count = await asyncio.to_thread(self.db.save_daily_data, df, code)

        logger.info(f"✓ {code}: {count} 条记录")

        return {"code": code, "records": count}
```

### 示例 2: StockListSyncService

```python
import asyncio
from loguru import logger
from src.providers import DataProviderFactory
from app.core.exceptions import ExternalAPIError
from app.utils.retry import retry_async

class StockListSyncService:
    """股票列表同步服务"""

    async def sync_stock_list(self) -> dict:
        """同步股票列表"""

        # 创建提供者
        provider = DataProviderFactory.create_provider(source="akshare")

        logger.info("获取股票列表...")

        # 使用重试机制调用
        response = await retry_async(
            asyncio.to_thread,
            provider.get_stock_list,
            max_retries=3,
            delay_base=3.0
        )

        # 检查响应状态并提取数据
        if not response.is_success():
            raise ExternalAPIError(
                response.error_message or "获取股票列表失败",
                error_code=response.error_code or "API_ERROR"
            )

        stock_list = response.data

        # 保存到数据库
        count = await asyncio.to_thread(self.db.save_stock_list, stock_list)

        logger.info(f"✓ 股票列表同步完成: {count} 只")

        return {"total": count}
```

---

## 🔍 调试技巧

### 1. 检查 Response 内容

```python
response = provider.get_daily_data(code="000001")

# 打印完整响应信息
logger.debug(f"Status: {response.status}")
logger.debug(f"Message: {response.message}")
logger.debug(f"Data type: {type(response.data)}")
logger.debug(f"Metadata: {response.metadata}")

if response.is_error():
    logger.error(f"Error: {response.error_message}")
    logger.error(f"Error code: {response.error_code}")
```

### 2. 处理 Warning 状态

```python
response = provider.get_daily_data(code="000001")

if response.is_warning():
    # 警告状态仍有数据，但需要注意
    logger.warning(f"⚠️ {response.message}")
    logger.warning(f"Metadata: {response.metadata}")
    df = response.data  # 仍可使用数据
```

---

## 📝 检查清单

在调用 Provider API 时，确保：

- [ ] 使用 `asyncio.to_thread()` 进行异步调用
- [ ] 添加超时保护（`asyncio.wait_for`）
- [ ] 检查 `response.is_success()`
- [ ] 提取数据使用 `response.data`
- [ ] 处理错误时使用 `response.error_message` 和 `response.error_code`
- [ ] 检查 DataFrame 是否为空
- [ ] 使用 `ExternalAPIError` 封装外部 API 错误
- [ ] 添加适当的日志记录

---

## 🚀 相关资源

### Backend 文件
- [daily_sync_service.py](../../app/services/daily_sync_service.py) - 日线数据同步示例
- [stock_list_sync_service.py](../../app/services/stock_list_sync_service.py) - 股票列表同步示例
- [realtime_sync_service.py](../../app/services/realtime_sync_service.py) - 实时行情同步示例

### Core 文件
- [Response 类文档](../../../core/.claude/skills/response-format.md)
- [Provider 接口](../../../core/src/providers/base_provider.py)
- [AkShare Provider](../../../core/src/providers/akshare/provider.py)
- [Tushare Provider](../../../core/src/providers/tushare/provider.py)

---

**版本**: 1.0.0
**创建日期**: 2026-03-13
**维护者**: Stock Analysis Team
