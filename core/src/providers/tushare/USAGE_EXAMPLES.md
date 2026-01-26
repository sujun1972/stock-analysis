# TushareProvider 使用示例

本文档提供模块化重构后的 TushareProvider 使用示例。

## 基础使用

### 1. 创建Provider实例

```python
from src.providers.tushare import TushareProvider

# 方式1: 直接创建
provider = TushareProvider(
    token='your_tushare_token',
    timeout=30,
    retry_count=3,
    request_delay=0.2
)

# 方式2: 通过工厂创建（推荐用于Backend）
from src.providers import DataProviderFactory

provider = DataProviderFactory.create_provider(
    source='tushare',
    token='your_tushare_token',
    retry_count=3
)
```

### 2. 获取股票列表

```python
# 获取全部A股列表
stock_list = provider.get_stock_list()
print(f"共 {len(stock_list)} 只股票")
print(stock_list.head())

# 输出字段:
# code, name, market, industry, area, list_date, status
```

### 3. 获取日线数据

```python
# 获取单只股票的日线数据
daily_data = provider.get_daily_data(
    code='000001',
    start_date='20240101',
    end_date='20241231',
    adjust='qfq'  # 前复权
)

print(f"共 {len(daily_data)} 条数据")
print(daily_data.head())

# 输出字段:
# trade_date, open, high, low, close, volume, amount,
# amplitude, pct_change, change_amount, turnover
```

### 4. 批量获取日线数据

```python
codes = ['000001', '600000', '300001']
batch_data = provider.get_daily_batch(
    codes=codes,
    start_date='20240101',
    end_date='20241231',
    adjust='qfq'
)

for code, df in batch_data.items():
    print(f"{code}: {len(df)} 条数据")
```

### 5. 获取新股

```python
# 获取最近30天上市的新股
new_stocks = provider.get_new_stocks(days=30)
print(f"新股: {len(new_stocks)} 只")
print(new_stocks)

# 输出字段:
# code, name, market, list_date, status
```

### 6. 获取退市股票

```python
delisted = provider.get_delisted_stocks()
print(f"退市股票: {len(delisted)} 只")

# 输出字段:
# code, name, list_date, delist_date, market
```

### 7. 获取分钟数据

```python
# 注意: 需要2000积分
minute_data = provider.get_minute_data(
    code='000001',
    period='5',  # 5分钟
    start_date='20241201',
    end_date='20241231'
)

print(f"分钟数据: {len(minute_data)} 条")

# 输出字段:
# trade_time, period, open, high, low, close, volume, amount
```

### 8. 获取实时行情

```python
# 注意: 需要5000积分
quotes = provider.get_realtime_quotes(codes=['000001', '600000'])
print(quotes)

# 输出字段:
# code, name, latest_price, open, high, low, pre_close,
# volume, amount, pct_change, change_amount, turnover,
# amplitude, trade_time
```

## 高级使用

### 1. 使用配置常量

```python
from src.providers.tushare import TushareConfig

# 查看积分要求
print(f"日线数据需要: {TushareConfig.POINTS_DAILY_DATA} 积分")
print(f"分钟数据需要: {TushareConfig.POINTS_MINUTE_DATA} 积分")
print(f"实时行情需要: {TushareConfig.POINTS_REALTIME_QUOTES} 积分")

# 使用市场类型映射
market = TushareConfig.parse_market_from_code('000001')
print(f"000001 属于: {market}")
```

### 2. 使用数据转换器

```python
from src.providers.tushare import TushareDataConverter

converter = TushareDataConverter()

# 股票代码转换
ts_code = converter.to_ts_code('000001')  # '000001.SZ'
code = converter.from_ts_code('000001.SZ')  # '000001'

# 转换原始数据（如果需要手动处理）
import pandas as pd
raw_data = pd.DataFrame(...)  # 从API获取的原始数据
standard_data = converter.convert_daily_data(raw_data)
```

### 3. 异常处理

```python
from src.providers.tushare import (
    TusharePermissionError,
    TushareRateLimitError,
    TushareDataError,
    TushareAPIError
)

try:
    quotes = provider.get_realtime_quotes()

except TusharePermissionError as e:
    # 积分不足或权限不足
    print(f"权限错误: {e}")
    print("请检查您的账户积分")

except TushareRateLimitError as e:
    # 频率限制
    print(f"频率限制: {e}")
    print(f"建议等待 {e.retry_after} 秒后重试")

except TushareDataError as e:
    # 数据错误（空数据等）
    print(f"数据错误: {e}")

except TushareAPIError as e:
    # 其他API错误
    print(f"API错误: {e}")
```

### 4. 自定义API客户端

```python
from src.providers.tushare import TushareAPIClient

# 创建自定义客户端
client = TushareAPIClient(
    token='your_token',
    timeout=60,
    retry_count=5,
    retry_delay=2,
    request_delay=0.5  # 更长的请求间隔
)

# 使用通用查询接口
result = client.query(
    'stock_basic',
    exchange='',
    list_status='L'
)
```

### 5. Backend集成示例

```python
# backend/app/services/stock_service.py

from src.providers import DataProviderFactory
import asyncio

class StockService:
    def __init__(self):
        self.provider = None

    async def initialize(self):
        """初始化数据提供者"""
        config = await self.config_service.get_data_source_config()

        self.provider = DataProviderFactory.create_provider(
            source=config['data_source'],  # 'tushare'
            token=config.get('tushare_token', ''),
            retry_count=3
        )

    async def sync_daily_data(self, code: str, start_date: str, end_date: str):
        """同步日线数据（异步包装）"""
        df = await asyncio.wait_for(
            asyncio.to_thread(
                self.provider.get_daily_data,
                code=code,
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'
            ),
            timeout=30.0
        )

        # 保存到数据库
        await self.db_manager.save_daily_data(df, code)
        return len(df)
```

## 错误处理最佳实践

### 1. 积分不足处理

```python
from src.providers.tushare import TusharePermissionError

try:
    data = provider.get_minute_data('000001')
except TusharePermissionError:
    # 降级到免费数据源
    from src.providers import DataProviderFactory
    fallback = DataProviderFactory.create_provider(source='akshare')
    data = fallback.get_minute_data('000001')
```

### 2. 频率限制处理

```python
from src.providers.tushare import TushareRateLimitError
import time

def fetch_with_retry(provider, code, max_wait=300):
    """带频率限制处理的数据获取"""
    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            return provider.get_daily_data(code)

        except TushareRateLimitError as e:
            retry_count += 1
            wait_time = min(e.retry_after, max_wait)

            if retry_count < max_retries:
                print(f"频率限制，等待 {wait_time} 秒...")
                time.sleep(wait_time)
            else:
                raise
```

### 3. 批量请求错误处理

```python
def batch_fetch_with_error_handling(provider, codes):
    """批量获取，记录失败项"""
    results = {}
    errors = {}

    for code in codes:
        try:
            results[code] = provider.get_daily_data(code)
        except Exception as e:
            errors[code] = str(e)

    return results, errors

# 使用
success, failed = batch_fetch_with_error_handling(provider, codes)
print(f"成功: {len(success)}, 失败: {len(failed)}")
```

## 配置推荐

### 开发环境
```python
provider = TushareProvider(
    token='your_token',
    timeout=10,
    retry_count=1,  # 快速失败
    request_delay=0.1  # 更短间隔
)
```

### 生产环境
```python
provider = TushareProvider(
    token='your_token',
    timeout=30,
    retry_count=3,  # 容错
    request_delay=0.3  # 避免频率限制
)
```

### 高频场景
```python
provider = TushareProvider(
    token='your_token',
    timeout=60,
    retry_count=5,
    request_delay=0.5  # 更长间隔保证稳定
)
```

## 性能优化建议

### 1. 批量请求优化

```python
# 不推荐：循环单次请求
for code in codes:
    data = provider.get_daily_data(code)
    process(data)

# 推荐：使用批量接口
batch_data = provider.get_daily_batch(codes)
for code, data in batch_data.items():
    process(data)
```

### 2. 缓存结果

```python
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=128)
def get_stock_list_cached():
    """缓存股票列表"""
    return provider.get_stock_list()

# 每天更新一次
def get_stock_list_daily():
    cache_key = datetime.now().strftime('%Y-%m-%d')
    # 使用Redis或其他缓存
    ...
```

### 3. 异步并发

```python
import asyncio

async def fetch_multiple(codes):
    """并发获取多只股票数据"""
    tasks = [
        asyncio.to_thread(provider.get_daily_data, code)
        for code in codes
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理结果和异常
    valid_data = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]

    return valid_data, errors
```

## 常见问题

### Q1: 如何知道我的账户有多少积分？
A: 登录Tushare官网查看，或者尝试调用高积分接口，根据错误消息判断。

### Q2: 频率限制多久解除？
A: 通常是每分钟或每小时，具体取决于您的积分等级。建议增加 `request_delay`。

### Q3: 如何处理空数据？
A: 所有方法在无数据时返回空DataFrame，检查 `df.empty` 即可。

```python
df = provider.get_daily_data('000001')
if df.empty:
    print("无数据")
```

### Q4: 能否同时使用多个数据源？
A: 可以，创建多个Provider实例：

```python
tushare = DataProviderFactory.create_provider('tushare', token='...')
akshare = DataProviderFactory.create_provider('akshare')

# 优先用Tushare，失败则用AkShare
try:
    data = tushare.get_daily_data(code)
except Exception:
    data = akshare.get_daily_data(code)
```

## 相关文档

- [重构文档](./REFACTORING.md) - 了解模块化重构的详细信息
- [配置说明](./config.py) - 查看所有配置常量
- [异常体系](./exceptions.py) - 了解异常类型定义
- [BaseDataProvider接口](../base_provider.py) - 查看完整接口规范
