---
name: check-logging
description: 检查代码是否正确使用项目的统一日志系统（基于 loguru）
user-invocable: true
disable-model-invocation: false
---

# 统一日志系统使用规范检查

你是一个日志规范专家，负责确保项目中所有代码都正确使用统一的日志系统。

## 项目日志系统规范

本项目使用基于 `loguru` 的统一日志系统，位于 `core/src/utils/logger.py`

### 正确的使用方式

```python
from src.utils.logger import get_logger

# 获取模块专用 logger（使用 __name__ 可以追踪日志来源）
logger = get_logger(__name__)

# 使用 logger 记录不同级别的日志
logger.debug("调试信息：变量值 = {}", value)
logger.info("正在处理数据...")
logger.warning("警告：配置项缺失，使用默认值")
logger.error("错误：数据加载失败 - {}", error_msg)
logger.critical("严重错误：数据库连接丢失")
```

### 错误的使用方式

❌ **禁止使用 print() 输出日志**
```python
# 错误！不要使用 print
print("Processing data...")
print(f"Error: {error}")
```

❌ **禁止使用标准库 logging**
```python
# 错误！不要使用标准库的 logging
import logging
logging.info("message")
```

❌ **禁止直接从 loguru 导入**
```python
# 错误！应该使用项目封装的 get_logger
from loguru import logger
logger.info("message")
```

### 例外情况

以下情况可以豁免：
- 测试文件（`test_*.py` 或 `*_test.py`）
- `__main__` 块中的简单输出
- 调试临时代码（需要添加 `# TODO: remove debug print` 注释）
- 明确的用户交互输出（如 CLI 工具的帮助信息）

## 任务目标

检查所有 Python 文件（除测试文件外），确保：

1. 没有使用 `print()` 代替日志记录
2. 使用统一的 `get_logger(__name__)` 方式获取 logger
3. 日志级别使用恰当（debug/info/warning/error/critical）
4. 没有使用标准库的 `logging` 模块

## 执行步骤

### 第一步：检查 print() 的使用

```bash
cd /Volumes/MacDriver/stock-analysis

echo "=== 检查 Core 模块中的 print() 使用 ==="
grep -rn "print(" core/src --include="*.py" | grep -v "test_" | grep -v "_test.py" | grep -v "# noqa: T201" | grep -v "# TODO: remove debug print" || echo "✅ 未发现非规范的 print() 使用"

echo -e "\n=== 检查 Backend 模块中的 print() 使用 ==="
grep -rn "print(" backend/app --include="*.py" | grep -v "test_" | grep -v "_test.py" | grep -v "# noqa: T201" || echo "✅ 未发现非规范的 print() 使用"
```

### 第二步：检查标准库 logging 的使用

```bash
echo -e "\n=== 检查是否使用了标准库 logging ==="
grep -rn "import logging" core/src backend/app --include="*.py" | grep -v "test_" | grep -v "_test.py" || echo "✅ 未使用标准库 logging"

grep -rn "from logging import" core/src backend/app --include="*.py" | grep -v "test_" | grep -v "_test.py" || echo "✅ 未使用标准库 logging"
```

### 第三步：检查是否正确导入 logger

```bash
echo -e "\n=== 检查 logger 导入方式 ==="

# 正确的导入方式
echo "✅ 正确的导入（应该使用）："
grep -rn "from src.utils.logger import get_logger" core/src --include="*.py" | wc -l | xargs echo "  - 找到"

# 错误的导入方式（直接从 loguru 导入）
echo -e "\n❌ 错误的导入（不应该使用）："
grep -rn "from loguru import logger" core/src backend/app --include="*.py" | grep -v "test_" | grep -v "logger.py" || echo "  - 未发现"
```

### 第四步：检查 logger 初始化方式

```bash
echo -e "\n=== 检查 logger 初始化 ==="

# 正确：logger = get_logger(__name__)
echo "✅ 正确的初始化方式："
grep -rn "logger = get_logger(__name__)" core/src backend/app --include="*.py" | wc -l | xargs echo "  - 找到"

# 检查是否有文件导入了 get_logger 但没有初始化
echo -e "\n⚠️  导入了 get_logger 但可能未使用："
for file in $(grep -rl "from src.utils.logger import get_logger" core/src --include="*.py"); do
    if ! grep -q "logger = get_logger" "$file"; then
        echo "  - $file"
    fi
done
```

### 第五步：检查日志级别使用情况

```bash
echo -e "\n=== 日志级别使用统计 ==="

echo "logger.debug() 使用次数: $(grep -r "logger\.debug(" core/src backend/app --include="*.py" | wc -l)"
echo "logger.info() 使用次数: $(grep -r "logger\.info(" core/src backend/app --include="*.py" | wc -l)"
echo "logger.warning() 使用次数: $(grep -r "logger\.warning(" core/src backend/app --include="*.py" | wc -l)"
echo "logger.error() 使用次数: $(grep -r "logger\.error(" core/src backend/app --include="*.py" | wc -l)"
echo "logger.critical() 使用次数: $(grep -r "logger\.critical(" core/src backend/app --include="*.py" | wc -l)"
```

### 第六步：检查异常处理中的日志记录

```bash
echo -e "\n=== 检查异常处理中的日志使用 ==="

# 查找 except 块中没有日志记录的情况
echo "⚠️  可能缺少日志记录的 except 块："
grep -B2 -A5 "except.*:" core/src backend/app --include="*.py" | grep -A5 "except" | grep -v "logger\." | grep -v "test_" | head -30
```

### 第七步：生成详细报告

```bash
echo -e "\n================================================================================"
echo "                         日志系统使用规范检查报告"
echo "================================================================================"
echo "检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "检查范围: core/src, backend/app"
echo ""

# 统计信息
total_py_files=$(find core/src backend/app -name "*.py" ! -path "*/test_*" ! -path "*/*_test.py" | wc -l)
files_with_logger=$(grep -rl "get_logger(__name__)" core/src backend/app --include="*.py" | wc -l)
files_with_print=$(grep -rl "print(" core/src backend/app --include="*.py" | grep -v "test_" | wc -l)

echo "Python 文件总数: $total_py_files"
echo "使用统一 logger 的文件: $files_with_logger"
echo "包含 print() 的文件: $files_with_print"
echo ""
```

## 输出格式

### 检查报告示例

```
================================================================================
                        日志系统使用规范检查报告
================================================================================
检查时间: 2026-01-26 12:00:00
检查范围: core/src, backend/app

Python 文件总数: 87
使用统一 logger 的文件: 72
包含 print() 的文件: 5

=== 问题清单 ===

❌ 发现非规范的 print() 使用:
  core/src/data_pipeline/processor.py:45: print(f"Processing {len(data)} records")
  core/src/features/calculator.py:123: print("Debug: feature values:", features)

⚠️  导入了 get_logger 但未初始化:
  core/src/utils/helper.py

✅ 未发现标准库 logging 的使用
✅ 所有异常处理都有日志记录

=== 日志级别使用统计 ===
logger.debug(): 45 次
logger.info(): 234 次
logger.warning(): 67 次
logger.error(): 89 次
logger.critical(): 3 次

=== 修复建议 ===

高优先级（需要立即修复）:
1. 将 core/src/data_pipeline/processor.py:45 的 print() 改为 logger.info()
2. 将 core/src/features/calculator.py:123 的 print() 改为 logger.debug()

中优先级:
1. 为 core/src/utils/helper.py 添加 logger 初始化

=== 合规性评分 ===
总体评分: B+ (85/100)

- logger 导入规范: A+ (100/100)
- logger 使用覆盖: B  (83/100)
- 日志级别合理性: A- (90/100)
- 异常日志完整性: A+ (100/100)
```

## 自动修���建议

### 修复 print() 使用

对于发现的 print() 使用，建议按以下方式修复：

```python
# 修复前
print(f"Processing {count} records")
print(f"Error: {error}")

# 修复后
logger.info(f"Processing {count} records")
logger.error(f"Error occurred: {error}")
```

### 为文件添加 logger

如果文件缺少 logger 初始化：

```python
# 在文件顶部添加
from src.utils.logger import get_logger

# 在导入后添加
logger = get_logger(__name__)
```

### 批量检查脚本

创建一个辅助脚本 `scripts/check_logging.sh`：

```bash
#!/bin/bash

# 批量检查日志规范
echo "开始检查日志使用规范..."

# 检查所有非测试的 Python 文件
for file in $(find core/src backend/app -name "*.py" ! -path "*/test_*" ! -path "*/*_test.py"); do
    # 检查是否使用了 print()
    if grep -q "print(" "$file"; then
        # 检查是否是在 __main__ 块中
        if ! grep -B5 "print(" "$file" | grep -q "if __name__"; then
            echo "⚠️  $file 包含 print() 调用"
        fi
    fi

    # 检查是否导入了 get_logger
    if grep -q "from src.utils.logger import get_logger" "$file"; then
        # 检查是否初始化了 logger
        if ! grep -q "logger = get_logger(__name__)" "$file"; then
            echo "⚠️  $file 导入了 get_logger 但未初始化"
        fi
    fi
done

echo "检查完成！"
```

## 集成到 CI/CD

在 GitHub Actions 或 GitLab CI 中添加日志规范检查：

```yaml
# .github/workflows/logging-check.yml
name: Logging Standards Check

on: [push, pull_request]

jobs:
  check-logging:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Check for print() usage
        run: |
          if grep -rn "print(" core/src backend/app --include="*.py" | grep -v "test_" | grep -v "# noqa: T201"; then
            echo "❌ 发现非规范的 print() 使用"
            exit 1
          fi

      - name: Check for standard logging usage
        run: |
          if grep -rn "import logging" core/src backend/app --include="*.py" | grep -v "test_"; then
            echo "❌ 发现标准库 logging 的使用，应使用项目统一的 logger"
            exit 1
          fi

      - name: Summary
        run: echo "✅ 日志使用规范检查通过"
```

## Pre-commit Hook 配置

在 `.pre-commit-config.yaml` 中添加：

```yaml
repos:
  # ... 其他配置 ...

  - repo: local
    hooks:
      - id: check-print-usage
        name: Check for print() usage in non-test files
        entry: bash -c 'grep -rn "print(" core/src backend/app --include="*.py" | grep -v "test_" | grep -v "# noqa: T201" && exit 1 || exit 0'
        language: system
        pass_filenames: false

      - id: check-logging-import
        name: Check for standard logging import
        entry: bash -c 'grep -rn "import logging" core/src backend/app --include="*.py" | grep -v "test_" && exit 1 || exit 0'
        language: system
        pass_filenames: false
```

## 相关文档

- [项目日志系统文档](../../core/src/utils/logger.py)
- [Loguru 官方文档](https://loguru.readthedocs.io/)
- [Python 日志最佳实践](https://docs.python-guide.org/writing/logging/)

## 使用示例

### 手动调用 skill

```bash
# 在 Claude Code 中运行
/skill check-logging
```

### 在代码审查时使用

当添加或修改 Python 文件时，可以：
1. 自动触发此 skill 检查日志规范
2. 在 PR 审查时运行此检查
3. 作为 CI/CD pipeline 的一部分

### 修复流程

1. 运行 skill 获取检查报告
2. 根据报告修复问题
3. 重新运行检查确认修复
4. 提交代码

## 注意事项

- 测试文件（`test_*.py` 和 `*_test.py`）会被自动排除
- `__main__` 块中的 print() 是允许的（用于 CLI 输出）
- 如果必须使用 print()，添加 `# noqa: T201` 注释来豁免检查
- logger 应该始终使用 `__name__` 参数，以便追踪日志来源
