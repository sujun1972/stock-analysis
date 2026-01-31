# 集成测试文档

## 概述

本目录包含端到端集成测试，用于验证系统各模块间的协作和完整工作流。

## 测试文件

### 1. test_end_to_end_workflow.py
**功能**: 端到端工作流集成测试
**流程**: 数据下载 → 特征计算 → 模型训练 → 策略回测

**测试类**:
- `TestCompleteWorkflow`: 完整交易工作流测试
- `TestMultiStockWorkflow`: 多股票工作流测试

### 2. test_multi_data_source.py
**功能**: 多数据源集成测试
**内容**: AkShare和Tushare数据源切换、一致性验证、降级机制

**测试类**:
- `TestDataSourceSwitching`: 数据源切换测试
- `TestDataSourceFallback`: 降级机制测试
- `TestDataFormatConsistency`: 格式一致性测试

### 3. test_persistence_integration.py
**功能**: 持久化集成测试
**内容**: 特征存储(CSV/Parquet/HDF5)、模型保存加载、数据库读写

**测试类**:
- `TestFeatureStorage`: 特征存储测试
- `TestModelPersistence`: 模型持久化测试
- `TestDatabasePersistence`: 数据库持久化测试
- `TestEndToEndPersistence`: 端到端持久化工作流测试

## 运行测试

### 使用运行脚本
```bash
cd tests/integration
python run_integration_tests.py
```

### 使用pytest
```bash
# 运行所有集成测试
pytest tests/integration/ -v

# 运行特定文件
pytest tests/integration/test_end_to_end_workflow.py -v

# 运行特定测试
pytest tests/integration/test_persistence_integration.py::TestFeatureStorage::test_02_parquet_storage -v
```

## 环境要求

### 必需依赖
```bash
pytest>=7.4.0
pandas>=2.0.0
numpy>=1.24.0
```

### 可选依赖
```bash
akshare>=1.13.0      # AkShare数据源
tushare>=1.3.0       # Tushare数据源
pyarrow>=13.0.0      # Parquet格式
tables>=3.8.0        # HDF5格式
lightgbm>=4.0.0      # LightGBM模型
torch>=2.0.0         # GRU模型
```

### 安装依赖
```bash
# 最小依赖
pip install akshare lightgbm pyarrow

# 完整依赖
pip install akshare tushare lightgbm torch pyarrow tables
```

## 测试状态说明

- ✅ **PASSED**: 测试通过
- ⚠️ **SKIPPED**: 测试跳过（通常因缺少依赖或数据）
- ❌ **FAILED**: 测试失败

### 常见跳过原因
- 缺少数据源包（akshare/tushare）
- 数据库未连接
- 缺少存储格式支持（pyarrow/tables）
- 缺少模型库（lightgbm/torch）

## 开发指南

### 添加新测试
1. 在适当的测试文件中添加测试方法
2. 遵循命名规范: `test_XX_descriptive_name`
3. 添加详细的docstring
4. 使用`skipTest`处理依赖缺失

### 测试最佳实践
- 使用`setUp`和`tearDown`管理测试资源
- 使用临时目录存储测试文件
- 测试后清理临时文件
- 捕获并正确处理异常

## 相关文档

- [重构计划文档](../../REFACTORING_PLAN.md)
- [性能测试文档](../performance/README.md)
- [单元测试文档](../unit/README.md)

---

**创建日期**: 2026-01-31
**维护者**: Quant Team
