---
name: code-review
description: 检查 Python 和 TypeScript 代码规范、安全漏洞和最佳实践
user-invocable: true
disable-model-invocation: false
---

# 代码规范检查技能

你是一个代码质量专家，负责检查项目代码的规范性、安全性和最佳实践遵循情况。

## 任务目标

执行全面的代码质量检查，包括：

1. **Python 代码检查**
   - 代码风格: PEP 8 规范
   - 类型注解检查
   - 导入路径规范
   - 安全漏洞扫描

2. **TypeScript/JavaScript 代码检查**
   - ESLint 规则检查
   - Prettier 格式化检查
   - Next.js 最佳实践
   - React hooks 规则

3. **项目特定规范**
   - 导入路径一致性（core.src.xxx）
   - 错误处理模式
   - 日志记录规范
   - 文档字符串完整性

4. **安全检查**
   - SQL 注入风险
   - 命令注入风险
   - 敏感信息泄露
   - 依赖包安全漏洞

## 执行步骤

### 第一步：Python 代码风格检查

```bash
cd /Volumes/MacDriver/stock-analysis

# 检查 core 模块
echo "=== 检查 Core 模块 ==="
python3 -m flake8 core/src --count --select=E9,F63,F7,F82 --show-source --statistics
python3 -m flake8 core/src --count --max-complexity=10 --max-line-length=120 --statistics

# 检查 backend 模块
echo "=== 检查 Backend 模块 ==="
python3 -m flake8 backend/app --count --max-line-length=120 --statistics

# 检查测试代码
echo "=== 检查测试代码 ==="
python3 -m flake8 core/tests --count --max-line-length=120 --statistics
```

**常见问题类型：**
- E501: 行过长（超过120字符）
- F401: 导入但未使用
- F841: 赋值但未使用的变量
- E302/E303: 空行数量不符合规范
- W503/W504: 行断开位置不规范

### 第二步：Python 类型检查（可选）

```bash
# 安装 mypy（如果未安装）
pip install mypy

# 检查类型注解
echo "=== 类型注解检查 ==="
mypy core/src/database --ignore-missing-imports
mypy core/src/data_pipeline --ignore-missing-imports
mypy backend/app --ignore-missing-imports
```

### 第三步：检查导入路径规范

```bash
# 检查是否有错误的导入路径
echo "=== 检查导入路径 ==="

# 应该使用: from core.src.xxx import yyy
# 错误示例: from src.xxx import yyy (在项目根目录运行时)

grep -r "^from src\." core/ backend/ --include="*.py" || echo "✅ 导入路径检查通过"

# 检查相对导入
grep -r "^from \.\." core/src --include="*.py" | head -10
```

**项目导入规范：**
- ✅ 正确: `from core.src.database.db_manager import DatabaseManager`
- ✅ 正确: `from src.database.db_manager import DatabaseManager` (在 Docker 容器内)
- ❌ 错误: `from database.db_manager import DatabaseManager`

### 第四步：TypeScript/JavaScript 代码检查

```bash
cd frontend

# ESLint 检查
echo "=== ESLint 检查 ==="
npm run lint

# 如果需要自动修复
# npm run lint -- --fix

# TypeScript 编译检查
echo "=== TypeScript 类型检查 ==="
npx tsc --noEmit
```

**常见问题：**
- 未使用的变量
- Missing依赖在 useEffect
- 缺少 key 属性
- any 类型使用
- 异步函数未处理错误

### 第五步：安全漏洞扫描

```bash
cd /Volumes/MacDriver/stock-analysis

# Python 依赖安全检查
echo "=== Python 依赖安全检查 ==="
pip install safety
safety check --json || echo "发现安全漏洞，请查看上方报告"

# 检查敏感信息泄露
echo "=== 检查敏感信息 ==="
grep -r "password.*=.*['\"]" . --include="*.py" --include="*.ts" --exclude-dir=node_modules --exclude-dir=stock_env || echo "✅ 未发现硬编码密码"

grep -r "api_key.*=.*['\"]" . --include="*.py" --include="*.ts" --exclude-dir=node_modules --exclude-dir=stock_env || echo "✅ 未发现硬编码 API Key"

# 检查 .env 文件是否被 gitignore
echo "=== 检查 .env 配置 ==="
if grep -q "^\.env$" .gitignore; then
    echo "✅ .env 已被 .gitignore 忽略"
else
    echo "⚠️  警告: .env 未在 .gitignore 中"
fi
```

### 第六步：SQL 注入风险检查

```bash
# 检查是否有字符串拼接的 SQL 查询
echo "=== SQL 注入风险检查 ==="

# 危险模式: f"SELECT * FROM table WHERE id = {user_input}"
grep -r 'f".*SELECT.*{' core/src backend/app --include="*.py" | grep -v "# nosec" || echo "✅ 未发现明显的 SQL 注入风险"

# 危险模式: "SELECT * FROM table WHERE id = " + user_input
grep -r '"SELECT.*" +' core/src backend/app --include="*.py" | grep -v "# nosec" || echo "✅ 未发现字符串拼接 SQL"
```

**推荐做法：**
- ✅ 使用参数化查询
- ✅ 使用 ORM（如 SQLAlchemy）
- ❌ 避免字符串拼接 SQL

### 第七步：错误处理检查

```bash
# 检查裸 except 块（应该指定异常类型）
echo "=== 错误处理检查 ==="
grep -r "except:" core/src backend/app --include="*.py" | grep -v "# noqa" || echo "✅ 未发现裸 except 块"

# 检查是否有 pass 而没有日志记录的异常处理
grep -A1 "except.*:" core/src backend/app --include="*.py" | grep -B1 "^\s*pass$" | head -20
```

**最佳实践：**
```python
# ✅ 好的做法
try:
    result = risky_operation()
except ValueError as e:
    logger.error(f"操作失败: {e}")
    raise

# ❌ 不好的做法
try:
    result = risky_operation()
except:
    pass
```

## 输出格式

生成一份代码质量报告，包含：

### 1. 执行摘要
```
================================================================================
                          代码质量检查报告
================================================================================
检查时间: 2026-01-26 12:00:00
检查范围: Python (core/, backend/) + TypeScript (frontend/)
```

### 2. Python 代码检查结果
```
Python 代码检查:
✅ PEP 8 规范: 通过 (23 个警告)
✅ 导入路径: 规范
⚠️  类型注解: 部分缺失 (覆盖率 45%)
✅ 单元测试: 60 个测试全部通过

主要问题:
- E501: 12 处行过长 (建议分行)
- F401: 5 处未使用的导入
- W503: 6 处行断开位置
```

### 3. TypeScript 代码检查结果
```
TypeScript/JavaScript 代码检查:
✅ ESLint: 通过 (0 errors, 3 warnings)
✅ TypeScript 编译: 通过
✅ React Hooks: 规范
⚠️  代码覆盖率: 未配置

主要警告:
- 3 处未使用的变量
- 1 处缺少 useEffect 依赖
```

### 4. 安全检查结果
```
安全检查:
✅ SQL 注入: 未发现风险
✅ 命令注入: 未发现风险
✅ 敏感信息: 未发现泄露
⚠️  依赖漏洞: 发现 2 个中等风险

依赖漏洞详情:
- requests 2.25.1 → 2.31.0 (修复 CVE-2023-xxxxx)
- pillow 8.3.1 → 10.0.0 (修复 CVE-2023-xxxxx)
```

### 5. 项目特定规范检查
```
项目规范遵循:
✅ 导入路径一致性: 100%
✅ 日志记录规范: 使用 loguru
⚠️  文档字符串: 70% 覆盖率
✅ 错误处理: 规范（无裸 except）

建议改进:
1. 为所有公共函数添加文档字符串
2. 补充类型注解（目标覆盖率 > 80%）
3. 配置 pre-commit hooks 自动检查
```

### 6. 代码质量评分
```
总体评分: B+ (85/100)

评分细则:
- 代码风格: A- (90/100)
- 类型安全: B  (75/100)
- 安全性:   A  (95/100)
- 测试覆盖: A+ (100/100)
- 文档完整: B- (70/100)
```

### 7. 改进建议（优先级排序）

**高优先级（建议立即修复）：**
1. 升级有安全漏洞的依赖包
2. 修复所有 ESLint errors
3. 移除未使用的导入

**中优先级（建议本周完成）：**
1. 修复行过长问题（E501）
2. 补充类型注解
3. 添加缺失的文档字符串

**低优先级（可选优化）：**
1. 配置 pre-commit hooks
2. 启用更严格的 linter 规则
3. 提高代码覆盖率到 90%+

## 自动修复建议

### Python 代码格式化

```bash
# 安装 black（代码格式化工具）
pip install black

# 自动格式化代码
black core/src --line-length 120
black backend/app --line-length 120
black core/tests --line-length 120

# 自动移除未使用的导入
pip install autoflake
autoflake --in-place --remove-unused-variables core/src/**/*.py
```

### TypeScript 代码格式化

```bash
cd frontend

# 自动修复 ESLint 问题
npm run lint -- --fix

# Prettier 格式化
npx prettier --write "src/**/*.{ts,tsx}"
```

## 配置 Pre-commit Hooks

创建 `.pre-commit-config.yaml`：

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        args: [--line-length=120]

  - repo: https://github.com/PyCQA/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=120]

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.40.0
    hooks:
      - id: eslint
        files: \.(js|ts|tsx)$
```

安装并启用：
```bash
pip install pre-commit
pre-commit install
```

## 持续集成（CI）配置

在 GitHub Actions 中运行代码检查：

```yaml
# .github/workflows/code-quality.yml
name: Code Quality

on: [push, pull_request]

jobs:
  python-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install flake8 black mypy
      - run: black --check core/ backend/
      - run: flake8 core/ backend/ --max-line-length=120
      - run: mypy core/src --ignore-missing-imports

  typescript-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - working-directory: frontend
        run: |
          npm ci
          npm run lint
          npx tsc --noEmit
```

## 相关文档

- [PEP 8 - Python代码风格指南](https://pep8.org/)
- [ESLint规则文档](https://eslint.org/docs/rules/)
- [Next.js最佳实践](https://nextjs.org/docs/pages/building-your-application/deploying/production-checklist)
- [OWASP安全编码实践](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
