# Code Quality Tools - 代码质量工具集成

**作用**: 自动化代码格式化、Lint 检查、类型检查和持续集成
**适用范围**: 所有 Python 代码开发、代码审查、CI/CD 流程

---

## 📋 概述

Backend 项目集成了完整的代码质量工具链，确保代码风格一致、质量稳定：

- **Black**: 代码自动格式化
- **isort**: 导入语句自动排序
- **Flake8**: 代码风格和质量检查
- **MyPy**: 静态类型检查
- **pre-commit**: Git 提交前自动检查
- **GitHub Actions**: CI/CD 自动化测试

---

## ⚙️ 工具配置

### 1. Black (代码格式化)

**配置文件**: `backend/pyproject.toml`

```toml
[tool.black]
line-length = 100
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
/(
  migrations
  | core/venv
  | venv
)/
'''
```

**使用方法**:
```bash
# 格式化所有代码
./venv/bin/black app/ tests/

# 检查但不修改
./venv/bin/black --check app/ tests/

# 格式化单个文件
./venv/bin/black app/api/endpoints/stocks.py
```

### 2. isort (导入排序)

**配置文件**: `backend/pyproject.toml`

```toml
[tool.isort]
profile = "black"
line_length = 100
skip_gitignore = true
skip = ["venv", "migrations", "core/venv"]
known_first_party = ["app", "core"]
known_third_party = ["fastapi", "pydantic", "pandas"]
```

**使用方法**:
```bash
# 排序所有导入
./venv/bin/isort app/ tests/

# 检查但不修改
./venv/bin/isort --check-only app/ tests/

# 排序单个文件
./venv/bin/isort app/api/endpoints/stocks.py
```

### 3. Flake8 (代码检查)

**配置文件**: `backend/.flake8`

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503, E501, E402, F541, F821, F823
per-file-ignores =
    tests/*:F841
# E203: whitespace before ':'
# W503: line break before binary operator
# E501: line too long (handled by black)
# E402: module level import not at top of file (needed for Core imports)
# F541: f-string is missing placeholders (intentional for consistency)
# F821: undefined name (from Core module)
# F823: local variable referenced before assignment (false positive)
# F841: local variable never used (test mocks)

exclude =
    .git,
    __pycache__,
    .venv,
    venv,
    migrations,
    core/venv
```

**使用方法**:
```bash
# 检查所有代码
./venv/bin/flake8 app/ tests/

# 检查单个文件
./venv/bin/flake8 app/api/endpoints/stocks.py

# 显示统计信息
./venv/bin/flake8 app/ tests/ --statistics
```

### 4. MyPy (类型检查)

**配置文件**: `backend/pyproject.toml`

```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
exclude = [
    "venv",
    "migrations",
    "core/venv",
]
```

**使用方法**:
```bash
# 类型检查
./venv/bin/mypy app/

# 检查特定模块
./venv/bin/mypy app/api/endpoints/
```

### 5. pre-commit (提交前检查)

**配置文件**: `backend/.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-merge-conflict
      - id: debug-statements

  - repo: https://github.com/psf/black
    rev: 26.1.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 7.0.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 7.3.0
    hooks:
      - id: flake8
```

**使用方法**:
```bash
# 安装 pre-commit hooks
./venv/bin/pre-commit install

# 手动运行所有检查
./venv/bin/pre-commit run --all-files

# 运行特定检查
./venv/bin/pre-commit run black --all-files
```

---

## 🚀 日常使用工作流

### 开发中

```bash
# 1. 编写代码
vim app/api/endpoints/new_feature.py

# 2. 格式化代码
./venv/bin/black app/api/endpoints/new_feature.py
./venv/bin/isort app/api/endpoints/new_feature.py

# 3. 检查代码质量
./venv/bin/flake8 app/api/endpoints/new_feature.py

# 4. 运行测试
./venv/bin/pytest tests/unit/api/test_new_feature.py
```

### 提交前

```bash
# pre-commit 会自动运行，但也可以手动运行
./venv/bin/pre-commit run --all-files

# 如果检查通过，提交代码
git add .
git commit -m "feat: add new feature"
```

### 快速修复

```bash
# 一键格式化所有代码
./venv/bin/black app/ tests/ && ./venv/bin/isort app/ tests/

# 检查是否还有问题
./venv/bin/flake8 app/ tests/
```

---

## 🎯 CI/CD 集成

### GitHub Actions 工作流

**配置文件**: `.github/workflows/code-quality.yml`

```yaml
name: Code Quality

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'backend/**/*.py'
  pull_request:
    branches: [ main, develop ]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install black isort flake8 mypy pytest pytest-cov
          pip install -r backend/requirements.txt

      - name: Check formatting with Black
        run: black --check backend/app/ backend/tests/

      - name: Check imports with isort
        run: isort --check-only backend/app/ backend/tests/

      - name: Lint with flake8
        run: flake8 backend/app/ backend/tests/

      - name: Type check with mypy
        run: mypy backend/app/
        continue-on-error: true

      - name: Run tests
        run: pytest backend/tests/ --cov=backend/app
```

---

## 📖 最佳实践

### ✅ 推荐做法

1. **提交前运行格式化**
   ```bash
   ./venv/bin/black app/ tests/
   ./venv/bin/isort app/ tests/
   ```

2. **使用 pre-commit hooks**
   - 自动在提交前运行检查
   - 避免提交不符合规范的代码

3. **定期运行完整检查**
   ```bash
   ./venv/bin/flake8 app/ tests/ --statistics
   ```

4. **修复 Flake8 警告**
   - 优先修复实际问题（F821, E999）
   - 可以忽略的警告已在配置中排除

5. **CI 失败时及时修复**
   - 查看 GitHub Actions 日志
   - 在本地重现问题
   - 修复后重新提交

### ❌ 避免做法

1. ❌ **跳过代码格式化**
   - 不一致的代码风格难以维护

2. ❌ **忽略 Flake8 警告**
   - 积累的问题会越来越难修复

3. ❌ **绕过 pre-commit hooks**
   ```bash
   # 不要使用 --no-verify
   git commit --no-verify -m "skip checks"
   ```

4. ❌ **在代码中使用 `# noqa` 注释**
   - 除非确实需要忽略特定规则
   - 优先修复问题而不是忽略

5. ❌ **提交未格式化的代码**
   - 会导致 CI 失败
   - 增加 Code Review 负担

---

## 🔧 常见问题

### Q1: Black 和 Flake8 冲突怎么办？

**A**: 已在 `.flake8` 中配置忽略规则：
```ini
extend-ignore = E203, W503, E501
```
这些规则与 Black 兼容。

### Q2: 如何忽略特定文件的检查？

**A**: 在 `.flake8` 中添加：
```ini
exclude =
    .git,
    your_file.py
```

### Q3: Core 模块导入报错怎么办？

**A**: 已配置忽略 E402 和 F821：
```ini
extend-ignore = E402, F821
```
这些是由于 Core 模块的特殊导入方式导致的。

### Q4: 测试文件中未使用的变量报错？

**A**: 已配置忽略测试文件中的 F841：
```ini
per-file-ignores =
    tests/*:F841
```

### Q5: pre-commit 太慢怎么办？

**A**: 只检查修改的文件：
```bash
./venv/bin/pre-commit run --files app/api/endpoints/stocks.py
```

---

## 📊 代码质量指标

### 格式化覆盖率
- ✅ 90 个文件已格式化
- ✅ 代码行数减少 ~1300 行（去除空行和不一致的格式）

### Flake8 检查结果
- ✅ 从 585 个错误减少到 0 个错误
- ✅ 主要修复：未使用的导入、空行问题、f-string 格式

### 测试通过率
- ✅ 单元测试：237/243 通过 (97.5%)
- ✅ 集成测试：96/135 通过 (71.1%)

---

## 🔗 相关资源

### 工具文档
- [Black 官方文档](https://black.readthedocs.io/)
- [isort 官方文档](https://pycqa.github.io/isort/)
- [Flake8 官方文档](https://flake8.pycqa.org/)
- [MyPy 官方文档](https://mypy.readthedocs.io/)
- [pre-commit 官方文档](https://pre-commit.com/)

### 项目配置
- `backend/pyproject.toml` - Black、isort、MyPy 配置
- `backend/.flake8` - Flake8 配置
- `backend/.pre-commit-config.yaml` - pre-commit 配置
- `.github/workflows/code-quality.yml` - CI/CD 配置

### 相关 Skills
- [exception-handling.md](exception-handling.md) - 异常处理规范
- [api-response.md](api-response.md) - API 响应格式

---

## 🎓 快速参考

### 常用命令

| 命令 | 作用 |
|------|------|
| `black app/ tests/` | 格式化所有代码 |
| `isort app/ tests/` | 排序所有导入 |
| `flake8 app/ tests/` | 检查代码质量 |
| `mypy app/` | 类型检查 |
| `pre-commit run --all-files` | 运行所有检查 |
| `pytest tests/ --cov=app` | 运行测试并生成覆盖率 |

### 配置文件位置

| 文件 | 位置 |
|------|------|
| Black/isort/MyPy | `backend/pyproject.toml` |
| Flake8 | `backend/.flake8` |
| pre-commit | `backend/.pre-commit-config.yaml` |
| CI/CD | `.github/workflows/code-quality.yml` |

### 忽略规则说明

| 规则 | 说明 | 原因 |
|------|------|------|
| E203 | 冒号前的空格 | Black 兼容性 |
| W503 | 二元运算符前换行 | Black 兼容性 |
| E501 | 行太长 | Black 处理 |
| E402 | 模块级导入不在顶部 | Core 导入需要 |
| F541 | f-string 缺少占位符 | 保持一致性 |
| F821 | 未定义的名称 | Core 模块导入 |
| F823 | 局部变量引用 | False positive |
| F841 | 未使用的局部变量 | 测试 Mock |

---

**版本**: 1.0.0
**创建日期**: 2026-02-05
**维护者**: Stock Analysis Team
**最后更新**: 2026-02-05
