# CLI单元测试

## 概览

本目录包含CLI命令行工具的完整单元测试，覆盖所有功能模块。

## 测试结构

```
tests/cli/
├── conftest.py              # Pytest配置和共享fixtures
├── utils/                   # 工具模块测试
│   ├── test_output.py      # 输出工具测试 (25个用例)
│   ├── test_progress.py    # 进度条测试 (20个用例)
│   └── test_validators.py  # 参数验证测试 (30个用例)
└── commands/                # 命令测试
    ├── test_download.py    # download命令测试 (24个用例)
    ├── test_train.py       # train命令测试 (22个用例)
    ├── test_backtest.py    # backtest命令测试 (10个用例)
    └── test_analyze.py     # analyze命令测试 (11个用例)
```

**总计**: 142个测试用例

## 运行测试

### 运行所有CLI测试
```bash
pytest tests/cli/ -v
```

### 运行特定模块
```bash
# 工具模块测试
pytest tests/cli/utils/ -v

# 命令测试
pytest tests/cli/commands/ -v
```

### 运行特定文件
```bash
pytest tests/cli/utils/test_output.py -v
pytest tests/cli/commands/test_train.py -v
```

### 生成覆盖率报告
```bash
pytest tests/cli/ --cov=src.cli --cov-report=html
open htmlcov/index.html
```

## Fixtures说明

在`conftest.py`中定义了以下共享fixtures：

- `cli_runner` - Click CLI测试运行器
- `temp_dir` - 临时目录（自动清理）
- `mock_db_manager` - Mock数据库管理器
- `mock_settings` - Mock配置对象
- `sample_stock_data` - 样本股票数据
- `sample_features_data` - 样本特征数据
- `mock_model` - Mock机器学习模型
- `mock_logger` - Mock日志器

## 测试标记

部分测试使用`@pytest.mark.skip`标记，原因：
- 需要实现相关类（如ICCalculator、BacktestEngine等）
- 需要安装额外依赖（如pyarrow）

## 注意事项

1. 测试使用mock隔离外部依赖，确保单元测试的独立性
2. 导入路径使用`src.`前缀（如`from src.cli.utils.output import ...`）
3. 临时文件在测试后自动清理
4. 部分集成测试被标记为skip，待核心类实现后可启用

## 相关文档

- [CLI使用指南](../../docs/CLI_GUIDE.md)
- [开发路线图](../../DEVELOPMENT_ROADMAP.md)
