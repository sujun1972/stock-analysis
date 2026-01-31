# 性能基准测试套件

> 基于 REFACTORING_PLAN.md 任务 1.2: 性能基准测试套件

## 概述

本性能基准测试套件用于检测性能回归,确保代码优化不会导致性能劣化。所有性能阈值基于 REFACTORING_PLAN.md 中定义的性能目标。

## 性能目标

### 特征计算性能 (test_feature_calculation_benchmarks.py)

| 测试项 | 性能目标 | 数据规模 |
|--------|---------|----------|
| 125个Alpha因子计算 | < 60秒 | 1000股×250天 |
| 60+技术指标计算 | < 30秒 | 1000股×250天 |
| 单因子平均计算 | < 0.5秒 | 单股票×250天 |
| 动量因子计算 | < 0.5秒 | 单股票×1000天 |
| 反转因子计算 | < 0.5秒 | 单股票×1000天 |
| 波动率因子计算 | < 0.5秒 | 单股票×1000天 |

### 回测性能 (test_backtest_benchmarks.py)

| 测试项 | 性能目标 | 数据规模 |
|--------|---------|----------|
| 向量化回测 | < 3秒 | 1000股×250天 |
| 多头策略回测 | < 2秒 | 100股×250天 |
| 市场中性策略 | < 5秒 | 100股×250天 |
| 性能指标计算 | < 0.5秒 | 回测结果 |
| 回撤分析 | < 0.3秒 | 回测结果 |

### 数据库性能 (test_database_and_model_benchmarks.py)

| 测试项 | 性能目标 | 数据规模 |
|--------|---------|----------|
| 单股票查询 | < 10ms | 1年数据 |
| 批量查询100股 | < 500ms | 100股×1年 |
| 特征写入 | < 1秒 | 1000行×50特征 |

### 模型训练性能 (test_database_and_model_benchmarks.py)

| 测试项 | 性能目标 | 数据规模 |
|--------|---------|----------|
| LightGBM训练 | < 10秒 | 10万样本×125特征 |
| LightGBM预测 | < 0.1秒 | 2000样本 |
| GRU训练(CPU) | < 60秒 | 1000样本×20序列×50特征 |
| GRU训练(GPU) | < 5秒 | 1000样本×20序列×50特征 |

## 文件结构

```
tests/performance/
├── README.md                              # 本文件
├── benchmarks.py                          # 基准测试框架和工具
├── test_feature_calculation_benchmarks.py # 特征计算性能测试
├── test_backtest_benchmarks.py            # 回测性能测试
├── test_database_and_model_benchmarks.py  # 数据库和模型性能测试
└── run_benchmarks.py                      # 测试运行器和报告生成器
```

## 快速开始

### 1. 运行所有性能测试

```bash
cd /Volumes/MacDriver/stock-analysis/core/tests/performance

# 运行所有测试
python run_benchmarks.py

# 或使用pytest直接运行
pytest test_*.py -v
```

### 2. 运行特定类别的测试

```bash
# 只运行特征计算测试
python run_benchmarks.py --category feature

# 只运行回测测试
python run_benchmarks.py --category backtest

# 只运行数据库测试
python run_benchmarks.py --category database

# 只运行模型训练测试
python run_benchmarks.py --category model
```

### 3. 生成HTML性能报告

```bash
# 运行测试并生成报告
python run_benchmarks.py --output benchmark_report.html

# 在浏览器中查看报告
open benchmark_report.html  # macOS
# 或
xdg-open benchmark_report.html  # Linux
```

## 使用pytest运行

### 运行单个测试文件

```bash
# 特征计算测试
pytest test_feature_calculation_benchmarks.py -v

# 回测测试
pytest test_backtest_benchmarks.py -v

# 数据库和模型测试
pytest test_database_and_model_benchmarks.py -v
```

### 运行特定测试类

```bash
# 只运行Alpha因子性能测试
pytest test_feature_calculation_benchmarks.py::TestAlphaFactorsPerformance -v

# 只运行回测引擎性能测试
pytest test_backtest_benchmarks.py::TestBacktestEnginePerformance -v

# 只运行LightGBM性能测试
pytest test_database_and_model_benchmarks.py::TestLightGBMPerformance -v
```

### 运行单个测试方法

```bash
# 测试所有Alpha因子计算性能
pytest test_feature_calculation_benchmarks.py::TestAlphaFactorsPerformance::test_all_alpha_factors_benchmark -v

# 测试向量化回测性能
pytest test_backtest_benchmarks.py::TestBacktestEnginePerformance::test_vectorized_backtest_large_scale -v
```

## 性能报告解读

### 测试输出格式

```
✓ 所有Alpha因子计算(单股票): 2.345s (余量: 53.1%)
  实际耗时: 2.345s
  性能阈值: 5.000s
  性能余量: 53.1% (距离阈值还有53.1%的空间)
```

### 性能状态

- **✓ PASS**: 性能满足要求,在阈值内
- **✗ FAIL**: 性能回归,超过阈值

### 性能余量

- **正余量** (如 +50%): 实际性能优于阈值,还有50%的优化空间
- **负余量** (如 -20%): 性能劣化,比阈值慢了20%

## CI/CD集成

### GitHub Actions示例

在 `.github/workflows/performance.yml` 中添加:

```yaml
name: Performance Benchmarks

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-benchmark

      - name: Run performance benchmarks
        run: |
          cd tests/performance
          python run_benchmarks.py --output benchmark_report.html

      - name: Upload performance report
        uses: actions/upload-artifact@v2
        with:
          name: performance-report
          path: tests/performance/benchmark_report.html

      - name: Check performance regression
        run: |
          cd tests/performance
          pytest test_*.py --tb=short
```

## 性能优化建议

### 如果测试失败

1. **检查代码变更**: 查看最近的代码修改是否引入了性能问题
2. **分析瓶颈**: 使用 `cProfile` 或 `line_profiler` 找出性能瓶颈
3. **优化建议**:
   - 使用向量化操作替代循环
   - 减少不必要的数据复制
   - 使用缓存机制
   - 优化数据库查询
   - 使用并行计算

### 性能剖析示例

```python
# 使用cProfile分析性能
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# 运行要分析的代码
alpha = AlphaFactors(data)
result = alpha.add_all_alpha_factors()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 打印前20个最慢的函数
```

## 扩展基准测试

### 添加新的性能测试

1. 在相应的测试文件中添加测试方法
2. 使用 `PerformanceBenchmarkBase` 基类
3. 定义性能阈值
4. 使用 `assert_performance` 进行断言

示例:

```python
class TestNewFeaturePerformance(PerformanceBenchmarkBase):
    """新特性性能测试"""

    def test_new_feature_benchmark(self, test_data):
        """测试新特性性能"""
        print_benchmark_header("新特性性能测试")

        # 执行测试
        start = time.time()
        result = new_feature_function(test_data)
        elapsed = time.time() - start

        # 性能断言
        threshold = 1.0  # 定义阈值
        self.assert_performance(
            elapsed,
            threshold,
            "新特性测试",
            {'data_size': len(test_data)}
        )
```

## 性能基线管理

### 保存性能基线

```bash
# 运行测试并保存结果
pytest test_*.py --benchmark-save=baseline

# 与基线比较
pytest test_*.py --benchmark-compare=baseline
```

### 性能趋势追踪

建议在CI/CD中保存每次的性能测试结果,用于追踪性能趋势:

```bash
# 保存带时间戳的结果
DATE=$(date +%Y%m%d_%H%M%S)
pytest test_*.py --benchmark-save=perf_$DATE
```

## 故障排查

### 常见问题

1. **测试数据生成慢**
   - 使用缓存的测试数据
   - 减小测试数据规模

2. **测试超时**
   - 增加pytest超时时间: `pytest --timeout=300`
   - 检查是否有死锁或无限循环

3. **GPU测试失败**
   - 检查CUDA是否安装: `torch.cuda.is_available()`
   - 使用CPU模式运行: `pytest -m "not gpu"`

4. **数据库测试失败**
   - 检查数据库连接
   - 确保临时文件权限

## 性能基准测试最佳实践

1. **稳定的测试环境**: 在相同的硬件和系统环境下运行
2. **多次运行取平均**: 减少随机波动影响
3. **隔离测试**: 避免测试之间相互影响
4. **监控资源使用**: CPU、内存、磁盘IO
5. **版本控制**: 记录每个版本的性能基线

## 相关文档

- [REFACTORING_PLAN.md](../../REFACTORING_PLAN.md) - 重构计划和性能目标
- [pytest文档](https://docs.pytest.org/) - pytest使用指南
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/) - pytest-benchmark插件

## 维护信息

- **创建日期**: 2026-01-31
- **维护团队**: Stock Analysis Team
- **更新频率**: 每次性能优化后
- **联系方式**: tech-support@example.com

---

**重要提示**: 性能阈值是基于当前硬件环境设定的。如果在不同的硬件上运行,可能需要调整阈值。
