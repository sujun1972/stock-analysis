# 测试指南

**Testing Guide for Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

> 💡 **快速运行测试**：查看 [../../tests/README.md](../../tests/README.md)
>
> 本文档关注**如何编写测试**，包括测试哲学、规范、最佳实践。
>
> 如需**运行测试**、查看测试统计或使用交互式菜单，请查看上述链接。

---

## 📚 文档导航

### 本文档 (测试编写指南)
- [测试哲学](#测试哲学) - 核心原则和测试金字塔
- [单元测试](#单元测试) - 编写单元测试的方法
- [集成测试](#集成测试) - 模块间交互测试
- [性能测试](#性能测试) - 性能基准测试
- [最佳实践](#最佳实践) - 测试编写技巧

### 其他测试文档
- 📋 [测试运行指南](../../tests/README.md) - 如何运行测试、交互式菜单
- 🔗 [集成测试详解](../../tests/integration/README.md) - 集成测试说明
- ⚡ [性能测试详解](../../tests/performance/README.md) - 性能基准测试
- 🖥️ [CLI测试说明](../../tests/cli/README.md) - 命令行工具测试

---

## 🎯 测试哲学

### 核心原则

- ✅ **测试覆盖率≥90%**: 所有核心代码必须有充分测试
- ✅ **测试先行**: 优先编写测试，再实现功能
- ✅ **独立性**: 每个测试独立运行，不依赖其他测试
- ✅ **可重复性**: 测试结果可重复，不受外部环境影响
- ✅ **快速反馈**: 单元测试应在秒级完成

### 测试金字塔

```
         /\
        /  \  E2E测试 (5%)
       /----\
      / 集成  \ 集成测试 (15%)
     /--------\
    /   单元    \ 单元测试 (80%)
   /____________\
```

**比例建议**:
- **单元测试**: 80% - 快速、独立、覆盖核心逻辑
- **集成测试**: 15% - 验证模块间交互
- **E2E测试**: 5% - 验证完整工作流

---

## 🧪 单元测试

### 1. 基本结构

**位置**: `tests/unit/`

**命名规范**:
```
tests/unit/
├── features/
│   ├── test_alpha_factors.py      # 测试 src/features/alpha_factors/
│   ├── test_technical_indicators.py
│   └── test_feature_engineering.py
├── models/
│   ├── test_lightgbm_model.py
│   └── test_gru_model.py
└── data/
    ├── test_database_manager.py
    └── test_data_validator.py
```

### 2. 测试用例编写

#### 基本示例

```python
# tests/unit/features/test_alpha_factors.py

import pytest
import pandas as pd
import numpy as np
from src.features.alpha_factors import calculate_momentum, calculate_volatility


class TestMomentumFactor:
    """动量因子测试套件"""

    @pytest.fixture
    def sample_data(self):
        """测试数据fixture"""
        return pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 107, 106, 108, 110, 112]
        })

    def test_basic_calculation(self, sample_data):
        """测试基本计算逻辑"""
        result = calculate_momentum(sample_data, window=5)

        # 验证返回类型
        assert isinstance(result, pd.Series)
        # 验证长度
        assert len(result) == len(sample_data)
        # 验证前期NaN
        assert result.iloc[:4].isna().all()
        # 验证数值范围
        assert result.iloc[4:].between(-1, 2).all()

    def test_edge_cases(self):
        """测试边界情况"""
        # 空数据
        empty_df = pd.DataFrame({'close': []})
        result = calculate_momentum(empty_df, window=5)
        assert len(result) == 0

        # 单个数据点
        single_df = pd.DataFrame({'close': [100]})
        result = calculate_momentum(single_df, window=5)
        assert result.isna().all()

    def test_invalid_inputs(self, sample_data):
        """测试异常输入"""
        # 无效窗口
        with pytest.raises(ValueError, match="window must be positive"):
            calculate_momentum(sample_data, window=0)

        with pytest.raises(ValueError, match="window must be positive"):
            calculate_momentum(sample_data, window=-5)

        # 缺少必需列
        invalid_df = pd.DataFrame({'price': [100, 102, 101]})
        with pytest.raises(ValueError, match="must contain 'close' column"):
            calculate_momentum(invalid_df, window=5)

    @pytest.mark.parametrize("window,expected_nan_count", [
        (5, 4),
        (10, 9),
        (20, 19)
    ])
    def test_different_windows(self, sample_data, window, expected_nan_count):
        """参数化测试：不同窗口大小"""
        result = calculate_momentum(sample_data, window=window)
        nan_count = result.isna().sum()
        assert nan_count == expected_nan_count

    def test_numerical_accuracy(self):
        """测试数值精度"""
        data = pd.DataFrame({'close': [100, 105, 110, 115, 120]})
        result = calculate_momentum(data, window=2)

        # 手动计算预期值
        expected = pd.Series([np.nan, 0.05, 0.0476, 0.0455, 0.0435])

        # 使用近似相等比较
        pd.testing.assert_series_equal(
            result,
            expected,
            check_exact=False,
            rtol=1e-3  # 相对误差容忍度
        )
```

### 3. Fixture使用

#### 共享Fixture

```python
# tests/conftest.py

import pytest
import pandas as pd
from src.data.database_manager import DatabaseManager


@pytest.fixture(scope="session")
def db_manager():
    """会话级数据库管理器"""
    manager = DatabaseManager(test_mode=True)
    yield manager
    manager.close()


@pytest.fixture(scope="module")
def sample_stock_data():
    """模块级测试数据"""
    return pd.DataFrame({
        'stock_code': ['000001.SZ'] * 100,
        'trade_date': pd.date_range('2023-01-01', periods=100),
        'open': np.random.uniform(10, 20, 100),
        'high': np.random.uniform(15, 25, 100),
        'low': np.random.uniform(5, 15, 100),
        'close': np.random.uniform(10, 20, 100),
        'volume': np.random.uniform(1000000, 5000000, 100)
    })


@pytest.fixture
def mock_api_response():
    """Mock API响应"""
    return {
        'code': 0,
        'message': 'success',
        'data': {
            'stock_code': '000001.SZ',
            'price': 15.23
        }
    }
```

#### Fixture作用域

```python
# scope="function" (默认): 每个测试函数创建一次
@pytest.fixture
def fresh_data():
    return pd.DataFrame({'value': [1, 2, 3]})

# scope="class": 每个测试类创建一次
@pytest.fixture(scope="class")
def class_data():
    return load_large_dataset()

# scope="module": 每个模块创建一次
@pytest.fixture(scope="module")
def module_data():
    return setup_database()

# scope="session": 整个测试会话创建一次
@pytest.fixture(scope="session")
def session_config():
    return load_config()
```

### 4. Mock和Patch

#### Mock外部依赖

```python
# tests/unit/data/test_data_fetcher.py

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.data.data_fetcher import StockDataFetcher


class TestStockDataFetcher:
    @pytest.fixture
    def fetcher(self):
        return StockDataFetcher()

    @patch('src.data.data_fetcher.requests.get')
    def test_fetch_stock_data(self, mock_get, fetcher):
        """Mock HTTP请求"""
        # 配置Mock返回值
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {'date': '2023-01-01', 'close': 15.23}
            ]
        }
        mock_get.return_value = mock_response

        # 执行测试
        result = fetcher.fetch('000001.SZ')

        # 验证
        assert len(result) == 1
        mock_get.assert_called_once()

    @patch('src.data.data_fetcher.DatabaseManager')
    def test_save_to_database(self, mock_db_manager, fetcher):
        """Mock数据库操作"""
        # 创建Mock实例
        mock_db_instance = MagicMock()
        mock_db_manager.return_value = mock_db_instance

        # 执行测试
        data = pd.DataFrame({'close': [15.23]})
        fetcher.save(data)

        # 验证数据库调用
        mock_db_instance.insert.assert_called_once()
```

#### Mock时间

```python
from unittest.mock import patch
from datetime import datetime


@patch('src.utils.time_utils.datetime')
def test_time_dependent_function(mock_datetime):
    """Mock时间以测试时间相关功能"""
    # 固定时间
    mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

    result = get_current_trading_day()
    assert result == '2023-01-01'
```

---

## 🔗 集成测试

### 1. 数据库集成测试

**位置**: `tests/integration/test_database_integration.py`

```python
import pytest
from src.data.database_manager import DatabaseManager
from src.data.data_validator import DataValidator


class TestDatabaseIntegration:
    @pytest.fixture(scope="class")
    def db(self):
        """测试数据库"""
        db = DatabaseManager(database="test_stock_db")
        db.create_tables()
        yield db
        db.drop_tables()
        db.close()

    def test_insert_and_query(self, db):
        """测试插入和查询"""
        # 插入测试数据
        test_data = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'trade_date': ['2023-01-01'],
            'close': [15.23]
        })
        db.insert('stock_data', test_data)

        # 查询验证
        result = db.query(
            "SELECT * FROM stock_data WHERE stock_code='000001.SZ'"
        )
        assert len(result) == 1
        assert result['close'].iloc[0] == 15.23

    def test_data_validation_pipeline(self, db):
        """测试数据验证流程"""
        # 插入无效数据
        invalid_data = pd.DataFrame({
            'stock_code': ['000001.SZ'],
            'trade_date': ['2023-01-01'],
            'close': [-999]  # 无效价格
        })

        # 验证
        validator = DataValidator()
        is_valid, errors = validator.validate(invalid_data)

        assert not is_valid
        assert 'close' in errors
```

### 2. 特征工程集成测试

```python
# tests/integration/test_feature_pipeline.py

import pytest
from src.features.feature_engineer import FeatureEngineer
from src.data.database_manager import DatabaseManager


class TestFeaturePipeline:
    @pytest.fixture(scope="class")
    def feature_engineer(self):
        return FeatureEngineer()

    def test_complete_feature_calculation(self, feature_engineer, sample_stock_data):
        """测试完整特征计算流程"""
        # 计算所有特征
        features = feature_engineer.calculate_all_features(sample_stock_data)

        # 验证特征数量
        assert len(features.columns) >= 100  # 至少100个特征

        # 验证关键特征存在
        required_features = [
            'momentum_5', 'momentum_20',
            'volatility_20', 'volatility_60',
            'rsi_14', 'macd'
        ]
        for feature in required_features:
            assert feature in features.columns

        # 验证无NaN（前期窗口除外）
        assert features.iloc[60:].notna().all().all()
```

---

## 🎭 端到端测试

### 1. 完整工作流测试

**位置**: `tests/integration/test_end_to_end_workflow.py`

```python
import pytest
from src.data.database_manager import DatabaseManager
from src.features.feature_engineer import FeatureEngineer
from src.models.model_factory import ModelFactory
from src.backtest.backtest_engine import BacktestEngine


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    @pytest.fixture(scope="class")
    def setup_environment(self):
        """设置测试环境"""
        db = DatabaseManager(database="test_e2e")
        db.create_tables()

        # 插入测试数据
        test_data = load_test_dataset()
        db.insert('stock_data', test_data)

        yield db

        db.drop_tables()
        db.close()

    def test_complete_trading_workflow(self, setup_environment):
        """测试完整交易工作流"""
        db = setup_environment

        # 1. 数据加载
        data = db.query_stock_data('000001.SZ', '2023-01-01', '2023-12-31')
        assert len(data) > 0

        # 2. 特征计算
        engineer = FeatureEngineer()
        features = engineer.calculate_all_features(data)
        assert len(features.columns) >= 100

        # 3. 模型预测
        model = ModelFactory.create_model('lightgbm')
        model.load('models/lightgbm_latest.pkl')
        predictions = model.predict(features)
        assert len(predictions) == len(features)

        # 4. 回测
        strategy = create_strategy_from_predictions(predictions)
        engine = BacktestEngine(strategy)
        result = engine.run(data)

        # 验证回测结果
        assert result.total_return is not None
        assert result.sharpe_ratio is not None
        assert result.max_drawdown < 0  # 最大回撤应为负数
```

---

## 📊 性能测试

### 1. 基准测试

```python
# tests/performance/test_feature_performance.py

import pytest
import time
from src.features.alpha_factors import calculate_all_alpha_factors


@pytest.mark.benchmark
class TestFeaturePerformance:
    """特征计算性能基准测试"""

    @pytest.fixture
    def large_dataset(self):
        """大规模测试数据"""
        return generate_test_data(n_stocks=1000, n_days=252)

    def test_feature_calculation_speed(self, large_dataset, benchmark):
        """测试特征计算速度"""
        # 使用pytest-benchmark
        result = benchmark(calculate_all_alpha_factors, large_dataset)

        # 验证性能要求
        assert benchmark.stats['mean'] < 5.0  # 平均时间<5秒

    def test_memory_usage(self, large_dataset):
        """测试内存使用"""
        import tracemalloc

        tracemalloc.start()
        features = calculate_all_alpha_factors(large_dataset)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # 验证内存使用
        peak_mb = peak / 1024 / 1024
        assert peak_mb < 500  # 峰值内存<500MB
```

### 2. 性能回归测试

```python
# tests/performance/test_performance_regression.py

import pytest
import json
from pathlib import Path


class TestPerformanceRegression:
    """性能回归测试"""

    BASELINE_FILE = Path("tests/performance/baseline.json")

    @pytest.fixture
    def baseline(self):
        """加载基准性能数据"""
        if self.BASELINE_FILE.exists():
            return json.loads(self.BASELINE_FILE.read_text())
        return {}

    def test_feature_calculation_regression(self, large_dataset, baseline):
        """特征计算性能回归测试"""
        start = time.time()
        result = calculate_all_alpha_factors(large_dataset)
        elapsed = time.time() - start

        # 与基准比较
        if 'feature_calculation' in baseline:
            baseline_time = baseline['feature_calculation']
            # 允许10%的性能波动
            assert elapsed < baseline_time * 1.1, \
                f"Performance regression: {elapsed:.2f}s > {baseline_time:.2f}s"

        # 更新基准（可选）
        baseline['feature_calculation'] = elapsed
        self.BASELINE_FILE.write_text(json.dumps(baseline, indent=2))
```

---

## 🎯 测试覆盖率

### 1. 运行覆盖率测试

```bash
# 生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term

# 只看核心模块
pytest --cov=src/features --cov=src/models --cov-report=term

# 查看缺失的行
pytest --cov=src --cov-report=term-missing
```

### 2. 覆盖率要求

**最低覆盖率标准**:
- ✅ **整体**: ≥90%
- ✅ **核心模块**: ≥95% (features, models, backtest)
- ✅ **数据层**: ≥85%
- ✅ **工具类**: ≥80%

**配置文件** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "--cov=src --cov-report=html --cov-report=term --cov-fail-under=90"

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/__init__.py",
    "*/config.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

---

## 🏃 运行测试

### 1. 基本命令

```bash
# 运行所有测试
pytest

# 运行特定目录
pytest tests/unit/features/

# 运行特定文件
pytest tests/unit/features/test_alpha_factors.py

# 运行特定测试类
pytest tests/unit/features/test_alpha_factors.py::TestMomentumFactor

# 运行特定测试方法
pytest tests/unit/features/test_alpha_factors.py::TestMomentumFactor::test_basic_calculation
```

### 2. 高级选项

```bash
# 详细输出
pytest -v

# 非常详细输出
pytest -vv

# 显示print输出
pytest -s

# 只运行失败的测试
pytest --lf

# 遇到第一个失败就停止
pytest -x

# 并行运行（需要pytest-xdist）
pytest -n 4

# 运行特定标记的测试
pytest -m "not slow"
```

### 3. 测试标记

```python
# 标记慢速测试
@pytest.mark.slow
def test_large_dataset_processing():
    pass

# 标记需要GPU的测试
@pytest.mark.gpu
def test_gpu_training():
    pass

# 标记集成测试
@pytest.mark.integration
def test_database_integration():
    pass

# 跳过测试
@pytest.mark.skip(reason="Not implemented yet")
def test_future_feature():
    pass

# 条件跳过
@pytest.mark.skipif(sys.platform == 'win32', reason="Unix only")
def test_unix_feature():
    pass
```

**运行特定标记**:
```bash
# 只运行单元测试
pytest -m "not integration and not slow"

# 只运行集成测试
pytest -m integration

# 排除慢速测试
pytest -m "not slow"
```

---

## 🔍 测试最佳实践

### 1. AAA模式

**Arrange-Act-Assert**:
```python
def test_calculate_returns():
    # Arrange: 准备测试数据
    prices = pd.Series([100, 105, 110])

    # Act: 执行被测试的代码
    returns = calculate_returns(prices)

    # Assert: 验证结果
    expected = pd.Series([np.nan, 0.05, 0.0476])
    pd.testing.assert_series_equal(returns, expected, rtol=1e-3)
```

### 2. 测试命名

```python
# ✅ 好的命名：描述测试内容
def test_momentum_returns_nan_for_insufficient_data():
    pass

def test_volatility_raises_error_for_negative_window():
    pass

def test_backtest_calculates_correct_sharpe_ratio():
    pass

# ❌ 避免：模糊的命名
def test_momentum():
    pass

def test_case_1():
    pass
```

### 3. 一个测试一个断言

```python
# ✅ 好的：每个测试一个概念
def test_momentum_returns_correct_type():
    result = calculate_momentum(data)
    assert isinstance(result, pd.Series)

def test_momentum_returns_correct_length():
    result = calculate_momentum(data)
    assert len(result) == len(data)

# ❌ 避免：测试多个不相关的概念
def test_momentum_everything():
    result = calculate_momentum(data)
    assert isinstance(result, pd.Series)  # 类型
    assert len(result) == len(data)  # 长度
    assert result.mean() > 0  # 数值
    assert result.std() < 1  # 分布
```

### 4. 使用参数化减少重复

```python
# ✅ 好的：参数化测试
@pytest.mark.parametrize("window,expected_nan_count", [
    (5, 4),
    (10, 9),
    (20, 19),
    (60, 59)
])
def test_momentum_nan_count(window, expected_nan_count):
    result = calculate_momentum(data, window=window)
    assert result.isna().sum() == expected_nan_count

# ❌ 避免：重复的测试代码
def test_momentum_window_5():
    result = calculate_momentum(data, window=5)
    assert result.isna().sum() == 4

def test_momentum_window_10():
    result = calculate_momentum(data, window=10)
    assert result.isna().sum() == 9
```

---

## 🚀 CI/CD集成

### 1. GitHub Actions配置

**文件**: `.github/workflows/tests.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest --cov=src --cov-report=xml --cov-fail-under=90

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### 2. 预提交钩子

**文件**: `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: [--cov=src, --cov-fail-under=90]
```

---

## 📚 相关文档

- 🎨 [代码规范](coding_standards.md)
- 🤝 [贡献指南](contributing.md)
- 🏗️ [架构总览](../architecture/overview.md)

---

## 📊 测试类型概览

### 测试套件统计

| 测试类型 | 文件数 | 测试数 | 覆盖范围 | 详细文档 |
|---------|--------|--------|---------|---------|
| **单元测试** | ~80 | ~2,600+ | 所有核心模块 | [tests/README.md](../../tests/README.md) |
| **集成测试** | 23 | 134 | 模块间交互 | [tests/integration/README.md](../../tests/integration/README.md) |
| **性能测试** | ~10 | ~100 | 性能基准 | [tests/performance/README.md](../../tests/performance/README.md) |
| **CLI测试** | 8 | 142 | 命令行工具 | [tests/cli/README.md](../../tests/cli/README.md) |
| **总计** | **~121** | **~2,976** | **90%+覆盖率** | - |

### 测试目录结构

```
tests/
├── README.md                    # 测试运行指南 ⭐
├── run_tests.py                 # 交互式测试运行器
│
├── unit/                        # 单元测试 (~2,600个)
│   ├── features/                # 特征层测试 (125+ Alpha因子)
│   ├── models/                  # 模型层测试 (LightGBM/GRU/Ridge)
│   ├── strategies/              # 策略层测试 (动量/均值回归/多因子)
│   ├── backtest/                # 回测引擎测试
│   ├── data/                    # 数据层测试
│   └── ...                      # 其他模块测试
│
├── integration/                 # 集成测试 (134个)
│   ├── README.md                # 集成测试说明
│   ├── test_end_to_end_workflow.py
│   ├── test_database_*.py
│   └── providers/               # 外部API集成测试
│
├── performance/                 # 性能测试 (~100个)
│   ├── README.md                # 性能基准说明
│   ├── test_feature_calculation_benchmarks.py
│   ├── test_backtest_benchmarks.py
│   └── run_benchmarks.py        # 性能测试运行器
│
└── cli/                         # CLI测试 (142个)
    ├── README.md                # CLI测试说明
    ├── utils/                   # CLI工具测试
    └── commands/                # CLI命令测试
```

### 快速开始测试

**日常开发（推荐）**:
```bash
cd tests
python run_tests.py --fast  # 快速单元测试 (~38秒)
```

**提交前检查**:
```bash
python run_tests.py --all   # 所有测试 + 覆盖率 (~4.5分钟)
```

**查看详细信息**: 参见 [tests/README.md](../../tests/README.md)

---

## ❓ 常见问题

### Q: 如何测试异步代码？

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await fetch_data_async()
    assert result is not None
```

### Q: 如何处理测试数据？

**建议**:
- 使用fixtures生成测试数据
- 避免依赖真实数据库
- 使用工厂模式创建测试对象

### Q: 测试覆盖率不够怎么办？

**步骤**:
1. 运行 `pytest --cov=src --cov-report=html`
2. 打开 `htmlcov/index.html` 查看未覆盖代码
3. 为未覆盖的边界情况添加测试

### Q: 如何测试难以复现的Bug？

**方法**:
1. 添加回归测试用例
2. 使用固定随机种子
3. Mock外部依赖

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
