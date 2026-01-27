# 测试指南

本文档说明如何在 Docker 环境中运行项目测试。

## 环境配置

测试环境通过 [docker-compose.dev.yml](../docker-compose.dev.yml) 配置，自动挂载源代码、测试文件和配置文件到容器中，支持热重载和实时测试。

## 快速开始

### 启动开发环境

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### 运行测试

**推荐方式：使用测试脚本**

```bash
# 运行 ModelEvaluator 基础测试（37 个测试用例）
./scripts/run_tests.sh model_evaluator

# 运行 ModelEvaluator 综合测试（63 个测试用例）
./scripts/run_tests.sh model_evaluator_full

# 运行所有单元测试
./scripts/run_tests.sh all_unit

# 运行自定义测试文件
./scripts/run_tests.sh custom tests/unit/test_features.py

# 只运行包含特定关键词的测试
./scripts/run_tests.sh -k IC model_evaluator
```

**其他运行方式**

```bash
# 直接运行单个测试文件
docker-compose exec backend python /app/core/tests/unit/test_model_evaluator.py

# 使用 pytest
docker-compose exec backend pytest /app/core/tests/unit/

# 进入容器手动测试
docker-compose exec backend bash
```

## 测试套件说明

### ModelEvaluator 测试

| 测试套件 | 测试用例数 | 覆盖范围 | 运行时间 |
|---------|----------|---------|---------|
| `test_model_evaluator.py` | 37 | IC 计算、分组收益、多空收益、风险指标 | ~0.04s |
| `test_model_evaluator_comprehensive.py` | 63 | 边界情况、异常处理、性能测试、大数据集 | ~0.3s |

## 测试覆盖范围

### ModelEvaluator 模块

- **基础指标**：IC、Rank IC、IC IR
- **收益指标**：分组收益、多空组合、多空价差
- **风险指标**：Sharpe 比率、最大回撤、胜率
- **异常处理**：None/空数组/长度不匹配/NaN/Inf/数据不足
- **配置管理**：自定义分组数、多空比例、风险参数
- **性能测试**：大数据集（10万样本）、大量分组（100组）、时间序列、稀疏数据
- **向后兼容**：旧导入方式、静态/实例方法调用

## 环境变量

测试环境自动配置以下变量：
- `ENVIRONMENT=development` - 开发模式
- `DEBUG=true` - 调试模式
- `PYTHONPATH=/app:/app/core` - Python 模块路径

## 故障排查

| 问题 | 解决方法 |
|-----|---------|
| 找不到测试文件 | 检查挂载：`docker-compose exec backend ls -la /app/core/tests/`<br>重启服务：`docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart` |
| 导入错误 | 验证 PYTHONPATH：`docker-compose exec backend printenv PYTHONPATH`<br>验证导入：`docker-compose exec backend python -c "from src.models.evaluation import ModelEvaluator"` |
| 依赖缺失 | 检查包：`docker-compose exec backend pip list \| grep -E "(pandas\|numpy)"`<br>重新构建：`docker-compose build backend` |
| 测试失败 | 查看日志：`docker-compose logs backend`<br>详细输出：`./scripts/run_tests.sh -v model_evaluator` |

## 添加新测试

1. 在 `core/tests/unit/` 创建测试文件
2. 使用 unittest 或 pytest 编写测试
3. 运行测试：`./scripts/run_tests.sh custom tests/unit/test_new_feature.py`

## 持续集成

CI/CD 流程中的测试命令：

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
./scripts/run_tests.sh all
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

## 性能基准

| 测试套件 | 测试数量 | 运行时间 | 备注 |
|---------|---------|---------|-----|
| model_evaluator | 37 | ~0.04s | 基础功能测试 |
| model_evaluator_comprehensive | 63 | ~0.3s | 包含大数据集测试 |
| 所有单元测试 | 150+ | ~2s | 完整测试覆盖 |

## 最佳实践

- 使用 `./scripts/run_tests.sh` 快速运行测试
- 修改代码后及时运行相关测试
- 使用 `-k` 选项进行针对性测试
- 定期重启容器清理缓存

## 相关文档

- [docker-compose.dev.yml](../docker-compose.dev.yml) - 开发环境配置
- [测试脚本](../scripts/run_tests.sh) - 测试运行脚本
- [ModelEvaluator 重构文档](../core/src/models/evaluation/REFACTORING.md)
