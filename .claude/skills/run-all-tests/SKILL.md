---
name: run-all-tests
description: 运行所有测试套件（单元测试 + 集成测试），生成详细测试报告
user-invocable: true
disable-model-invocation: false
---

# 完整测试流水线技能

你是一个测试自动化专家，负责运行 A股量化交易系统的完整测试套件并生成报告。

## 任务目标

执行完整的测试流程，包括：

1. **环境准备检查**
   - 验证虚拟环境是否激活
   - 检查测试依赖是否安装

2. **单元测试（Core 模块）**
   - 运行 60+ 单元测试用例
   - 测试覆盖：DataLoader, FeatureEngineer, DataCleaner, DataSplitter, FeatureCache

3. **集成测试（Phase 1-4）**
   - Phase 1: 数据管道测试
   - Phase 2: 特征工程测试
   - Phase 3: AI 模型测试
   - Phase 4: 回测引擎测试

4. **测试报告生成**
   - 统计测试通过率
   - 标记失败的测试
   - 提供修复建议

## 执行步骤

### 第一步：环境检查

```bash
# 检查虚拟环境
which python3
python3 --version

# 检查测试目录是否存在
ls -la core/tests/
```

如果虚拟环境未激活，提示用户运行：
```bash
source stock_env/bin/activate
```

### 第二步：运行单元测试套件

```bash
cd core/tests && python3 run_all_tests.py --verbosity 2
```

这将运行以下测试模块：
- test_data_loader.py (9 个测试)
- test_feature_engineer.py (10 个测试)
- test_data_cleaner.py (10 个测试)
- test_data_splitter.py (11 个测试)
- test_feature_cache.py (10 个测试)
- test_database_manager_refactored.py (10 个测试)

### 第三步：运行集成测试 - Phase 1

```bash
cd core/tests && python3 test_phase1_data_pipeline.py
```

验证：
- 数据加载功能
- 数据清洗功能
- 过滤率和清洗率指标

### 第四步：运行集成测试 - Phase 2

```bash
cd core/tests && python3 test_phase2_features.py
```

验证：
- 技术指标计算（36个）
- Alpha因子计算（51个）
- 特征转换（38个）
- 总特征数量（125+）

### 第五步：运行集成测试 - Phase 3

```bash
cd core/tests && python3 test_phase3_models.py
```

验证：
- LightGBM 模型训练
- 模型评估指标（IC, Rank IC, R²）
- 模型保存和加载

预期指标：
- IC > 0.75
- Rank IC > 0.75
- R² > 0.80

### 第六步：运行集成测试 - Phase 4

```bash
cd core/tests && python3 test_phase4_backtest.py
```

验证：
- 回测引擎运行
- 绩效分析（年化收益、夏普比率、最大回撤）
- 交易统计（胜率、平均盈亏）

预期绩效：
- 年化收益率 > 50%
- 夏普比率 > 5.0
- 最大回撤 < -5%
- 胜率 > 60%

## 输出格式

生成一份完整的测试报告，包含：

### 1. 环境信息
```
Python 版本: 3.x.x
虚拟环境: stock_env
工作目录: /Volumes/MacDriver/stock-analysis
```

### 2. 单元测试摘要
```
================================================================================
                            单元测试报告
================================================================================
模块名称                           测试数     成功     失败     错误     跳过
--------------------------------------------------------------------------------
✓ test_data_loader                    9        9        0        0        0
✓ test_feature_engineer              10       10        0        0        0
✓ test_data_cleaner                  10       10        0        0        0
✓ test_data_splitter                 11       11        0        0        0
✓ test_feature_cache                 10       10        0        0        0
--------------------------------------------------------------------------------
总计                                  60       60        0        0        0
通过率: 100.0%
```

### 3. 集成测试摘要
```
================================================================================
                            集成测试报告
================================================================================
测试阶段          状态    关键指标
--------------------------------------------------------------------------------
Phase 1: 数据     ✅      过滤率: 33%, 清洗率: 8%
Phase 2: 特征     ✅      特征数: 125个
Phase 3: 模型     ✅      IC: 0.79, Rank IC: 0.78
Phase 4: 回测     ✅      年化: 107%, 夏普: 12.85
--------------------------------------------------------------------------------
```

### 4. 失败测试分析（如果有）

对于每个失败的测试：
- 测试名称和位置
- 失败原因
- 错误堆栈
- 建议的修复步骤

### 5. 总结与建议

- 总体测试通过率
- 关键问题列表
- 下一步行动建议
- 相关文档链接

## 错误处理

### 如果虚拟环境未激活
```
❌ 错误: 虚拟环境未激活

请运行:
source stock_env/bin/activate
```

### 如果测试依赖缺失
```
❌ 错误: 缺少测试依赖

请运行:
pip install -r requirements.txt
```

### 如果数据库未运行（集成测试需要）
```
⚠️  警告: TimescaleDB 未运行，部分集成测试可能失败

请运行:
docker-compose up -d timescaledb
```

## 性能优化建议

- 单元测试应在 5 秒内完成
- 集成测试每个 Phase 应在 30 秒内完成
- 总测试时间应控制在 3 分钟以内

如果测试时间过长：
1. 检查是否有真实数据库查询（应使用 Mock）
2. 减少测试数据量
3. 使用并行测试执行

## 相关文档

- [core/tests/README.md](../../core/tests/README.md) - 测试文档
- [QUICKSTART.md](../../QUICKSTART.md#2️⃣-验证系统功能) - 测试指南
- [TROUBLESHOOTING.md](../../TROUBLESHOOTING.md) - 故障排除

## 持续集成（CI）建议

在 CI/CD 流水线中运行此技能：
```yaml
# .github/workflows/test.yml
- name: Run All Tests
  run: |
    source stock_env/bin/activate
    cd core/tests
    python3 run_all_tests.py
    python3 test_phase1_data_pipeline.py
    python3 test_phase2_features.py
    python3 test_phase3_models.py
    python3 test_phase4_backtest.py
```
