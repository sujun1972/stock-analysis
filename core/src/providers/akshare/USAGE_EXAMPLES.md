# AkShare Provider 使用示例

## 📖 目录

1. [基础使用](#基础使用)
2. [股票列表](#股票列表)
3. [日线数据](#日线数据)
4. [分时数据](#分时数据)
5. [实时行情](#实时行情)
6. [异常处理](#异常处理)
7. [高级配置](#高级配置)

## 基础使用

### 初始化提供者

```python
from src.providers.akshare import AkShareProvider

# 使用默认配置
provider = AkShareProvider()

# 自定义配置
provider = AkShareProvider(
    timeout=60,           # 请求超时 60 秒
    retry_count=5,        # 失败重试 5 次
    retry_delay=2,        # 重试延迟 2 秒
    request_delay=0.5     # 请求间隔 0.5 秒
)
```

## 股票列表

### 获取全部 A 股列表

```python
# 获取所有 A 股
stock_list = provider.get_stock_list()
print(f"共 {len(stock_list)} 只股票")
print(stock_list.head())

# 输出示例：
#      code  name    market  status
# 0  000001  平安银行  深圳主板    正常
# 1  000002  万科A   深圳主板    正常
# 2  000004  国华网安  深圳主板    正常
```

### 获取新股

```python
# 获取最近 30 天上市的新股
new_stocks = provider.get_new_stocks(days=30)
print(f"最近30天新股: {len(new_stocks)} 只")
print(new_stocks)

# 输出字段：code, name, market, list_date, status
```

### 获取退市股票

```python
# 获取退市股票列表
delisted = provider.get_delisted_stocks()
print(f"退市股票: {len(delisted)} 只")
print(delisted.head())

# 输出字段：code, name, list_date, delist_date, market
```

## 日线数据

### 获取单只股票日线数据

```python
# 获取平安银行最近一年的日线数据（前复权）
df = provider.get_daily_data(
    code='000001',
    start_date='20230101',
    end_date='20231231',
    adjust='qfq'  # 前复权：'qfq', 后复权：'hfq', 不复权：''
)

print(f"数据条数: {len(df)}")
print(df.head())

# 输出字段：
# trade_date, open, high, low, close, volume, amount,
# amplitude, pct_change, change_amount, turnover
```

### 批量获取多只股票

```python
# 批量获取日线数据
codes = ['000001', '000002', '600000']
data_dict = provider.get_daily_batch(
    codes=codes,
    start_date='20230101',
    end_date='20231231',
    adjust='qfq'
)

for code, df in data_dict.items():
    print(f"{code}: {len(df)} 条数据")
```

## 分时数据

### 获取分钟级数据

```python
# 获取 5 分钟数据
df = provider.get_minute_data(
    code='000001',
    period='5',  # 可选：'1', '5', '15', '30', '60'
    start_date='2023-12-01 09:30:00',
    end_date='2023-12-01 15:00:00',
    adjust=''  # 分时数据一般不复权
)

print(f"分时数据: {len(df)} 条")
print(df.head())

# 输出字段：
# trade_time, period, open, high, low, close, volume,
# amount, amplitude, pct_change, change_amount, turnover
```

## 实时行情

### 获取指定股票实时行情

```python
# 获取少量股票实时行情（推荐方式，速度快）
codes = ['000001', '000002', '600000', '600036']
quotes = provider.get_realtime_quotes(codes=codes)

print(quotes)

# 输出字段：
# code, name, latest_price, open, high, low, pre_close,
# volume, amount, pct_change, change_amount, turnover,
# amplitude, trade_time
```

### 获取全部股票实时行情

```python
# 注意：全量获取需要 3-5 分钟，谨慎使用！
quotes = provider.get_realtime_quotes()  # codes=None 表示全部

print(f"获取了 {len(quotes)} 只股票的实时行情")
```

### 使用回调函数增量保存

```python
def save_quote(quote_dict):
    """每获取一条数据就立即保存到数据库"""
    print(f"保存 {quote_dict['code']} 的数据")
    # 这里可以调用数据库保存逻辑
    # db.save(quote_dict)

# 使用回调函数
codes = ['000001', '000002', '600000']
quotes = provider.get_realtime_quotes(
    codes=codes,
    save_callback=save_quote  # 每获取一条就调用
)
```

## 异常处理

### 捕获特定异常

```python
from src.providers.akshare import AkShareProvider
from src.providers.akshare.exceptions import (
    AkShareDataError,
    AkShareRateLimitError,
    AkShareTimeoutError,
    AkShareNetworkError
)

provider = AkShareProvider()

try:
    df = provider.get_stock_list()
except AkShareRateLimitError as e:
    print(f"IP 限流: {e}")
    print("建议：等待一段时间后重试")
except AkShareTimeoutError as e:
    print(f"请求超时: {e}")
    print("建议：检查网络连接或增加超时时间")
except AkShareNetworkError as e:
    print(f"网络错误: {e}")
    print("建议：检查网络连接")
except AkShareDataError as e:
    print(f"数据获取失败: {e}")
except Exception as e:
    print(f"未知错误: {e}")
```

## 高级配置

### 自定义配置参数

```python
from src.providers.akshare import AkShareProvider
from src.providers.akshare.config import AkShareConfig

# 查看默认配置
print(f"默认超时: {AkShareConfig.DEFAULT_TIMEOUT} 秒")
print(f"默认重试: {AkShareConfig.DEFAULT_RETRY_COUNT} 次")
print(f"默认延迟: {AkShareConfig.DEFAULT_REQUEST_DELAY} 秒")

# 创建自定义配置的提供者
provider = AkShareProvider(
    timeout=AkShareConfig.DEFAULT_TIMEOUT * 2,  # 加倍超时时间
    retry_count=AkShareConfig.DEFAULT_RETRY_COUNT + 2,  # 增加重试次数
    request_delay=AkShareConfig.DEFAULT_REQUEST_DELAY * 2  # 增加请求间隔
)
```

### 市场类型解析

```python
from src.providers.akshare.config import AkShareConfig

# 解析股票代码的市场类型
codes = ['000001', '600000', '300001', '688001', '430001']
for code in codes:
    market = AkShareConfig.parse_market_from_code(code)
    print(f"{code}: {market}")

# 输出：
# 000001: 深圳主板
# 600000: 上海主板
# 300001: 创业板
# 688001: 科创板
# 430001: 北交所
```

## 🚨 使用注意事项

### 1. IP 限流风险
```python
# ❌ 错误：频繁请求会导致 IP 限流
provider = AkShareProvider(request_delay=0.1)  # 间隔太短

# ✅ 正确：使用合理的请求间隔
provider = AkShareProvider(request_delay=0.3)  # 推荐 >= 0.3 秒
```

### 2. 实时行情性能
```python
# ❌ 错误：全量获取实时行情太慢（3-5分钟）
quotes = provider.get_realtime_quotes()  # 不推荐

# ✅ 正确：指定股票代码列表（快速）
codes = ['000001', '000002', '600000']
quotes = provider.get_realtime_quotes(codes=codes)  # 推荐
```

### 3. 日期格式
```python
# 支持多种日期格式
df = provider.get_daily_data('000001', start_date='20230101')  # YYYYMMDD
df = provider.get_daily_data('000001', start_date='2023-01-01')  # YYYY-MM-DD
df = provider.get_daily_data('000001', start_date='2023/01/01')  # YYYY/MM/DD
```

## 📚 更多示例

查看项目中的完整测试用例：
- 单元测试：`tests/unit/test_akshare_provider.py`
- 集成测试：`tests/integration/test_akshare_integration.py`

## 🔗 相关文档

- [重构说明](./REFACTORING.md)
- [配置详解](./config.py)
- [异常处理](./exceptions.py)
