# 测试报告目录

此目录用于存放测试运行时生成的各类报告文件。

## 目录结构

```
reports/
├── htmlcov/           # HTML格式的覆盖率报告
│   └── index.html    # 覆盖率报告首页
├── coverage.xml      # XML格式的覆盖率报告（用于CI/CD）
└── .coverage         # 覆盖率数据文件（pytest-cov生成）
```

## 报告说明

### 1. HTML 覆盖率报告 (`htmlcov/`)
- **生成方式**: 运行测试时自动生成
- **查看方式**: 在浏览器中打开 `htmlcov/index.html`
- **内容**: 详细的代码覆盖率分析，包括每个文件、每行代码的覆盖情况

### 2. XML 覆盖率报告 (`coverage.xml`)
- **生成方式**: 运行测试时自动生成
- **用途**: CI/CD集成、代码质量分析工具（如SonarQube、Codecov）

### 3. 覆盖率数据文件 (`.coverage`)
- **生成方式**: pytest-cov自动生成
- **用途**: 供coverage工具读取，生成各种格式的报告

## 如何生成报告

```bash
# 在 core 目录下运行
cd core

# 方式1: 使用测试运行器（推荐）
python tests/run_tests.py

# 方式2: 直接使用 pytest
pytest tests/ --cov=src --cov-report=html:tests/reports/htmlcov --cov-report=xml:tests/reports/coverage.xml

# 查看 HTML 报告
open tests/reports/htmlcov/index.html  # macOS
# 或
xdg-open tests/reports/htmlcov/index.html  # Linux
```

## 注意事项

1. **不要提交到Git**: 此目录下的所有文件（除了此README和.gitkeep）都已添加到 `.gitignore`
2. **自动清理**: 每次运行测试时会覆盖之前的报告
3. **目录保留**: `.gitkeep` 文件确保此目录结构被保留在版本控制中

## 测试覆盖率目标

- **总体覆盖率**: ≥ 80%
- **核心模块**: ≥ 90%
- **关键业务逻辑**: 100%

当前覆盖率统计请查看最新的测试报告。
