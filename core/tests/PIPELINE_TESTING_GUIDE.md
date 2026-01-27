# DataPipeline 测试指南

## 📋 概述

本文档说明如何运行和理解 DataPipeline 的测试套件。

## 🗂️ 测试文件结构

```
core/tests/
├── unit/
│   ├── test_pipeline_config.py      # 配置类单元测试 (10个测试)
│   └── test_pipeline.py             # Pipeline 单元测试 (21个测试)
├── integration/
│   └── test_pipeline_integration.py # 集成测试 (9个测试)
├── run_pipeline_tests.sh            # 测试运行脚本
└── PIPELINE_TESTING_GUIDE.md        # 本文档
```

## 🚀 快速开始

### 方式 1: 使用测试脚本（推荐）

```bash
# 进入测试目录
cd core/tests

# 运行所有测试
./run_pipeline_tests.sh all

# 只运行单元测试
./run_pipeline_tests.sh unit

# 只运行集成测试
./run_pipeline_tests.sh integration
```

### 方式 2: 直接运行测试文件

```bash
# 运行配置类测试
python3 core/tests/unit/test_pipeline_config.py

# 运行 Pipeline 单元测试
python3 core/tests/unit/test_pipeline.py

# 运行集成测试
python3 core/tests/integration/test_pipeline_integration.py
```

### 方式 3: 使用 pytest

```bash
# 安装 pytest (如果还没有)
pip install pytest pytest-cov

# 运行所有 pipeline 测试
pytest core/tests/unit/test_pipeline*.py core/tests/integration/test_pipeline*.py -v

# 带覆盖率报告
pytest core/tests/unit/test_pipeline*.py --cov=core/src/pipeline --cov-report=html

# 只运行特定测试
pytest core/tests/unit/test_pipeline.py::TestDataPipelineConfigResolution -v
```

## 📊 测试覆盖

### 单元测试 (test_pipeline.py)

#### 1. 配置解析测试 (5个测试)
- ✅ `test_01_resolve_config_from_none` - 从 None 创建配置
- ✅ `test_02_resolve_config_use_defaults` - 使用默认值
- ✅ `test_03_resolve_config_with_overrides` - 参数覆盖
- ✅ `test_04_resolve_config_none_values_ignored` - None 值忽略
- ✅ `test_05_resolve_config_all_params` - 所有参数解析

#### 2. 核心功能测试 (5个测试)
- ✅ `test_06_initialization` - 流水线初始化
- ✅ `test_07_separate_features_target` - 特征和目标分离
- ✅ `test_08_get_feature_names` - 特征名获取
- ✅ `test_09_scaler_management` - Scaler 管理
- ✅ `test_10_get_training_data_with_config` - 使用配置获取数据

#### 3. 向后兼容性测试 (2个测试)
- ✅ `test_11_legacy_params_support` - 旧参数支持
- ✅ `test_12_mixed_params_priority` - 混合参数优先级

#### 4. 重构版本测试 (5个测试)
- ✅ `test_13_feature_config_constant` - 特征配置常量
- ✅ `test_14_validate_data_empty` - 空数据验证
- ✅ `test_15_validate_data_length_mismatch` - 长度不匹配验证
- ✅ `test_16_validate_data_null_values` - 空值检查
- ✅ `test_17_validate_data_success` - 有效数据通过

#### 5. 辅助函数测试 (2个测试)
- ✅ `test_18_create_pipeline` - create_pipeline 便捷函数
- ✅ `test_19_module_exports` - 模块导出检查

#### 6. 缓存机制测试 (2个测试)
- ✅ `test_20_build_cache_config` - 缓存配置构建
- ✅ `test_21_clear_cache` - 缓存清除

### 集成测试 (test_pipeline_integration.py)

#### 1. 基础集成测试 (3个测试)
- ✅ `test_01_end_to_end_pipeline` - 端到端流水线
- ✅ `test_02_config_variations` - 不同配置处理
- ✅ `test_03_prepare_for_model_flow` - 模型数据准备

#### 2. 缓存集成测试 (2个测试)
- ✅ `test_04_cache_save_and_load` - 缓存保存和加载
- ✅ `test_05_cache_performance` - 缓存性能测试

#### 3. 错误处理测试 (2个测试)
- ✅ `test_06_invalid_data_handling` - 无效数据处理
- ✅ `test_07_pipeline_error_propagation` - 错误传播

#### 4. 便捷函数测试 (2个测试)
- ✅ `test_08_create_pipeline_function` - create_pipeline 函数
- ✅ `test_09_get_full_training_data` - get_full_training_data 函数

## 📝 测试说明

### 测试分类

#### 单元测试
- **目的**: 测试单个方法和功能
- **特点**: 使用 Mock，隔离依赖
- **速度**: 快速（< 1秒）
- **覆盖**: 代码逻辑、边界条件、异常处理

#### 集成测试
- **目的**: 测试组件协作
- **特点**: 模拟真实场景
- **速度**: 中等（1-5秒）
- **覆盖**: 数据流、缓存机制、端到端流程

### Mock 说明

测试中使用了以下 Mock 对象：

```python
# Mock 数据库管理器
mock_db = Mock()

# Mock 组件
mock_loader = Mock()        # DataLoader
mock_engineer = Mock()      # FeatureEngineer
mock_cleaner = Mock()       # DataCleaner

# Mock 缓存
mock_cache = Mock()         # FeatureCache
```

### 测试数据

测试使用合成数据，保证：
- 可重复性（使用 `np.random.seed(42)`）
- 数据完整性（无空值、无异常值）
- 价格关系合理（high ≥ max(open, close)）

## 🎯 测试重点

### 1. 配置解析 (_resolve_config)
确保：
- ✅ 从 None 正确创建配置
- ✅ 使用默认值
- ✅ 参数覆盖逻辑正确
- ✅ None 值被正确忽略

### 2. 向后兼容性
确保：
- ✅ 旧参数仍然有效
- ✅ 新旧参数混合使用正确
- ✅ 优先级正确（旧参数 > 配置对象）

### 3. 数据验证 (重构版本)
确保：
- ✅ 检测空数据
- ✅ 检测长度不匹配
- ✅ 检测空值
- ✅ 有效数据通过验证

### 4. 缓存机制
确保：
- ✅ 缓存保存正确
- ✅ 缓存加载正确
- ✅ 缓存验证正确
- ✅ 性能提升明显

## 🐛 常见问题

### 问题 1: 导入错误

```
ImportError: No module named 'src.pipeline'
```

**解决方案**:
```bash
# 确保在正确的目录
cd /path/to/stock-analysis/core

# 设置 PYTHONPATH
export PYTHONPATH=$PYTHONPATH:/path/to/stock-analysis/core/src
```

### 问题 2: Mock 警告

```
UserWarning: Mock object has no attribute 'xxx'
```

**解决方案**:
这是正常的，测试使用 Mock 对象模拟依赖。如果测试通过，可以忽略。

### 问题 3: 重构版本测试跳过

```
⚠ 重构版本不可用，跳过相关测试
```

**说明**:
部分测试需要 `pipeline_refactored.py`。如果文件不存在，相关测试会被跳过。

### 问题 4: 缓存测试失败

```
✗ 缓存测试失败
```

**解决方案**:
```bash
# 清理缓存目录
rm -rf data/pipeline_cache/*

# 重新运行测试
python3 tests/unit/test_pipeline.py
```

## 📈 性能基准

### 单元测试
- **总测试数**: 21
- **预计时间**: < 2 秒
- **通过率**: 100%

### 集成测试
- **总测试数**: 9
- **预计时间**: < 5 秒
- **通过率**: > 90% (部分需要完整环境)

### 缓存性能
- **数据量**: 1000 行 × 50 特征
- **保存时间**: < 0.1 秒
- **加载时间**: < 0.05 秒
- **性能提升**: ~2x

## 🔍 调试技巧

### 1. 运行单个测试

```bash
# 运行特定测试类
python3 -m unittest tests.unit.test_pipeline.TestDataPipelineConfigResolution

# 运行特定测试方法
python3 -m unittest tests.unit.test_pipeline.TestDataPipelineConfigResolution.test_01_resolve_config_from_none
```

### 2. 增加详细输出

```bash
# 使用 -v 参数
python3 tests/unit/test_pipeline.py -v

# 使用 pytest 的详细模式
pytest tests/unit/test_pipeline.py -vv -s
```

### 3. 查看覆盖率

```bash
# 生成覆盖率报告
pytest tests/unit/test_pipeline.py --cov=src/pipeline --cov-report=html

# 在浏览器中查看
open htmlcov/index.html
```

### 4. 断点调试

```python
# 在测试中添加断点
import pdb; pdb.set_trace()

# 或使用 breakpoint() (Python 3.7+)
breakpoint()
```

## 📊 覆盖率目标

| 模块 | 目标 | 当前 |
|------|------|------|
| pipeline.py | 90% | ~85% |
| _resolve_config | 100% | 100% |
| get_training_data | 80% | ~75% |
| prepare_for_model | 80% | ~75% |
| 辅助方法 | 90% | ~85% |

## ✅ 测试检查清单

运行测试前确认：

- [ ] 已安装所需依赖 (pandas, numpy, sklearn, imblearn)
- [ ] Python 版本 >= 3.8
- [ ] 在正确的目录（core/）
- [ ] 清理旧的缓存文件
- [ ] 环境变量设置正确

运行测试后检查：

- [ ] 所有单元测试通过
- [ ] 所有集成测试通过（或合理跳过）
- [ ] 无意外的警告或错误
- [ ] 覆盖率达到目标

## 🔗 相关文档

- [Pipeline 重构报告](../../PIPELINE_REFACTORING_REPORT.md)
- [Pipeline 源代码](../../src/pipeline.py)
- [Pipeline 重构版本](../../src/pipeline_refactored.py)
- [配置类文档](../../src/data_pipeline/pipeline_config.py)

## 💬 反馈

如有问题或建议，请：
1. 检查本文档的常见问题部分
2. 查看测试输出的详细信息
3. 提交 Issue 或 Pull Request

---

**文档版本**: 1.0
**更新日期**: 2026-01-27
**维护者**: Development Team
