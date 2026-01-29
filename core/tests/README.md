# Core 项目测试套件

完整的测试套件，覆盖所有重构后的模块化组件。

## 📁 目录结构

```
tests/
├── unit/                # 单元测试（组件级测试）
│   ├── providers/       # 数据提供商测试
│   ├── models/          # 模型测试
│   ├── features/        # 特征工程测试
│   ├── strategies/      # 策略测试（7个文件，108个测试用例）⭐ NEW
│   ├── config/          # 配置测试
│   └── ...
│
├── integration/         # 集成测试（端到端测试）
│   ├── providers/       # 提供商集成测试
│   ├── test_data_pipeline.py
│   ├── test_database_manager_refactored.py
│   └── ...
│
├── performance/         # 性能测试（性能基准测试）
│   ├── test_performance_iterrows.py
│   └── test_performance_sample_balancing.py
│
├── run_tests.py        # 统一测试运行器
└── README.md           # 本文件
```

## 🚀 快速开始

### 方法1: 使用统一测试运行器 ⭐ 推荐

**交互式菜单模式**（最简单）：
```bash
cd core/tests
python3 run_tests.py
```

**命令行模式**：
```bash
# 运行所有测试（带覆盖率报告）
python3 run_tests.py --all

# 快速测试（排除慢速的GRU模型测试和外部API测试）
python3 run_tests.py --fast

# 只运行单元测试
python3 run_tests.py --unit

# 只运行集成测试
python3 run_tests.py --integration

# 只运行性能测试
python3 run_tests.py --performance

# 运行Provider测试
python3 run_tests.py --providers

# 运行模型测试（排除GRU）
python3 run_tests.py --models

# 运行特征工程测试
python3 run_tests.py --features

# 运行策略测试 ⭐ NEW
python3 run_tests.py --module unit/strategies/

# 运行特定模块
python3 run_tests.py --module unit/test_data_loader.py

# 查看所有选项
python3 run_tests.py --help
```

### 方法2: 直接使用pytest

```bash
# 运行所有测试并生成覆盖率报告
pytest tests/ --cov=src --cov-report=html --cov-report=term -v

# 只运行单元测试
pytest tests/unit/ --cov=src --cov-report=html -v

# 排除慢速测试
pytest tests/ --cov=src --cov-report=html \
  --ignore=tests/unit/models/test_gru_model.py -v

# 运行特定测试文件
pytest tests/unit/test_data_loader.py -v
```

## 📊 查看覆盖率报告

测试完成后，在浏览器中打开覆盖率报告：

```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html

# Windows
start htmlcov/index.html
```

## ⚡ 性能优化建议

**GRU模型测试很慢？需要跳过外部API测试？**

快速模式会自动排除：
- GRU深度学习模型测试（每个测试约30-60秒）
- 外部API集成测试（AkShare、Tushare，需要网络连接和API token）

推荐使用快速模式：

```bash
python3 run_tests.py --fast
```

或手动排除：
```bash
pytest tests/ --cov=src --cov-report=html \
  --ignore=tests/unit/models/test_gru_model.py \
  --ignore=tests/integration/providers/akshare/ \
  --ignore=tests/integration/providers/test_tushare_provider.py -v
```

## 📈 测试统计

- **总测试数量**: ~1800个测试用例（+108个策略测试 ⭐）
- **单元测试**: ~1300个（含108个策略测试）
- **集成测试**: ~400个
- **性能测试**: ~100个
- **预计运行时间**:
  - 所有测试: ~60分钟
  - 快速模式（排除GRU和外部API）: ~15分钟
  - 只运行单元测试: ~20分钟
  - 只运行策略测试: ~5分钟

### 策略测试详情 ⭐ NEW

- **测试文件**: 7个
- **测试用例**: 108个
- **覆盖策略**:
  - MomentumStrategy（动量策略）- 15个测试
  - MeanReversionStrategy（均值回归）- 17个测试
  - MultiFactorStrategy（多因子）- 17个测试
  - MLStrategy（机器学习）- 15个测试（6个跳过）
  - StrategyCombiner（策略组合）- 19个测试
  - SignalGenerator（信号生成）- 25个测试
- **当前通过率**: 52%（56/108通过）
- **详细状态**: 见 [tests/unit/strategies/README_TEST_STATUS.md](unit/strategies/README_TEST_STATUS.md)

## 🔧 常见问题

**Q: 测试卡住了怎么办？**

A: 通常是GRU模型测试导致的。终止测试（Ctrl+C），然后使用快速模式：
```bash
python3 run_tests.py --fast
```

**Q: 如何只运行我修改过的模块的测试？**

A: 使用 `--module` 参数：
```bash
python3 run_tests.py --module unit/test_data_loader.py
```

**Q: 覆盖率报告在哪里？**

A: 生成在 `htmlcov/index.html`，用浏览器打开查看。

## 📝 更多详细说明

查看统一测试运行器的帮助信息：
```bash
python3 run_tests.py --help
```
