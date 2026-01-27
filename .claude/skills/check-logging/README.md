# 日志使用规范检查 Skill (Core 子项目)

## 概述

这个 skill 用于检查 **core 子项目**中所有 Python 代码是否正确使用统一的日志系统。项目使用基于 `loguru` 的统一日志系统，位于 [core/src/utils/logger.py](../../../core/src/utils/logger.py)。

**检查范围：仅 `core/` 子项目，不包括 backend、frontend 等其他子项目。**

## 功能

- ✅ 检查是否有使用 `print()` 代替日志记录
- ✅ 检查是否有使用标准库 `logging` 模块
- ✅ 检查是否正确导入和初始化 logger
- ✅ 统计各日志级别的使用情况
- ✅ 生成详细的检查报告和修复建议

## 使用方法

### 方法 1：通过 Claude Code 调用 skill

在 Claude Code 对话中输入：

```
/skill check-logging
```

或者直接说：

```
请检查项目的日志使用规范
```

### 方法 2：运行检查脚本

直接运行项目中的检查脚本：

```bash
# 在项目根目录执行
./scripts/check_logging_standards.sh
```

## 检查报告示例

```
================================================================================
                     日志系统使用规范检查工具
================================================================================

=== 第一步：检查 print() 使用 ===
❌ 发现非规范的 print() 使用:
  core/src/data_pipeline/processor.py:45: print(f"Processing {len(data)} records")
  core/src/features/calculator.py:123: print("Debug: feature values:", features)

=== 第二步：检查标准库 logging 使用 ===
❌ 发现标准库 logging 的使用:
  core/src/database/db_manager.py:9:import logging

=== 第三步：检查 logger 导入方式 ===
✅ 正确的导入方式: 72 处
❌ 错误的导入方式（直接从 loguru）:
  backend/app/main.py:8:from loguru import logger

...

================================================================================
                             检查总结
================================================================================

Python 文件总数: 140
使用统一 logger 的文件: 72
发现的问题数量: 15
Logger 使用覆盖率: 51%

⚠️  发现较多问题，需要改进
总体评分: C+ (75/100)
```

## 正确的日志使用规范

### ✅ 正确示例

```python
from src.utils.logger import get_logger

# 获取模块专用 logger（使用 __name__ 可以追踪日志来源）
logger = get_logger(__name__)

def process_data(data):
    """处理数据的函数"""
    logger.info("开始处理数据，共 {} 条记录", len(data))

    try:
        result = expensive_operation(data)
        logger.debug("处理结果: {}", result)
        return result
    except ValueError as e:
        logger.error("数据处理失败: {}", e)
        raise
    except Exception as e:
        logger.critical("未预期的错误: {}", e)
        raise
```

### ❌ 错误示例

```python
# 错误 1: 使用 print() 代替日志
print("Processing data...")
print(f"Error: {error}")

# 错误 2: 使用标准库 logging
import logging
logging.info("message")

# 错误 3: 直接从 loguru 导入
from loguru import logger
logger.info("message")
```

## 日志级别使用指南

选择合适的日志级别：

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| `debug()` | 详细的调试信息，仅用于开发 | 变量值、函数参数、中间结果 |
| `info()` | 重要的业务流程信息 | 开始处理、完成任务、关键操作 |
| `warning()` | 警告信息，不影响正常运行 | 配置缺失使用默认值、性能问题 |
| `error()` | 错误信息，影响功能但不致命 | 数据加载失败、API 调用失败 |
| `critical()` | 严重错误，可能导致程序崩溃 | 数据库连接丢失、关键资源不可用 |

## 例外情况

以下情况可以豁免日志规范检查：

### 1. 测试文件

所有测试文件（`test_*.py` 或 `*_test.py`）会自动豁免。

### 2. `__main__` 块

用于 CLI 工具的用户输出：

```python
if __name__ == "__main__":
    # CLI 输出可以使用 print
    print("Stock Analysis Tool v1.0")
    print("Usage: python script.py [options]")
```

### 3. 临时调试代码

如果必须临时使用 print() 进行调试，添加注释标记：

```python
# TODO: remove debug print
print(f"Debug: value = {value}")  # noqa: T201
```

## 修复建议

### 快速修复 1：替换 print() 为 logger

```bash
# 使用 sed 批量替换（谨慎使用，建议先测试）
find core/src -name "*.py" -exec sed -i '' 's/print(/logger.info(/g' {} +
```

### 快速修复 2：添加 logger 到文件

对于缺少 logger 的文件，添加：

```python
# 在文件顶部的导入区域
from src.utils.logger import get_logger

# 在导入后添加（通常在类定义或函数定义之前）
logger = get_logger(__name__)
```

### 快速修复 3：替换标准库 logging

```python
# 替换前
import logging
logging.info("message")

# 替换后
from src.utils.logger import get_logger
logger = get_logger(__name__)
logger.info("message")
```

### 快速修复 4：替换直接的 loguru 导入

```python
# 替换前
from loguru import logger

# 替换后
from src.utils.logger import get_logger
logger = get_logger(__name__)
```

## 集成到开发流程

### Pre-commit Hook

在 `.pre-commit-config.yaml` 中添加：

```yaml
repos:
  - repo: local
    hooks:
      - id: check-logging-standards
        name: Check logging standards
        entry: ./scripts/check_logging_standards.sh
        language: system
        pass_filenames: false
        types: [python]
```

### GitHub Actions

在 `.github/workflows/code-quality.yml` 中添加：

```yaml
- name: Check Logging Standards
  run: ./scripts/check_logging_standards.sh
```

### VS Code 任务

在 `.vscode/tasks.json` 中添加：

```json
{
  "label": "Check Logging Standards",
  "type": "shell",
  "command": "./scripts/check_logging_standards.sh",
  "problemMatcher": [],
  "group": {
    "kind": "test",
    "isDefault": false
  }
}
```

## 相关资源

- [项目日志系统实现](../../../core/src/utils/logger.py)
- [Loguru 官方文档](https://loguru.readthedocs.io/)
- [Python 日志最佳实践](https://docs.python-guide.org/writing/logging/)
- [代码规范检查 skill](../code-review/skill.md)

## 常见问题

### Q: 为什么不能使用 print()？

A: print() 输出到标准输出，无法：
- 控制日志级别
- 记录时间戳和源代码位置
- 输出到文件进行持久化
- 在生产环境中灵活控制日志输出

### Q: 为什么不能直接使用 loguru 的 logger？

A: 项目封装了 `get_logger(__name__)` 来：
- 统一配置日志格式
- 追踪日志来源（通过 `__name__` 参数）
- 便于后续调整日志行为

### Q: 测试代码可以使用 print() 吗？

A: 可以。测试文件（`test_*.py` 和 `*_test.py`）会被自动豁免。

### Q: 如何批量修复所有问题？

A: 建议分批次手动修复，因为自动替换可能会误改：
1. 先修复 `__main__` 块外的 print()
2. 再替换标准库 logging
3. 最后统一 loguru 导入方式

## 维护

这个 skill 由项目维护者负责更新。如果发现问题或有改进建议，请：

1. 在项目 issue 中反馈
2. 提交 PR 改进检查脚本
3. 更新文档说明新的规范
