---
name: test-core
description: 专门测试 core 项目，使用虚拟环境，支持单元测试和集成测试
user-invocable: true
disable-model-invocation: false
---

# Core 项目测试技能

你是一个专业的测试工程师，负责运行 stock-analysis/core 项目的测试套件。

## 任务目标

运行 core 子项目的测试，确保代码质量和功能正确性。

## 执行步骤

### 第一步：环境准备

1. **检查虚拟环境**
```bash
# 检查是否存在虚拟环境
ls -la | grep -E "venv|stock_env|.venv"
```

2. **创建虚拟环境（如果不存在）**
```bash
python3 -m venv .venv
```

3. **激活虚拟环境并检查 Python 版本**
```bash
source .venv/bin/activate && python --version
```

4. **安装依赖（如有必要）**
```bash
# 进入 core 目录并安装依赖
cd core && pip install -e . -q
```

检查是否有 requirements.txt 或 setup.py，如果有则安装：
```bash
# 如果存在 requirements.txt
pip install -r requirements.txt -q

# 或者如果是可安装包
pip install -e . -q
```

### 第二步：运行测试

根据用户需求选择测试类型：

#### 选项 1: 运行所有测试（默认）
```bash
cd core/tests && python run_all_tests.py --type all --verbosity 2
```

#### 选项 2: 只运行单元测试
```bash
cd core/tests && python run_all_tests.py --type unit --verbosity 2
```

#### 选项 3: 只运行集成测试
```bash
cd core/tests && python run_all_tests.py --type integration --verbosity 2
```

#### 选项 4: 只运行性能测试
```bash
cd core/tests && python run_all_tests.py --type performance --verbosity 2
```

#### 选项 5: 运行特定测试模块
```bash
cd core/tests && python run_all_tests.py --module unit.test_data_loader --verbosity 2
```

### 第三步：解析测试结果

仔细分析测试输出，提取关键信息：

1. **测试统计**
   - 总测试数
   - 成功数量
   - 失败数量
   - 错误数量
   - 跳过数量
   - 通过率

2. **失败分析**（如果有失败）
   - 失败的测试名称
   - 失败原因
   - 错误堆栈
   - 涉及的文件和行号

3. **性能指标**
   - 总耗时
   - 每个模块的耗时

## 输出格式

### 成功情况
```
================================================================================
                            Core 项目测试报告
================================================================================

环境信息:
  Python 版本: 3.x.x
  虚拟环境: .venv
  工作目录: /Volumes/MacDriver/stock-analysis/core

测试摘要:
  总测试数: 60
  成功: 60 (100.0%)
  失败: 0
  错误: 0
  跳过: 0
  总耗时: 12.34秒

模块详情:
  ✓ unit.test_data_loader          9 tests passed
  ✓ unit.test_feature_engineer    10 tests passed
  ✓ unit.test_data_cleaner        10 tests passed
  ✓ unit.test_data_splitter       11 tests passed
  ✓ integration.test_pipeline     20 tests passed

结论: ✓ 所有测试通过!
================================================================================
```

### 失败情况
```
================================================================================
                            Core 项目测试报告
================================================================================

环境信息:
  Python 版本: 3.x.x
  虚拟环境: .venv
  工作目录: /Volumes/MacDriver/stock-analysis/core

测试摘要:
  总测试数: 60
  成功: 58 (96.7%)
  失败: 2
  错误: 0
  跳过: 0
  总耗时: 12.34秒

失败详情:
  ✗ unit.test_data_loader.TestDataLoader.test_load_invalid_data
    原因: AssertionError: Expected ValueError but got None
    文件: core/tests/unit/test_data_loader.py:45

  ✗ integration.test_pipeline.TestPipeline.test_end_to_end
    原因: Connection refused to TimescaleDB
    文件: core/tests/integration/test_pipeline.py:78

修复建议:
  1. test_load_invalid_data 失败可能是数据验证逻辑缺失
     建议检查: core/src/data/data_loader.py:123

  2. test_end_to_end 失败是因为数据库未运行
     建议运行: docker-compose up -d timescaledb

结论: ✗ 有 2 个测试失败，需要修复
================================================================================
```

## 错误处理

### 虚拟环境问题
```
❌ 错误: 无法创建虚拟环境

解决方案:
1. 检查 Python 版本: python3 --version (需要 >= 3.9)
2. 安装 venv 模块: sudo apt-get install python3-venv (Linux)
3. 或使用现有虚拟环境: source stock_env/bin/activate
```

### 依赖缺失
```
❌ 错误: ModuleNotFoundError: No module named 'pandas'

解决方案:
cd core && pip install -e .
或
pip install -r core/requirements.txt
```

### 测试文件不存在
```
❌ 错误: 未找到测试文件

解决方案:
1. 检查路径: ls core/tests/
2. 确认测试文件存在: ls core/tests/unit/test_*.py
```

### 数据库连接失败（集成测试）
```
⚠️ 警告: 集成测试需要 TimescaleDB

解决方案:
docker-compose up -d timescaledb

如果只想运行单元测试:
cd core/tests && python run_all_tests.py --type unit
```

## 使用场景

### 场景 1: 日常开发后运行测试
```
用户: "帮我运行 core 项目的测试"
→ 运行所有测试（单元 + 集成）
```

### 场景 2: 快速验证单元测试
```
用户: "只运行单元测试"
→ 运行 --type unit
```

### 场景 3: 测试特定模块
```
用户: "测试 data_loader 模块"
→ 运行 --module unit.test_data_loader
```

### 场景 4: CI/CD 集成
```
用户: "我想在 CI 中运行这个"
→ 提供 CI 配置示例
```

## 性能优化

- 单元测试应在 10 秒内完成
- 集成测试应在 60 秒内完成
- 如果超时，检查是否有真实数据库查询（应使用 Mock）

## 相关文档

- [core/tests/README.md](../../core/tests/README.md) - 测试文档
- [core/README.md](../../core/README.md) - Core 模块说明
- [pyproject.toml](../../core/pyproject.toml) - 项目配置

## 注意事项

1. **始终使用虚拟环境**：避免污染全局 Python 环境
2. **检查依赖**：确保所有依赖已安装
3. **数据库依赖**：集成测试可能需要 TimescaleDB
4. **测试隔离**：每个测试应该独立，不依赖其他测试
5. **清理资源**：测试后清理临时文件和数据

## 高级用法

### 使用 pytest（如果可用）
```bash
cd core && pytest tests/ -v --tb=short
```

### 生成覆盖率报告
```bash
cd core && pytest tests/ --cov=src --cov-report=term-missing
```

### 并行运行测试
```bash
cd core && pytest tests/ -n auto
```

### 运行特定标记的测试
```bash
cd core && pytest tests/ -m "not slow"
```
