# Alpha因子测试完整指南

## 📦 测试套件总览

### 测试文件
- **test_alpha_factors.py** - 基础功能测试（46+用例）
- **test_alpha_factors_extended.py** - 扩展深度测试（35+用例）
- **run_alpha_tests.sh** - 自动化测试脚本

### 总计：80+ 测试用例，覆盖率目标 95%+

---

## 🚀 快速开始

### 运行所有测试
```bash
cd core/tests
./run_alpha_tests.sh
```

### 运行基础测试
```bash
pytest unit/test_alpha_factors.py -v
```

### 运行扩展测试
```bash
pytest unit/test_alpha_factors_extended.py -v
```

### 查看覆盖率
```bash
pytest unit/test_alpha_factors*.py --cov=src/features/alpha_factors --cov-report=html
open htmlcov/index.html
```

---

## 📋 测试分类

### 1️⃣ 基础功能测试 (46+用例)

#### 配置测试 (3个)
- 默认周期配置
- 列名映射
- 常量配置

#### 计算器测试 (32个)
- **动量** (7个): 初始化、验证、因子计算、inplace
- **反转** (4个): 反转因子、隔夜反转、缺失列处理
- **波动率** (4个): 波动率、Parkinson波动率
- **成交量** (4个): 成交量因子、价量相关性
- **趋势** (3个): 趋势强度、突破因子
- **流动性** (2个): 流动性因子、缺失列处理
- **主类** (8个): 完整集成测试

#### 工具测试 (11个)
- 便捷函数 (3个)
- 边界情况 (5个)
- 性能测试 (2个)

---

### 2️⃣ 扩展深度测试 (35+用例)

#### 数据质量 (4个)
- ✅ 无穷大值检查
- ✅ NaN比例检查
- ✅ 值范围检查
- ✅ 稳定性检查

#### 计算正确性 (4个)
- ✅ 动量精度验证
- ✅ 波动率精度验证
- ✅ Z-score特性验证
- ✅ 突破边界验证

#### 性能测试 (4个)
- ✅ 大数据集测试
- ✅ 内存效率测试
- ✅ 缓存效率测试
- ✅ 并发独立性测试

#### 集成测试 (3个)
- ✅ 完整流程测试
- ✅ 混合使用测试
- ✅ 真实场景测试

#### 边界情况 (5个)
- ✅ 全NaN处理
- ✅ 极端波动处理
- ✅ 价格跳空处理
- ✅ 零成交量处理
- ✅ 重复索引处理

#### 其他测试 (15个)
- 日志和错误处理
- 因子关系验证
- 等等

---

## 🎯 测试覆盖矩阵

| 模块 | 单元测试 | 集成测试 | 性能测试 | 边界测试 | 总计 |
|------|----------|----------|----------|----------|------|
| FactorConfig | ✅ 3 | - | - | - | 3 |
| BaseFactorCalculator | ✅ 2 | ✅ 2 | ✅ 2 | ✅ 1 | 7 |
| MomentumFactorCalculator | ✅ 7 | ✅ 2 | ✅ 1 | ✅ 2 | 12 |
| ReversalFactorCalculator | ✅ 4 | ✅ 1 | - | ✅ 1 | 6 |
| VolatilityFactorCalculator | ✅ 4 | ✅ 1 | - | ✅ 2 | 7 |
| VolumeFactorCalculator | ✅ 4 | ✅ 1 | - | ✅ 2 | 7 |
| TrendFactorCalculator | ✅ 3 | ✅ 1 | - | ✅ 1 | 5 |
| LiquidityFactorCalculator | ✅ 2 | ✅ 1 | - | ✅ 1 | 4 |
| AlphaFactors | ✅ 8 | ✅ 3 | ✅ 2 | ✅ 2 | 15 |
| 便捷函数 | ✅ 3 | - | - | - | 3 |
| 数据质量 | - | - | - | ✅ 4 | 4 |
| 因子关系 | - | ✅ 2 | - | - | 2 |
| **总计** | **40** | **14** | **5** | **16** | **75+** |

---

## 📊 测试命令速查

### 基础命令

```bash
# 运行所有测试
pytest unit/test_alpha_factors*.py -v

# 运行并显示输出
pytest unit/test_alpha_factors*.py -v -s

# 运行失败时停止
pytest unit/test_alpha_factors*.py -x

# 最多失败5次后停止
pytest unit/test_alpha_factors*.py --maxfail=5
```

### 筛选测试

```bash
# 按名称筛选
pytest unit/test_alpha_factors.py -k "momentum"

# 按标记筛选（如果有）
pytest unit/test_alpha_factors.py -m "slow"

# 运行特定类
pytest unit/test_alpha_factors.py::TestMomentumFactorCalculator

# 运行特定方法
pytest unit/test_alpha_factors.py::TestMomentumFactorCalculator::test_add_momentum_factors
```

### 调试命令

```bash
# 在失败时进入pdb
pytest unit/test_alpha_factors.py --pdb

# 显示详细追踪
pytest unit/test_alpha_factors.py --tb=long

# 只运行上次失败的测试
pytest unit/test_alpha_factors.py --lf

# 先运行失败的测试
pytest unit/test_alpha_factors.py --ff
```

### 覆盖率命令

```bash
# 基础覆盖率
pytest unit/test_alpha_factors*.py --cov=src/features/alpha_factors

# HTML报告
pytest unit/test_alpha_factors*.py \
    --cov=src/features/alpha_factors \
    --cov-report=html

# 显示缺失行
pytest unit/test_alpha_factors*.py \
    --cov=src/features/alpha_factors \
    --cov-report=term-missing

# XML报告（CI用）
pytest unit/test_alpha_factors*.py \
    --cov=src/features/alpha_factors \
    --cov-report=xml
```

---

## 💡 编写测试技巧

### 1. 使用Fixtures

```python
@pytest.fixture
def sample_data():
    """创建测试数据"""
    return create_test_data()

def test_function(sample_data):
    result = process(sample_data)
    assert result is not None
```

### 2. 参数化测试

```python
@pytest.mark.parametrize("period,expected", [
    (5, "MOM5"),
    (10, "MOM10"),
    (20, "MOM20"),
])
def test_momentum_periods(period, expected, sample_data):
    calc = MomentumFactorCalculator(sample_data)
    result = calc.add_momentum_factors(periods=[period])
    assert expected in result.columns
```

### 3. 异常测试

```python
def test_invalid_input():
    with pytest.raises(ValueError, match="缺少必需的列"):
        AlphaFactors(pd.DataFrame({'open': [1, 2, 3]}))
```

### 4. 浮点数比较

```python
import numpy as np

def test_calculation_accuracy():
    result = calculate_value()
    expected = 1.23456789
    assert np.isclose(result, expected, rtol=1e-5)
```

### 5. Mock和Patch

```python
from unittest.mock import patch, MagicMock

def test_with_mock():
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked"
        result = call_function()
        assert result == "mocked"
```

---

## 🔍 常见测试场景

### 场景1: 测试新增因子

```python
def test_new_custom_factor(sample_price_data):
    """测试新增的自定义因子"""
    calc = MomentumFactorCalculator(sample_price_data)
    result = calc.add_custom_factor()

    # 检查因子是否创建
    assert 'CUSTOM_FACTOR' in result.columns

    # 检查值的合理性
    factor_values = result['CUSTOM_FACTOR'].dropna()
    assert len(factor_values) > 0
    assert not np.isinf(factor_values).any()
    assert factor_values.std() > 0  # 有变化
```

### 场景2: 测试边界条件

```python
def test_extreme_values():
    """测试极端值处理"""
    # 创建包含极端值的数据
    df = pd.DataFrame({
        'close': [1e-10, 1e10, 100, 200, 300]
    })

    af = AlphaFactors(df)
    result = af.add_momentum_factors(periods=[2])

    # 验证没有产生无穷大
    assert not np.isinf(result['MOM2']).any()
```

### 场景3: 测试性能

```python
import time

def test_performance_benchmark(large_price_data):
    """性能基准测试"""
    af = AlphaFactors(large_price_data)

    start = time.time()
    result = af.add_all_alpha_factors()
    elapsed = time.time() - start

    # 1000行数据应在10秒内完成
    assert elapsed < 10.0
    print(f"处理时间: {elapsed:.2f}秒")
```

### 场景4: 测试数据质量

```python
def test_factor_quality(sample_price_data):
    """测试因子数据质量"""
    af = AlphaFactors(sample_price_data)
    result = af.add_all_alpha_factors()

    for factor in af.get_factor_names():
        # 检查NaN比例
        nan_ratio = result[factor].isna().sum() / len(result)
        assert nan_ratio < 0.5, f"{factor} NaN比例过高"

        # 检查有效值
        valid = result[factor].dropna()
        if len(valid) > 0:
            # 不应该全是相同值
            assert valid.std() > 0, f"{factor} 没有变化"
```

---

## 📈 性能基准

| 操作 | 数据量 | 目标时间 |
|------|--------|----------|
| 所有因子 | 300行 | < 2秒 |
| 所有因子 | 1000行 | < 10秒 |
| 动量因子 | 300行 | < 0.3秒 |
| 波动率因子 | 300行 | < 0.4秒 |
| 成交量因子 | 300行 | < 0.3秒 |
| 趋势因子 | 300行 | < 0.5秒 |

---

## ✅ 测试检查清单

提交前确保：

- [ ] 所有测试通过 (`pytest unit/test_alpha_factors*.py`)
- [ ] 覆盖率 >= 95% (`--cov`)
- [ ] 无跳过的测试
- [ ] 性能测试通过
- [ ] 边界测试通过
- [ ] 代码lint通过
- [ ] 文档已更新

---

## 🆘 故障排除

### 问题1: 测试无法找到模块

```bash
# 解决方案：确保路径正确
cd core
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest tests/unit/test_alpha_factors.py
```

### 问题2: 测试超时

```bash
# 增加超时时间
pytest tests/unit/test_alpha_factors.py --timeout=300
```

### 问题3: 内存不足

```bash
# 逐个运行测试文件
pytest tests/unit/test_alpha_factors.py
pytest tests/unit/test_alpha_factors_extended.py
```

### 问题4: 随机失败

```bash
# 固定随机种子
np.random.seed(42)
```

---

## 📚 相关文档

- [alpha_factors.py](../src/features/alpha_factors.py) - 主模块
- [重构总结](../../ALPHA_FACTORS_REFACTORING_SUMMARY.md) - 重构文档
- [test_alpha_factors.py](unit/test_alpha_factors.py) - 基础测试
- [test_alpha_factors_extended.py](unit/test_alpha_factors_extended.py) - 扩展测试

---

**最后更新：** 2026-01-27
