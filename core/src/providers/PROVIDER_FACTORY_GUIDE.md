# 数据提供者工厂模式使用指南

## 概述

数据提供者工厂通过工厂模式和注册机制，实现可插拔的数据源架构，支持动态注册、运行时切换和插件化扩展。

**最新重构（2026-01-26）**：
- ✅ 模块化拆分：元数据管理、注册中心、工厂入口
- ✅ 线程安全：使用 RLock 确保并发安全
- ✅ 统一日志：使用项目标准 logger
- ✅ 向后兼容：保持原有 API 接口不变

## 问题：硬编码的数据源创建

### ❌ 之前的做法

```python
# 硬编码数据源选择
if config['source'] == 'akshare':
    from providers.akshare_provider import AkShareProvider
    provider = AkShareProvider()
elif config['source'] == 'tushare':
    from providers.tushare_provider import TushareProvider
    provider = TushareProvider(token=config['token'])
else:
    raise ValueError(f"Unsupported source: {config['source']}")
```

**问题**：
1. **紧耦合**：每添加新数据源需修改条件分支
2. **难以扩展**：无法动态添加第三方数据源
3. **缺乏元数据**：不知道哪些数据源可用、需要什么参数
4. **无法发现**：无法列出所有可用的数据源

## 解决方案：工厂模式 + 注册机制

### ✅ 改进后的做法

```python
from providers.provider_factory import DataProviderFactory

# 方式1：直接创建
provider = DataProviderFactory.create_provider('akshare')

# 方式2：使用便捷函数
from providers.provider_factory import get_provider
provider = get_provider('akshare')

# 方式3：动态注册第三方提供者
DataProviderFactory.register('yahoo', YahooFinanceProvider)
provider = DataProviderFactory.create_provider('yahoo')
```

## 核心概念

### 1. 工厂类（外观模式）

```python
class DataProviderFactory:
    """数据提供者工厂（外观模式）"""

    @classmethod
    def create_provider(cls, source: str, **kwargs) -> BaseDataProvider:
        """创建提供者实例"""

    @classmethod
    def register(cls, name: str, provider_class: Type, **metadata):
        """注册新提供者"""

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """获取可用提供者列表"""
```

### 2. 元数据管理（provider_metadata.py）

```python
@dataclass
class ProviderMetadata:
    """提供者元数据（使用 dataclass）"""
    provider_class: Type[BaseDataProvider]
    description: str = ""
    requires_token: bool = False
    features: List[str] = field(default_factory=list)
    priority: int = 0

    def has_feature(self, feature: str) -> bool:
        """检查是否支持指定特性"""

    def to_dict(self) -> dict:
        """转换为字典格式"""
```

### 3. 注册中心（provider_registry.py）

```python
class ProviderRegistry:
    """数据提供者注册中心（单例 + 线程安全）"""

    @classmethod
    def register(cls, name: str, provider_class: Type, **metadata):
        """注册提供者（线程安全）"""

    @classmethod
    def get(cls, name: str) -> Optional[ProviderMetadata]:
        """获取提供者元数据"""

    @classmethod
    def filter_by_feature(cls, feature: str) -> List[str]:
        """根据特性筛选提供者"""
```

## 使用示例

### 示例 1: 基本使用

```python
from providers.provider_factory import DataProviderFactory

# 创建 AkShare 提供者（无需 Token）
provider = DataProviderFactory.create_provider('akshare')

# 获取股票列表
stocks = provider.get_stock_list()

# 获取日线数据
df = provider.get_daily_data('000001', start_date='20240101')
```

### 示例 2: 使用 Tushare（需要 Token）

```python
# 创建 Tushare 提供者
provider = DataProviderFactory.create_provider(
    'tushare',
    token='your_token_here'
)

# 使用提供者
stocks = provider.get_stock_list()
```

### 示例 3: 列出所有可用提供者

```python
# 方式1：获取名称列表
providers = DataProviderFactory.get_available_providers()
print(providers)
# 输出: ['tushare', 'akshare']  # 按优先级排序

# 方式2：获取详细信息
providers_info = DataProviderFactory.list_all_providers()
for info in providers_info:
    print(f"{info['name']}: {info['description']}")
    print(f"  需要Token: {info['requires_token']}")
    print(f"  支持特性: {', '.join(info['features'])}")
```

### 示例 4: 注册自定义提供者

```python
from providers.base_provider import BaseDataProvider
from providers.provider_factory import DataProviderFactory

class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance 数据提供者"""

    def get_stock_list(self) -> pd.DataFrame:
        # 实现获取股票列表的逻辑
        pass

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        # 实现获取日线数据的逻辑
        pass

# 注册提供者
DataProviderFactory.register(
    name='yahoo',
    provider_class=YahooFinanceProvider,
    description="Yahoo Finance 数据源（免费）",
    requires_token=False,
    features=['stock_list', 'daily_data', 'realtime_quotes'],
    priority=15  # 优先级介于 akshare(10) 和 tushare(20) 之间
)

# 使用注册的提供者
provider = DataProviderFactory.create_provider('yahoo')
```

### 示例 5: 使用装饰器自动注册

```python
from providers.base_provider import BaseDataProvider
from providers.provider_factory import provider

@provider(
    name='yahoo',
    description="Yahoo Finance 数据源",
    requires_token=False,
    features=['stock_list', 'daily_data'],
    priority=15
)
class YahooFinanceProvider(BaseDataProvider):
    """Yahoo Finance 数据提供者"""

    def get_stock_list(self) -> pd.DataFrame:
        pass

    def get_daily_data(self, code, start_date=None, end_date=None, adjust='qfq'):
        pass

# 类定义时自动注册，无需手动调用 register()
```

### 示例 6: 根据特性查找提供者

```python
# 查找支持实时行情的提供者
providers = DataProviderFactory.get_provider_by_feature('realtime_quotes')
print(f"支持实时行情的提供者: {', '.join(providers)}")

# 查找支持财务数据的提供者
providers = DataProviderFactory.get_provider_by_feature('financial_data')
print(f"支持财务数据的提供者: {', '.join(providers)}")
```

### 示例 7: 使用默认提供者

```python
# 创建默认提供者（优先级最高的）
provider = DataProviderFactory.create_default_provider()

# 或使用便捷函数
from providers.provider_factory import get_provider
provider = get_provider(DataProviderFactory.get_default_provider())
```

### 示例 8: 查看提供者详细信息

```python
# 获取单个提供者信息
info = DataProviderFactory.get_provider_info('akshare')
print(f"名称: {info['name']}")
print(f"类名: {info['class']}")
print(f"描述: {info['description']}")
print(f"需要Token: {info['requires_token']}")
print(f"支持特性: {info['features']}")
print(f"优先级: {info['priority']}")
```

## 高级用法

### 1. 动态配置

```python
# 从配置文件读取数据源
import json

with open('config.json') as f:
    config = json.load(f)

# 动态创建提供者
provider = DataProviderFactory.create_provider(
    source=config['data_source'],
    **config.get('provider_config', {})
)
```

### 2. 多数据源切换

```python
class DataManager:
    """数据管理器：支持多数据源切换"""

    def __init__(self, primary_source='tushare', fallback_source='akshare'):
        self.primary_source = primary_source
        self.fallback_source = fallback_source
        self.provider = None

    def get_data(self, code, start_date, end_date):
        """获取数据（自动切换数据源）"""
        try:
            # 尝试主数据源
            if not self.provider:
                self.provider = DataProviderFactory.create_provider(
                    self.primary_source
                )
            return self.provider.get_daily_data(code, start_date, end_date)

        except Exception as e:
            logger.warning(f"主数据源失败: {e}，切换到备用数据源")

            # 切换到备用数据源
            self.provider = DataProviderFactory.create_provider(
                self.fallback_source
            )
            return self.provider.get_daily_data(code, start_date, end_date)
```

### 3. 插件化扩展

```python
# plugin.py - 第三方插件
from providers.base_provider import BaseDataProvider
from providers.provider_factory import provider

@provider(
    name='custom',
    description="自定义数据源",
    features=['stock_list', 'daily_data'],
    priority=5
)
class CustomProvider(BaseDataProvider):
    """自定义数据提供者"""
    # 实现必要的方法
    pass

# main.py - 主程序
import plugin  # 导入插件后自动注册

# 使用插件提供的数据源
provider = DataProviderFactory.create_provider('custom')
```

### 4. 注销提供者

```python
# 注销提供者（用于测试或动态卸载插件）
success = DataProviderFactory.unregister('yahoo')
print(f"注销成功: {success}")
```

## 内置提供者

### 1. AkShare

- **名称**: `akshare`
- **描述**: AkShare 数据源（免费，无需 Token）
- **需要Token**: 否
- **支持特性**:
  - `stock_list`: 股票列表
  - `daily_data`: 日线数据
  - `realtime_quotes`: 实时行情
  - `minute_data`: 分时数据
- **优先级**: 10

### 2. Tushare

- **名称**: `tushare`
- **描述**: Tushare Pro 数据源（需要 Token 和积分）
- **需要Token**: 是
- **支持特性**:
  - `stock_list`: 股票列表
  - `daily_data`: 日线数据
  - `realtime_quotes`: 实时行情
  - `minute_data`: 分时数据
  - `financial_data`: 财务数据
- **优先级**: 20

## 便捷函数

```python
from providers.provider_factory import (
    get_provider,           # 创建提供者
    register_provider,      # 注册提供者
    list_providers,         # 列出提供者
)

# 使用便捷函数
provider = get_provider('akshare')
providers = list_providers()

# 注册新提供者
register_provider(
    'yahoo',
    YahooFinanceProvider,
    description="Yahoo Finance",
    priority=15
)
```

## 最佳实践

### 1. 配置驱动

```python
# ✅ 好：配置驱动
DATA_SOURCE_CONFIG = {
    'source': 'tushare',
    'token': os.getenv('TUSHARE_TOKEN'),
    'timeout': 30,
    'retry_count': 3,
}

provider = DataProviderFactory.create_provider(**DATA_SOURCE_CONFIG)

# ❌ 避免硬编码
provider = TushareProvider(token='hardcoded_token')
```

### 2. 错误处理

```python
try:
    provider = DataProviderFactory.create_provider('tushare')
except ValueError as e:
    logger.error(f"提供者不存在: {e}")
    # 使用默认提供者
    provider = DataProviderFactory.create_default_provider()
```

### 3. 特性检查

```python
# 检查提供者是否支持特定特性
info = DataProviderFactory.get_provider_info('akshare')

if 'financial_data' in info['features']:
    # 使用财务数据功能
    pass
else:
    # 切换到支持的提供者
    providers = DataProviderFactory.get_provider_by_feature('financial_data')
    provider = get_provider(providers[0])
```

### 4. 单元测试

```python
import unittest

class TestCustomProvider(unittest.TestCase):
    def setUp(self):
        # 注册测试提供者
        DataProviderFactory.register(
            'test',
            MockDataProvider,
            priority=100
        )

    def tearDown(self):
        # 清理
        DataProviderFactory.unregister('test')

    def test_create_provider(self):
        provider = DataProviderFactory.create_provider('test')
        self.assertIsNotNone(provider)
```

## 架构优势

| 特性 | 改进前 | 重构后（2026-01） |
|------|--------|------------------|
| **扩展性** | 修改条件分支 | 动态注册 |
| **解耦** | 紧耦合 | 松耦合 + 模块化 |
| **发现性** | 无 | 列出所有提供者 |
| **元数据** | 无 | 完整元数据（dataclass） |
| **插件化** | 不支持 | 支持第三方插件 |
| **测试性** | 难以mock | 易于测试 |
| **线程安全** | 不支持 | RLock 并发安全 |
| **代码量** | 505 行 | 388 行（工厂）+ 模块化 |

## 设计模式收益

1. **工厂模式（Factory Pattern）** ✅
   - 封装对象创建逻辑
   - 客户端无需知道具体类

2. **外观模式（Facade Pattern）** ✅
   - DataProviderFactory 作为统一入口
   - 简化复杂的子系统调用

3. **单例模式（Singleton Pattern）** ✅
   - ProviderRegistry 类级别共享
   - 全局唯一注册表

4. **注册机制（Registry Pattern）** ✅
   - 动态添加新提供者
   - 插件化扩展

5. **元数据管理** ✅
   - 使用 dataclass 简化定义
   - 提供者特性描述和优先级排序

6. **线程安全** ✅
   - RLock 可重入锁
   - 双重检查锁定模式

7. **开闭原则（Open-Closed Principle）** ✅
   - 对扩展开放
   - 对修改关闭

## 总结

使用数据提供者工厂模式的优势：

1. **可扩展** ✅: 轻松添加新数据源
2. **可插拔** ✅: 运行时动态注册
3. **可发现** ✅: 列出所有可用提供者
4. **可配置** ✅: 配置驱动的数据源选择
5. **可测试** ✅: 易于 mock 和测试

从硬编码的条件分支到灵活的工厂注册，让数据源管理更加优雅！
