# Stock Analysis Core - 测试套件文档

> 完整的测试框架，覆盖量化交易系统的所有核心模块
>
> **最后更新**: 2026-02-01
> **测试通过率**: 98%+ ✅

---

> 📚 **测试编写指南**：查看 [../docs/developer_guide/testing.md](../docs/developer_guide/testing.md)
>
> 本文档关注**如何运行测试**，包括交互式菜单、测试统计、性能优化。
>
> 如需**编写测试**、了解测试哲学和最佳实践，请查看上述链接。

---

## 📋 目录

- [快速开始](#-快速开始)
- [测试目录结构](#-测试目录结构)
- [测试统计](#-测试统计)
- [运行测试](#-运行测试)
- [性能优化建议](#-性能优化建议)
- [常见问题](#-常见问题)
- [详细文档](#-详细文档)

---

## 🚀 快速开始

### 方法1: 交互式菜单（推荐）

```bash
cd core/tests
python run_tests.py
```

然后选择你要运行的测试:
- **[2] 快速单元测试** (~38秒) ⚡ - 日常开发推荐
- **[Q] 快速集成测试** (~30秒) - 验证集成无误
- **[X] 快速诊断** (<10秒) - 只运行失败过的测试
- **[QM] ML快速验证** (~15秒) 🚀 - 验证ML-2/ML-3/ML-4功能

### 方法2: 命令行直接运行

```bash
# 快速单元测试（推荐日常使用）
python run_tests.py --fast

# ML快速验证测试
python run_tests.py --quick-ml

# 运行所有测试
python run_tests.py --all

# 查看帮助
python run_tests.py --help
```

---

## 📁 测试目录结构

```
core/tests/
│
├── 📄 run_tests.py              # 统一测试运行器 ⭐ (含ML快速验证)
├── 📄 README.md                 # 本文件
│
├── 📂 unit/                     # 单元测试 (~1300个测试)
│   ├── providers/               # 数据提供商 (Tushare, AkShare)
│   ├── features/                # 特征工程 (125+因子)
│   ├── models/                  # 机器学习模型 (LightGBM, Ridge, GRU)
│   ├── strategies/              # 交易策略 (动量、均值回归、多因子)
│   ├── backtest/                # 回测引擎
│   ├── risk_management/         # 风险管理 (VaR, 回撤控制)
│   ├── analysis/                # 因子分析 (IC, 分层测试)
│   ├── optimization/            # 参数优化 (网格搜索、贝叶斯)
│   ├── config/                  # 配置管理
│   ├── utils/                   # 工具函数
│   └── api/                     # API接口
│
├── 📂 integration/              # 集成测试 (~134个测试, 174秒)
│   ├── providers/               # 外部API集成 (慢速: 4-5秒/测试)
│   ├── test_end_to_end_workflow.py         # 端到端工作流
│   ├── test_multi_data_source.py           # 多数据源切换
│   ├── test_database_*.py                  # 数据库集成
│   ├── test_gpu_integration.py             # GPU训练集成
│   ├── test_parallel_ic_calculation.py     # 并行IC计算
│   └── test_phase*.py                      # 阶段集成测试
│
├── 📂 performance/              # 性能测试 (~100个测试)
│   ├── test_feature_calculation_benchmarks.py
│   └── test_performance_*.py
│
├── 📂 visualization/            # 可视化测试
├── 📂 cli/                      # CLI命令行工具测试
├── 📂 config/                   # 配置测试fixtures
├── 📂 data/                     # 测试数据
├── 📂 reports/                  # 测试报告输出目录
└── 📂 logs/                     # 测试日志
```

---

## 📊 测试统计

### 总体概览

| 测试类型 | 文件数 | 测试数 | 通过率 | 耗时 (实测) |
|---------|--------|--------|--------|-------------|
| 单元测试 (全部) | ~80 | ~2665 | 98% | ~80秒 (排除GRU) |
| 单元测试 (快速) | ~76 | ~2582 | 99% | **~38秒** ⚡ |
| 集成测试 (全部) | 23 | 134 | 97% | ~175秒 (3分钟) |
| 集成测试 (快速) | ~15 | ~80 | 99% | **~30秒** ⚡ |
| 集成测试 (中速) | ~18 | ~100 | 98% | ~120秒 (2分钟) |
| 性能测试 | ~10 | ~100 | 95% | ~3秒 |
| **所有测试** | **~113** | **~2899** | **98%** | **~260秒 (4.5分钟)** |

> ⚡ 快速模式自动排除: GRU模型测试、因子分析器测试、并行回测测试、并行执行器测试、外部API测试

### 单元测试详细分类

| 功能层 | 测试文件 | 测试用例 | 预计耗时 | 状态 |
|--------|---------|---------|---------|------|
| 数据层 (data + providers) | ~15 | ~200 | ~8秒 | ✅ |
| 特征层 (features) | ~12 | ~300 | ~15秒 | ✅ |
| 模型层 (models, 排除GRU) | ~8 | ~150 | ~20秒 | ✅ |
| 回测层 (backtest) | ~6 | ~120 | ~8秒 | ✅ |
| 策略层 (strategies) | ~7 | ~108 | ~5秒 | ✅ |
| 风控层 (risk_management) | ~3 | ~41 | ~2秒 | ✅ |
| 因子分析层 (analysis) | ~7 | ~80 | ~4秒 | ✅ |
| 参数优化层 (optimization) | ~4 | ~50 | ~3秒 | ✅ |
| 配置层 (config) | ~6 | ~70 | ~2秒 | ✅ |
| 其他 (utils, api) | ~12 | ~180 | ~5秒 | ✅ |

### 集成测试详细分类

| 测试类别 | 文件数 | 测试用例 | 平均耗时/测试 | 总耗时 | 速度 |
|---------|--------|---------|--------------|--------|------|
| 外部API (Tushare, AkShare) | 4 | ~30 | **4-5秒** | ~120秒 | 🐢 慢 |
| 端到端工作流 | 1 | 3 | **4-5秒** | ~14秒 | 🐢 慢 |
| 多数据源切换 | 1 | ~10 | **4-5秒** | ~40秒 | 🐢 慢 |
| 数据库集成 | 2 | ~15 | 0.1-2秒 | ~10秒 | 🚶 中 |
| GPU/模型训练 | 2 | ~20 | 0.1-3秒 | ~15秒 | 🚶 中 |
| 并行IC计算 | 1 | ~12 | 0.1-4秒 | ~20秒 | 🚶 中 |
| 阶段测试 (phase2-4) | 3 | ~15 | 0.01-0.04秒 | ~1秒 | ⚡ 快 |
| 回测成本分析 | 1 | ~20 | 0.01-0.03秒 | ~0.5秒 | ⚡ 快 |
| 特征存储 | 1 | ~15 | 0.01-0.3秒 | ~1秒 | ⚡ 快 |
| 其他集成测试 | ~7 | ~24 | <0.1秒 | ~2秒 | ⚡ 快 |

> 💡 **速度分级说明**:
> - ⚡ 快速 (<0.1秒/测试): 适合频繁运行
> - 🚶 中速 (0.1-2秒/测试): 适合提交前运行
> - 🐢 慢速 (>3秒/测试): 仅CI/CD或发布前运行

---

## 🎯 运行测试

### 交互式菜单

```bash
python run_tests.py
```

菜单选项:

```
[快速测试 - 推荐日常使用]
  [2] 快速单元测试 (排除慢速测试: GRU/因子分析/并行) [~38秒] ⚡
  [Q] 快速集成测试 (排除外部API) [~30秒] ⚡
  [X] 快速诊断 (只运行失败过的测试) [<10秒] ⚡

[完整测试]
  [1] 运行所有测试 (单元+集成, 带覆盖率) [~260秒 (4.5分钟)]
  [3] 所有单元测试 (排除GRU) [~80秒]
  [4] 所有集成测试 [~175秒 (3分钟)]
  [5] 性能测试 [~3秒]

[集成测试分类 - 按速度]
  [I1] 快速集成测试 (排除外部API) [~30秒] ⚡
  [I2] 中速集成测试 (含数据库/不含API) [~120秒]
  [I3] 完整集成测试 (含外部API) [~175秒]

[单元测试 - 按功能层]
  [D] 数据层 (data + providers) [~8秒]
  [F] 特征层 (features) [~15秒]
  [M] 模型层 (models, 排除GRU) [~20秒]
  [B] 回测层 (backtest) [~8秒]
  [S] 策略层 (strategies) [~5秒]
  [R] 风控层 (risk_management) [~2秒]
  [A] 因子分析层 (analysis) [~4秒]
  [O] 参数优化层 (optimization) [~3秒]

[其他选项]
  [6] 运行特定模块测试
  [L] 按层级查看所有可用测试模块
  [P] 切换并行模式 (加速测试执行)
  [T] 查看测试统计信息
  [0] 退出
```

### 命令行模式

#### 快速测试（日常开发）

```bash
# 快速单元测试 (~38秒)
python run_tests.py --fast

# 快速单元测试 + 并行加速 (~20秒)
python run_tests.py --fast --parallel
```

#### 完整测试

```bash
# 运行所有测试
python run_tests.py --all

# 运行所有测试 + 覆盖率报告
python run_tests.py --all --coverage

# 运行所有单元测试
python run_tests.py --unit

# 运行所有集成测试
python run_tests.py --integration

# 运行性能测试
python run_tests.py --performance
```

#### 按功能层运行

```bash
# 数据层测试
python run_tests.py --layer data

# 特征层测试
python run_tests.py --layer features

# 模型层测试
python run_tests.py --layer models

# 回测层测试
python run_tests.py --layer backtest

# 策略层测试
python run_tests.py --layer strategies

# 风控层测试
python run_tests.py --layer risk_management

# 因子分析层测试
python run_tests.py --layer analysis

# 参数优化层测试
python run_tests.py --layer optimization
```

#### 运行特定模块

```bash
# 运行特定文件
python run_tests.py --module unit/test_data_loader.py

# 运行特定目录
python run_tests.py --module unit/strategies/

# 优先运行失败的测试
python run_tests.py --failed-first
```

#### 并行测试（加速）

```bash
# 并行运行所有测试 (使用4个工作进程)
python run_tests.py --all --parallel

# 并行运行快速测试
python run_tests.py --fast --parallel

# 自定义工作进程数
python run_tests.py --all --parallel --workers 8
```

#### 覆盖率要求

```bash
# 要求最低覆盖率80%
python run_tests.py --all --min-coverage 80

# 不生成覆盖率报告 (更快)
python run_tests.py --all --no-coverage
```

#### 查看信息

```bash
# 列出所有可用测试模块
python run_tests.py --list-modules

# 查看帮助
python run_tests.py --help
```

### 直接使用 pytest

```bash
# 运行所有测试
pytest tests/ -v

# 运行单元测试
pytest tests/unit/ -v

# 运行集成测试
pytest tests/integration/ -v

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html --cov-report=term

# 显示测试耗时
pytest tests/ --durations=20

# 并行运行
pytest tests/ -n 4
```

---

## ⚡ 性能优化建议

### 为什么快速模式这么快？

快速模式自动排除以下耗时测试:

#### 单元测试排除项
- ❌ **GRU模型测试** (2个文件, 会导致段错误)
  - `test_gru_model.py`
  - `test_gru_model_comprehensive.py`

- ❌ **耗时的单元测试** (3个文件, 共节省~42秒)
  - `test_factor_analyzer.py` - 因子分析器测试 (最慢测试5.28秒)
  - `test_parallel_backtester.py` - 并行回测器测试 (多个1秒+测试)
  - `test_parallel_executor.py` - 并行执行器测试 (多个1秒+测试)

#### 集成测试排除项
- ❌ **外部API测试** (~120秒)
  - `tests/integration/providers/` - Tushare, AkShare API调用
  - `test_multi_data_source.py` - 多数据源切换 (4-5秒/测试)
  - `test_end_to_end_workflow.py` - 端到端工作流 (4-5秒/测试)

- ❌ **慢速集成测试** (仅在I1快速模式)
  - `test_database_security_and_concurrency.py` - 数据库并发测试
  - `test_database_manager_refactored.py` - 数据库管理测试
  - `test_parallel_ic_calculation.py` - 并行IC计算 (4-5秒/测试)
  - `test_gpu_integration.py` - GPU集成测试
  - `test_model_trainer_integration.py` - 模型训练集成

### 推荐工作流

#### 日常开发
```bash
# 第一步: 快速单元测试 (~38秒)
python run_tests.py --fast

# 第二步: 运行你修改的模块测试
python run_tests.py --layer features  # 如果你修改了特征层

# 或者并行加速 (~20秒)
python run_tests.py --fast --parallel
```

#### 提交前检查
```bash
# 运行快速集成测试 (~30秒)
python run_tests.py --fast
python run_tests.py --layer data --parallel

# 或运行中速集成测试 (~120秒)
python run_tests.py --integration --fast
```

#### CI/CD 或发布前
```bash
# 运行所有测试 + 覆盖率检查
python run_tests.py --all --min-coverage 80
```

---

## 📈 查看测试报告

### 覆盖率报告

测试完成后会生成HTML覆盖率报告:

```bash
# macOS
open tests/reports/htmlcov/index.html

# Linux
xdg-open tests/reports/htmlcov/index.html

# Windows
start tests/reports/htmlcov/index.html
```

### 测试统计信息

```bash
# 查看详细的测试统计
python run_tests.py
# 然后选择 [T] 查看测试统计信息
```

---

## 🔧 常见问题

### Q: 测试运行很慢怎么办？

**A**: 使用快速模式:
```bash
python run_tests.py --fast
```

或者并行运行:
```bash
python run_tests.py --fast --parallel
```

### Q: 测试卡住不动了？

**A**: 可能是GRU模型测试导致段错误。终止测试 (Ctrl+C)，然后使用快速模式:
```bash
python run_tests.py --fast
```

### Q: 集成测试失败怎么办？

**A**: 集成测试依赖外部API和数据库:

1. **Tushare测试失败**: 检查是否设置了 `TUSHARE_TOKEN` 环境变量
2. **AkShare测试失败**: 检查网络连接
3. **数据库测试失败**: 检查 TimescaleDB 是否运行
4. **GPU测试失败**: 正常，大多数机器没有GPU

快速模式会自动跳过这些测试。

### Q: 如何只运行我修改的模块？

**A**: 使用 `--layer` 或 `--module` 参数:
```bash
# 按层运行
python run_tests.py --layer features

# 按文件运行
python run_tests.py --module unit/features/test_alpha_factors.py
```

### Q: 覆盖率报告在哪里？

**A**:
- HTML报告: `tests/reports/htmlcov/index.html`
- XML报告: `tests/reports/coverage.xml`
- 终端输出: 运行测试时会显示

### Q: 如何调试失败的测试？

**A**: 使用 pytest 的调试选项:
```bash
# 显示详细输出
pytest tests/unit/test_xxx.py -v -s

# 在失败处进入调试器
pytest tests/unit/test_xxx.py --pdb

# 只运行失败的测试
pytest tests/unit/test_xxx.py --lf
```

### Q: 并行测试报错怎么办？

**A**: 某些测试可能不支持并行 (如数据库测试)。尝试:
```bash
# 减少工作进程数
python run_tests.py --all --parallel --workers 2

# 或不使用并行
python run_tests.py --all
```

---

## 📚 详细文档

### 测试文档

- 📖 **[测试编写指南](../docs/developer_guide/testing.md)** - 如何编写测试、最佳实践
- 🔗 **[集成测试](integration/README.md)** - 端到端工作流、多数据源集成
- ⚡ **[性能测试](performance/README.md)** - 性能基准测试、回归检测
- 🖥️ **[CLI测试](cli/README.md)** - 命令行工具测试

### 特定模块测试

- [Tushare Provider测试](unit/providers/tushare/README.md) - Tushare数据提供商测试
- [AkShare Provider测试](unit/providers/akshare/README.md) - AkShare数据提供商测试
- [配置测试](config/README.md) - 配置管理测试fixtures
- [测试报告](reports/README.md) - 测试报告格式说明

### 项目文档

- 🏗️ [系统架构](../docs/architecture/overview.md) - 六层架构设计
- 🗺️ [开发路线图](../docs/ROADMAP.md) - 项目规划与版本历史
- 🤝 [贡献指南](../docs/developer_guide/contributing.md) - 如何贡献代码

---

## 📝 维护说明

### 添加新测试

1. **单元测试**: 放在 `tests/unit/` 对应的功能层目录
2. **集成测试**: 放在 `tests/integration/`
3. **性能测试**: 放在 `tests/performance/`

### 测试命名规范

- 测试文件: `test_*.py`
- 测试类: `Test*`
- 测试方法: `test_*`

### 慢速测试标记

如果添加了慢速测试 (>3秒)，请在 `run_tests.py` 的快速模式中排除:

```python
# 在 build_pytest_cmd 函数中添加
if exclude_slow:
    cmd.append('--ignore=tests/your/slow/test.py')
```

---

## 🎉 总结

- ✅ **2900+测试用例** 覆盖所有核心功能
- ✅ **98%+通过率** 确保代码质量
- ✅ **快速模式38秒** 支持敏捷开发 (并行模式20秒)
- ✅ **分层测试** 精确定位问题
- ✅ **并行支持** 加速测试执行
- ✅ **交互式菜单** 简单易用

**Happy Testing! 🚀**
