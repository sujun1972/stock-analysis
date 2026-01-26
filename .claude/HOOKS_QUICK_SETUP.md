# Hooks 快速配置指南

## 🚀 3 分钟快速启动

### 步骤 1: 安装依赖工具

```bash
# 安装 Python 格式化工具
pip install black autopep8

# 验证安装
which black autopep8 jq
```

### 步骤 2: 复制配置到项目

创建或编辑 `.claude/settings.json`，添加以下基础配置：

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "PreToolUse": [
      {
        "name": "protect-sensitive-files",
        "matcher": "Edit|Write",
        "type": "command",
        "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" =~ \\.(env|db)$ ]]; then echo '{\"allow\": false, \"message\": \"❌ 禁止修改 .env 和 .db 文件\"}' >&2 && exit 2; else echo '{\"allow\": true}'; fi"
      }
    ],
    "PostToolUse": [
      {
        "name": "auto-format-python",
        "matcher": "Edit|Write",
        "type": "command",
        "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" == *.py ]]; then black \"$FILE\" --line-length 100 --quiet 2>/dev/null && echo '✅ Python 代码已格式化'; fi"
      }
    ]
  }
}
```

### 步骤 3: 重启 Claude Code

- VSCode: `Cmd+Shift+P` → "Reload Window"
- CLI: 退出并重新启动

### 步骤 4: 测试 Hooks

尝试修改 `.env` 文件，应该看到：
```
❌ 禁止修改 .env 和 .db 文件
```

尝试编辑 Python 文件，保存后应该看到：
```
✅ Python 代码已格式化
```

---

## 📋 配置速查表

### 阻止文件修改

```json
{
  "name": "protect-files",
  "matcher": "Edit|Write",
  "type": "command",
  "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" =~ pattern ]]; then echo '{\"allow\": false}' >&2 && exit 2; else echo '{\"allow\": true}'; fi"
}
```

### 自动格式化代码

```json
{
  "name": "format-code",
  "matcher": "Edit|Write",
  "type": "command",
  "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" == *.ext ]]; then formatter \"$FILE\"; fi"
}
```

### 运行测试

```json
{
  "name": "run-tests",
  "matcher": "Edit|Write",
  "type": "command",
  "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ condition ]]; then pytest \"$FILE\"; fi"
}
```

### 会话启动检查

```json
{
  "name": "check-services",
  "type": "command",
  "command": "docker-compose ps | grep -q healthy || echo '⚠️ 服务未运行'"
}
```

---

## 🔍 调试 Hooks

### 查看 Hook 输出

Hooks 的输出会显示在 Claude Code 的响应中。如果 Hook 失败，会看到错误信息。

### 测试 Hook 命令

在终端单独测试 Hook 命令：

```bash
# 测试文件保护
echo '{"tool_input": {"file_path": ".env"}}' | FILE=$(jq -r '.tool_input.file_path // empty') && if [[ "$FILE" =~ \.(env|db)$ ]]; then echo "BLOCKED"; fi

# 测试格式化
FILE="test.py" && black "$FILE" --line-length 100 --quiet
```

### 常见问题

**Hook 没有执行**:
- 检查 `matcher` 是否正确匹配工具名称
- 确认 JSON 语法正确（使用 `jq` 验证）
- 查看是否有语法错误

**Hook 执行失败**:
- 检查命令是否存在（`which black jq`）
- 测试命令单独运行是否成功
- 查看错误消息

**Hook 太慢**:
- 避免耗时操作（大文件处理）
- 使用 `timeout` 命令限制执行时间
- 考虑异步执行

---

## ⚙️ 高级配置

### 环境变量

在 Hook 中使用项目路径：

```bash
cd "$CLAUDE_PROJECT_DIR" && docker-compose ps
```

### 条件执行

只在特定文件触发：

```bash
FILE=$(jq -r '.tool_input.file_path // empty')
if [[ "$FILE" == */backend/app/api/* ]]; then
  # 只对 API 文件执行
fi
```

### 智能 Hook (Prompt-based)

使用 LLM 判断：

```json
{
  "name": "intelligent-check",
  "type": "prompt",
  "prompt": "分析这个操作是否安全。返回 {\"allow\": true/false}"
}
```

---

## 📊 推荐配置组合

### 最小配置（新手）
- 敏感文件保护
- Python 代码格式化

### 标准配置（推荐）
- 敏感文件保护
- Python 代码格式化
- Docker 服务检查
- 数据库操作验证

### 完整配置（高级）
- 以上所有 +
- 自动运行测试
- 模型文件检查
- API 安全检查
- 智能回测分析

---

## 🎯 下一步

1. ✅ 实施基础配置（文件保护 + 代码格式化）
2. ✅ 测试 Hooks 是否正常工作
3. ✅ 根据需要添加更多 Hooks
4. ✅ 查看完整分析：[HOOKS_ANALYSIS.md](HOOKS_ANALYSIS.md)

---

**配置时间**: < 3 分钟
**学习曲线**: 低
**收益**: 立竿见影
