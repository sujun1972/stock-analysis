# Core 开发指南

Core 是项目的核心业务逻辑库，被 backend 以 Python 包方式引用。包含：数据提供者（Tushare/AkShare）、特征工程、模型训练、回测引擎、风险管理等。

---

## 日志规范

**必须使用** `src/utils/logger.py` 中的 `get_logger`，不得使用 `print()`、标准库 `logging` 或直接从 `loguru` 导入。

```python
from src.utils.logger import get_logger

logger = get_logger(__name__)

logger.debug("调试信息：变量值 = {}", value)
logger.info("正在处理数据...")
logger.warning("警告：配置项缺失，使用默认值")
logger.error("错误：数据加载失败 - {}", error_msg)
```

**例外**：测试文件（`test_*.py` / `*_test.py`）、`__main__` 入口、CLI 模块的用户输出可用 `print()`。

使用 `/check-logging` skill 可以自动检查 core 子项目的日志规范。

---

## 异常处理规范

使用 `src/exceptions.py` 中的领域异常类，禁止抛出通用 `Exception`。

```python
from src.exceptions import (
    # 数据相关
    DataError, DataNotFoundError, DataValidationError,
    DataProviderError, InsufficientDataError,

    # 特征工程
    FeatureError, FeatureCalculationError, FeatureStorageError, FeatureCacheError,

    # 模型相关
    ModelError, ModelTrainingError, ModelPredictionError,
    ModelNotFoundError, ModelValidationError,

    # 策略和回测
    StrategyError, SignalGenerationError,
    BacktestError, BacktestExecutionError,

    # 配置相关
    ConfigError, ConfigValidationError, ConfigFileNotFoundError,

    # 风险管理
    RiskManagementError, RiskLimitExceededError, DrawdownExceededError,

    # 数据库
    DatabaseError, DatabaseConnectionError, QueryError,
)
```

**正确用法**：

```python
from src.exceptions import DataValidationError

raise DataValidationError(
    "股票代码格式不正确",
    error_code="INVALID_STOCK_CODE",
    stock_code="ABC123",
    expected_format="6位数字"
)
```

**错误用法**：

```python
# ❌ 不要这样做
raise Exception("股票代码格式不正确")
raise ValueError("数据不足")
```

使用 `/exception-handling` skill 查看完整异常类列表和示例。

---

## 统一返回格式（Response）

高层 API 函数（特征计算、回测接口、模型训练等）使用 `Response` 类返回结果：

```python
from src.utils.response import Response

def calculate_alpha_factors(data: pd.DataFrame) -> Response:
    try:
        features = AlphaFactors(data).calculate_all_alpha_factors()
        return Response.success(
            data=features,
            message="Alpha因子计算完成",
            n_features=len(features.columns),
            elapsed_time=f"{elapsed:.2f}s",
        )
    except Exception as e:
        return Response.error(
            error=f"计算失败: {str(e)}",
            error_code="CALCULATION_ERROR"
        )
```

**调用方**：

```python
result = calculate_alpha_factors(data)
if result.is_success():
    df = result.data
    print(result.metadata)  # n_features, elapsed_time 等元数据
else:
    logger.error("计算失败: {}", result.error)
```

**不需要使用 Response 的场景**：底层工具函数、内部辅助函数、简单数据格式转换。

使用 `/response-format` skill 查看完整使用指南。

---

## Provider 使用规范

```python
from src.providers import DataProviderFactory

# 正确：使用类方法创建 Provider
provider = DataProviderFactory.create_provider(source="akshare")
provider = DataProviderFactory.create_provider(source="tushare", token="xxx")

# 调用 Provider 方法（同步）
response = provider.get_daily_data(code="000001")

# 检查状态并提取数据
if not response.is_success():
    raise ExternalAPIError(
        response.error_message or "获取数据失败",
        error_code=response.error_code or "API_ERROR"
    )

df = response.data
```

**添加新 Tushare Provider 方法**（放在 `core/src/providers/tushare/_mixins/` 对应功能域 mixin）：

```python
def get_your_data(self, ts_code=None, trade_date=None, start_date=None, end_date=None,
                  limit=6000, offset=0):
    """获取数据"""
    return self._query(
        'tushare_api_name', '数据描述',
        **self._build_params(
            ts_code=ts_code, trade_date=trade_date,
            start_date=start_date, end_date=end_date,
            limit=limit, offset=offset,
        )
    )
```

**添加新 AkShare Provider 方法**（放在 `core/src/providers/akshare/_mixins/` 对应功能域 mixin）：

AkShare 已采用 Mixin 模式拆分（参考 `_mixins/news_and_anns.py`）。新增数据域时：

1. 在 `_mixins/` 下新建功能域文件，定义 `XxxMixin` 类
2. 在 `_mixins/__init__.py` 导出
3. 在 `provider.py` 的 `AkShareProvider` 多重继承链中加入（**Mixin 在前，`BaseDataProvider` 在最后**）
4. 方法内调 `self.api_client.execute(self.api_client.ak.some_function, ...)` 走重试机制，返回 `Response`

AkShare 的常见坑：部分接口（如 `stock_notice_report` / `stock_individual_notice_report`）在区间内无数据时会抛 `KeyError('代码')`（内部 pandas 空 DF 索引失败）。Mixin 方法应把它识别为"区间内无数据"的**正常语义**，降级为 `Response.warning(data=空 DataFrame)`，而非当作错误抛出。

---

## 数据库连接池

psycopg2 连接池配置在 `core/src/database/connection_pool_manager.py`（min=2, max=20）。

与 backend 的 SQLAlchemy 连接池合计约 50 个连接，总量在 PostgreSQL `max_connections=200` 安全范围内。**不要随意调大** max_conn。

---

## 数据验证

验证器位于 `core/src/data/validators/`，支持的数据类型：
- `daily_basic`, `moneyflow`, `moneyflow_hsgt`
- `margin_detail`, `stk_limit`, `adj_factor`
