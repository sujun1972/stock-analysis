# Claude Code Skills for Stock Analysis Core

这个目录包含了Stock Analysis Core项目的Claude Code技能文档，用于指导AI助手在代码开发过程中遵循项目规范。

---

## 📚 可用Skills

### 1. Exception Handling (异常处理)

**文件**: `exception-handling.md`

**用途**: 统一异常处理系统使用指南

**适用场景**:
- 新功能开发
- 代码重构
- 错误处理改进
- API开发
- 数据处理

**核心内容**:
- ✅ 30+异常类使用指南
- ✅ 4个错误处理装饰器详解
- ✅ 完整的代码示例
- ✅ 快速参考表

**快速示例**:
```python
from src.exceptions import DataValidationError

# 正确的异常使用方式
raise DataValidationError(
    "股票代码格式不正确",
    error_code="INVALID_STOCK_CODE",
    stock_code="ABC123",
    expected_format="6位数字"
)
```

---

## 🎯 如何使用

### 方式1: Claude Code自动应用
当你在进行代码开发时，Claude Code会自动读取这些skill文档，并遵循其中的规范和最佳实践。

### 方式2: 手动参考
你可以随时查看skill文档，了解项目的规范和最佳实践：
```bash
cat .claude/skills/exception-handling.md
```

### 方式3: 明确引用
在与Claude Code对话时，你可以明确引用某个skill：
```
请参考exception-handling skill来实现这个功能
```

---

## 📖 Skill文档结构

每个skill包含两个文件：

1. **`{skill-name}.md`** - 详细的使用指南
   - 概述和背景
   - 使用原则
   - 完整示例
   - 错误示例和正确示例对比
   - 快速参考

2. **`{skill-name}.json`** - 元数据
   - skill名称和描述
   - 版本信息
   - 适用场景
   - 快速参考索引

---

## 🔧 添加新Skill

如果需要添加新的项目规范或最佳实践：

1. 在`.claude/skills/`目录下创建两个文件：
   - `{skill-name}.md` - 详细文档
   - `{skill-name}.json` - 元数据

2. 参考现有skill的格式和结构

3. 在此README中添加新skill的说明

---

## 📊 当前统计

- **Skills总数**: 1个
- **覆盖领域**: 异常处理
- **代码示例**: 15+个
- **快速参考**: 2个速查表

---

## 🎓 最佳实践

1. **保持更新**: Skill文档应该随着项目规范的变化而更新
2. **实用为主**: Skill应该包含大量实际代码示例
3. **易于查找**: 使用清晰的标题和索引
4. **版本控制**: 记录skill的版本和更新历史

---

**维护者**: Stock Analysis Team
**最后更新**: 2026-01-31
