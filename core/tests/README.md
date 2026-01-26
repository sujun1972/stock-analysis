# Core 项目测试套件

完整的测试套件，覆盖所有重构后的模块化组件。

## 📁 目录结构（重构后）

```
tests/
├── unit/                # 单元测试（组件级测试）
│   ├── __init__.py
│   ├── test_data_loader.py
│   ├── test_feature_engineer.py
│   ├── test_data_cleaner.py
│   ├── test_data_splitter.py
│   ├── test_feature_cache.py
│   ├── test_pipeline_config.py
│   ├── test_type_utils.py
│   ├── test_lightgbm_model.py
│   └── test_model_evaluator.py
│
├── integration/         # 集成测试（端到端测试）
│   ├── __init__.py
│   ├── test_data_pipeline.py
│   ├── test_database_manager_refactored.py
│   ├── test_phase1_data_pipeline.py
│   ├── test_phase2_features.py
│   ├── test_phase3_models.py
│   └── test_phase4_backtest.py
│
├── performance/         # 性能测试（性能基准测试）
│   ├── __init__.py
│   ├── test_performance_iterrows.py
│   └── test_performance_sample_balancing.py
│
├── __init__.py
├── run_all_tests.py    # 统一测试运行器
└── README.md           # 本文件
```

## 🚀 快速开始

### 运行所有测试

```bash
cd core/tests
python3 run_all_tests.py
```

### 按类型运行测试

```bash
# 只运行单元测试
python3 run_all_tests.py --type unit

# 只运行集成测试
python3 run_all_tests.py --type integration

# 只运行性能测试
python3 run_all_tests.py --type performance
```

### 运行特定测试模块

```bash
# 运行单元测试中的 DataLoader
python3 run_all_tests.py --module unit.test_data_loader

# 运行集成测试中的 DataPipeline
python3 run_all_tests.py --module integration.test_data_pipeline
```

更多详细说明请查看完整 README.md
