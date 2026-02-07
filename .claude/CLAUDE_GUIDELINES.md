# Claude Code 工作指南

## 文档写入规范

### ❌ 禁止操作

**不要在项目目录中创建任务过程说明文档**

例如：
- ❌ `docs/test_fixes_summary.md`
- ❌ `docs/implementation_notes.md`
- ❌ `docs/debug_log.md`
- ❌ 任何非项目正式文档的临时记录文件

### ✅ 允许操作

1. **如果确实需要记录临时信息**，使用系统临时目录：
   ```
   /tmp/claude_notes_<timestamp>.md
   ```

2. **项目正式文档**（用户明确要求时）：
   - 架构设计文档
   - API文档
   - 用户手册
   - 开发指南（必须是项目长期维护的文档）

### 📝 Git Commit 规范

所有任务完成后，信息应该完整记录在 git commit message 中：

```bash
git commit -m "type(scope): 简短描述

详细说明:
- 问题1: 描述 + 修复
- 问题2: 描述 + 修复

影响:
- 影响点1
- 影响点2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 🎯 核心原则

**Keep the project clean** - 项目目录应该只包含：
- 源代码
- 配置文件
- 测试文件
- 正式文档（长期维护）

**临时文件 = 系统临时目录** - 所有临时性记录、调试日志、过程说明都应写入 `/tmp/` 而非项目目录。

---

最后更新: 2026-02-07
