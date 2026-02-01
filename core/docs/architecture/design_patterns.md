# 设计模式详解

**Design Patterns in Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 📖 概述

Stock-Analysis Core 在架构设计中广泛应用了经典设计模式，以提升代码的可维护性、可扩展性和可测试性。本文档详细介绍了项目中使用的主要设计模式。

---

## 🎯 创建型模式 (Creational Patterns)

### 1. 工厂模式 (Factory Pattern)

**应用场景**: 模型创建、数据源创建、策略创建

#### 模型工厂

**位置**: `src/models/model_factory.py`

```python
from typing import Dict, Any
from src.models.base_model import BaseModel
from src.models.lightgbm_model import LightGBMModel
from src.models.gru_model import GRUModel
from src.models.ridge_model import RidgeModel

class ModelFactory:
    """模型工厂 - 创建不同类型的机器学习模型"""

    _models = {
        "lightgbm": LightGBMModel,
        "gru": GRUModel,
        "ridge": RidgeModel
    }

    @classmethod
    def create_model(
        cls,
        model_type: str,
        **kwargs: Any
    ) -> BaseModel:
        """
        创建指定类型的模型

        Args:
            model_type: 模型类型 ('lightgbm', 'gru', 'ridge')
            **kwargs: 模型初始化参数

        Returns:
            BaseModel实例

        Raises:
            ValueError: 不支持的模型类型
        """
        if model_type not in cls._models:
            raise ValueError(
                f"Unsupported model type: {model_type}. "
                f"Available: {list(cls._models.keys())}"
            )

        model_class = cls._models[model_type]
        return model_class(**kwargs)

    @classmethod
    def register_model(cls, name: str, model_class: type):
        """注册新的模型类型"""
        cls._models[name] = model_class

# 使用示例
model = ModelFactory.create_model(
    "lightgbm",
    n_estimators=100,
    learning_rate=0.05
)
```

**优势**:
- ✅ 统一的创建接口
- ✅ 易于添加新模型类型
- ✅ 配置化模型选择

#### 数据源工厂

**位置**: `src/data/provider_factory.py`

```python
class DataProviderFactory:
    """数据源工厂"""

    _providers = {
        "akshare": AkShareProvider,
        "tushare": TushareProvider
    }

    @classmethod
    def create_provider(cls, provider_type: str) -> DataProvider:
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider: {provider_type}")
        return cls._providers[provider_type]()

# 使用示例
provider = DataProviderFactory.create_provider("akshare")
data = provider.get_stock_data("000001.SZ", "2023-01-01", "2023-12-31")
```

---

### 2. 单例模式 (Singleton Pattern)

**应用场景**: 数据库连接、配置管理、日志管理

#### 数据库管理器单例

**位置**: `src/data/database_manager.py`

```python
from threading import Lock

class DatabaseManager:
    """数据库管理器 - 单例模式确保全局唯一连接"""

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        # 初始化数据库连接
        self.engine = create_engine(DATABASE_URL)
        self._initialized = True

    def get_connection(self):
        """获取数据库连接"""
        return self.engine.connect()

# 使用示例
db1 = DatabaseManager()
db2 = DatabaseManager()
assert db1 is db2  # 同一个实例
```

**优势**:
- ✅ 避免多次创建连接
- ✅ 全局访问点
- ✅ 线程安全

#### 配置管理单例

```python
class Config:
    """配置管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        # 加载配置文件
        pass

# 全局配置访问
config = Config()
```

---

### 3. 建造者模式 (Builder Pattern)

**应用场景**: 复杂对象构建（回测配置、策略配置）

#### 回测配置建造者

**位置**: `src/backtest/backtest_builder.py`

```python
class BacktestBuilder:
    """回测配置建造者"""

    def __init__(self):
        self._config = BacktestConfig()

    def set_data_range(self, start_date: str, end_date: str):
        """设置数据范围"""
        self._config.start_date = start_date
        self._config.end_date = end_date
        return self

    def set_initial_capital(self, capital: float):
        """设置初始资金"""
        self._config.initial_capital = capital
        return self

    def set_strategy(self, strategy: BaseStrategy):
        """设置交易策略"""
        self._config.strategy = strategy
        return self

    def set_risk_manager(self, risk_manager: RiskManager):
        """设置风险管理"""
        self._config.risk_manager = risk_manager
        return self

    def build(self) -> BacktestConfig:
        """构建配置对象"""
        self._validate()
        return self._config

    def _validate(self):
        """验证配置"""
        if not self._config.strategy:
            raise ValueError("Strategy must be set")

# 使用示例
backtest_config = (BacktestBuilder()
    .set_data_range("2023-01-01", "2023-12-31")
    .set_initial_capital(1000000)
    .set_strategy(AlphaStrategy())
    .set_risk_manager(RiskManager())
    .build()
)
```

**优势**:
- ✅ 链式调用，代码清晰
- ✅ 参数验证集中
- ✅ 可选参数灵活

---

## 🏗️ 结构型模式 (Structural Patterns)

### 4. 装饰器模式 (Decorator Pattern)

**应用场景**: 异常处理、性能监控、缓存、重试

#### 异常处理装饰器

**位置**: `src/utils/decorators.py`

```python
from functools import wraps
from src.utils.exceptions import DataValidationError
from src.utils.response import Response

def handle_exceptions(func):
    """统一异常处理装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return Response.success(result)
        except DataValidationError as e:
            logger.error(f"Data validation failed: {e}")
            return Response.error(str(e), error_code="VALIDATION_ERROR")
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            return Response.error(str(e), error_code="INTERNAL_ERROR")

    return wrapper

# 使用示例
@handle_exceptions
def calculate_alpha_factor(data: pd.DataFrame) -> pd.Series:
    # 计算因子
    return alpha_values
```

#### 性能监控装饰器

```python
import time
from functools import wraps

def time_it(func):
    """性能监控装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        logger.info(f"{func.__name__} took {elapsed:.2f}s")
        return result

    return wrapper

@time_it
def compute_features(data: pd.DataFrame):
    # 计算特征
    pass
```

#### 缓存装饰器

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_stock_data(stock_code: str, date: str):
    """带缓存的数据获取"""
    return fetch_from_database(stock_code, date)
```

#### 重试装饰器

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def fetch_remote_data(url: str):
    """带重试的远程数据获取"""
    return requests.get(url)
```

**优势**:
- ✅ 横切关注点分离
- ✅ 可组合使用
- ✅ 不修改原函数

---

### 5. 适配器模式 (Adapter Pattern)

**应用场景**: 数据源适配、第三方库封装

#### 数据源适配器

**位置**: `src/data/providers/`

```python
class DataProvider(ABC):
    """数据源接口（目标接口）"""

    @abstractmethod
    def get_stock_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        pass

class AkShareProvider(DataProvider):
    """AkShare数据源适配器"""

    def get_stock_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        # 调用AkShare API并转换为标准格式
        raw_data = ak.stock_zh_a_hist(
            symbol=stock_code,
            start_date=start_date,
            end_date=end_date
        )
        return self._standardize_format(raw_data)

    def _standardize_format(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """转换为标准格式"""
        return raw_data.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            # ...
        })

class TushareProvider(DataProvider):
    """Tushare数据源适配器"""

    def get_stock_data(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        # 调用Tushare API并转换为标准格式
        raw_data = ts.pro_bar(
            ts_code=stock_code,
            start_date=start_date,
            end_date=end_date
        )
        return self._standardize_format(raw_data)
```

**优势**:
- ✅ 统一接口
- ✅ 易于切换数据源
- ✅ 隐藏实现细节

---

### 6. 代理模式 (Proxy Pattern)

**应用场景**: 特征缓存、延迟加载

#### 特征缓存代理

```python
class FeatureStoreProxy:
    """特征存储代理 - 提供缓存功能"""

    def __init__(self, feature_store: FeatureStore):
        self._feature_store = feature_store
        self._cache = {}

    def get_features(
        self,
        stock_code: str,
        feature_names: List[str]
    ) -> pd.DataFrame:
        cache_key = f"{stock_code}_{','.join(feature_names)}"

        if cache_key in self._cache:
            logger.debug(f"Cache hit for {cache_key}")
            return self._cache[cache_key]

        logger.debug(f"Cache miss for {cache_key}")
        features = self._feature_store.get_features(stock_code, feature_names)
        self._cache[cache_key] = features
        return features
```

---

## 🎭 行为型模式 (Behavioral Patterns)

### 7. 策略模式 (Strategy Pattern)

**应用场景**: 交易策略、特征选择策略

#### 交易策略

**位置**: `src/strategies/`

```python
class BaseStrategy(ABC):
    """策略接口"""

    @abstractmethod
    def generate_signals(
        self,
        data: pd.DataFrame
    ) -> pd.Series:
        """
        生成交易信号

        Returns:
            pd.Series: 1=买入, -1=卖出, 0=持有
        """
        pass

class AlphaStrategy(BaseStrategy):
    """Alpha策略"""

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        alpha = self.calculate_alpha(data)
        return (alpha > 0.5).astype(int) * 2 - 1

class MeanReversionStrategy(BaseStrategy):
    """均值回归策略"""

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        mean = data['close'].rolling(20).mean()
        std = data['close'].rolling(20).std()
        z_score = (data['close'] - mean) / std
        return (z_score < -2).astype(int) * 2 - 1

# 策略使用
class BacktestEngine:
    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy  # 注入策略

    def run(self, data: pd.DataFrame):
        signals = self.strategy.generate_signals(data)
        # 执行回测逻辑
```

**优势**:
- ✅ 算法与使用分离
- ✅ 易于添加新策略
- ✅ 运行时切换策略

---

### 8. 观察者模式 (Observer Pattern)

**应用场景**: 事件监听、状态变化通知

#### 回测事件监听

```python
class BacktestObserver(ABC):
    """回测观察者接口"""

    @abstractmethod
    def on_trade(self, trade_event: TradeEvent):
        pass

    @abstractmethod
    def on_position_change(self, position_event: PositionEvent):
        pass

class PerformanceMonitor(BacktestObserver):
    """性能监控观察者"""

    def on_trade(self, trade_event: TradeEvent):
        logger.info(f"Trade executed: {trade_event}")
        self.update_metrics(trade_event)

    def on_position_change(self, position_event: PositionEvent):
        logger.info(f"Position changed: {position_event}")

class BacktestEngine:
    def __init__(self):
        self._observers: List[BacktestObserver] = []

    def attach(self, observer: BacktestObserver):
        """添加观察者"""
        self._observers.append(observer)

    def _notify_trade(self, trade_event: TradeEvent):
        """通知所有观察者"""
        for observer in self._observers:
            observer.on_trade(trade_event)

# 使用示例
engine = BacktestEngine()
engine.attach(PerformanceMonitor())
engine.attach(RiskMonitor())
```

---

### 9. 模板方法模式 (Template Method Pattern)

**应用场景**: 模型训练流程、回测流程

#### 模型训练模板

**位置**: `src/models/base_model.py`

```python
class BaseModel(ABC):
    """模型基类 - 定义训练流程模板"""

    def train(self, X: pd.DataFrame, y: pd.Series):
        """训练流程模板方法"""
        # 1. 数据预处理（子类可覆盖）
        X_processed = self.preprocess(X)

        # 2. 模型训练（子类必须实现）
        self._fit(X_processed, y)

        # 3. 后处理（子类可覆盖）
        self.postprocess()

    def preprocess(self, X: pd.DataFrame) -> pd.DataFrame:
        """数据预处理（钩子方法）"""
        return X  # 默认不处理

    @abstractmethod
    def _fit(self, X: pd.DataFrame, y: pd.Series):
        """模型训练（抽象方法）"""
        pass

    def postprocess(self):
        """后处理（钩子方法）"""
        pass  # 默认不处理

class LightGBMModel(BaseModel):
    """LightGBM模型"""

    def preprocess(self, X: pd.DataFrame) -> pd.DataFrame:
        # 特定的预处理
        return X.fillna(0)

    def _fit(self, X: pd.DataFrame, y: pd.Series):
        # LightGBM训练逻辑
        self.model = lgb.train(params, train_data)
```

**优势**:
- ✅ 流程复用
- ✅ 步骤可定制
- ✅ 控制反转

---

### 10. 命令模式 (Command Pattern)

**应用场景**: CLI命令、回测任务调度

#### CLI命令

**位置**: `bin/stock-cli`

```python
class Command(ABC):
    """命令接口"""

    @abstractmethod
    def execute(self):
        pass

class DownloadCommand(Command):
    """下载数据命令"""

    def __init__(self, stock_codes: List[str], start_date: str):
        self.stock_codes = stock_codes
        self.start_date = start_date

    def execute(self):
        for code in self.stock_codes:
            download_stock_data(code, self.start_date)

class BacktestCommand(Command):
    """回测命令"""

    def __init__(self, strategy: str, config: Dict):
        self.strategy = strategy
        self.config = config

    def execute(self):
        run_backtest(self.strategy, self.config)

# CLI调度器
class CommandInvoker:
    def __init__(self):
        self.commands = []

    def add_command(self, command: Command):
        self.commands.append(command)

    def execute_all(self):
        for command in self.commands:
            command.execute()
```

---

## 📊 模式使用统计

| 模式 | 应用场景数 | 代码位置 |
|------|-----------|---------|
| 工厂模式 | 3 | models/, data/providers/, strategies/ |
| 单例模式 | 2 | data/, utils/ |
| 装饰器模式 | 4 | utils/decorators.py |
| 策略模式 | 5 | strategies/ |
| 适配器模式 | 2 | data/providers/ |
| 模板方法 | 2 | models/, backtest/ |
| 观察者模式 | 1 | backtest/ |

---

## 🎯 最佳实践

1. **选择合适的模式**: 不要过度设计
2. **保持简单**: 优先考虑代码可读性
3. **遵循SOLID原则**: 单一职责、开闭原则等
4. **编写测试**: 模式应该提升可测试性
5. **文档化**: 说明使用的模式和原因

---

## 📚 相关文档

- 🏗️ [架构总览详解](overview.md)
- ⚡ [性能优化分析](performance.md)
- 🔧 [技术栈详解](tech_stack.md)

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
