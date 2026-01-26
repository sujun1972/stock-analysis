# Hooks 配置 - Docker 环境适配版

## 🐳 您的开发环境特点

- **代码运行**: Docker 容器内（Backend、Frontend、TimescaleDB）
- **Python 环境**: 宿主机虚拟环境 `stock_env`（用于本地测试）
- **代码编辑**: 宿主机（VSCode）
- **挂载方式**: `./backend:/app`, `./core/src:/app/src`

## ⚠️ 关键问题

原始配置中的 `black`、`autopep8` 在宿主机不存在，会导致：
- ❌ 格式化 Hook 失败
- ❌ 测试运行 Hook 失败
- ❌ 阻塞 Claude Code 工作流

## ✅ 适配方案

### 方案 A: 宿主机安装工具（推荐）

**优点**:
- ✅ Hook 执行速度快（无需启动容器）
- ✅ 适合频繁编辑代码
- ✅ 不依赖 Docker 服务状态

**缺点**:
- ⚠️ 需要在宿主机安装额外工具

**安装步骤**:
```bash
# 激活虚拟环境
source /Volumes/MacDriver/stock-analysis/stock_env/bin/activate

# 安装格式化工具
pip install black autopep8 isort flake8

# 验证安装
which black autopep8
```

**Hooks 配置** (使用虚拟环境):
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
      },
      {
        "name": "prevent-dangerous-db-ops",
        "matcher": "Bash",
        "type": "command",
        "command": "CMD=$(jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -iqE 'docker-compose.*(down|rm).*-v'; then echo '{\"allow\": false, \"message\": \"⚠️ 危险操作：禁止删除 Docker volumes（会丢失数据库数据）\"}' >&2 && exit 2; else echo '{\"allow\": true}'; fi"
      }
    ],
    "PostToolUse": [
      {
        "name": "auto-format-python",
        "matcher": "Edit|Write",
        "type": "command",
        "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" == *.py ]] && [[ \"$FILE\" != */stock_env/* ]]; then VENV=\"/Volumes/MacDriver/stock-analysis/stock_env/bin\"; if [ -f \"$VENV/black\" ]; then \"$VENV/black\" \"$FILE\" --line-length 100 --quiet 2>/dev/null && echo '✅ Python 代码已格式化（Black）'; elif [ -f \"$VENV/autopep8\" ]; then \"$VENV/autopep8\" --in-place --max-line-length 100 \"$FILE\" 2>/dev/null && echo '✅ Python 代码已格式化（autopep8）'; fi; fi"
      }
    ],
    "SessionStart": [
      {
        "name": "check-docker-services",
        "type": "command",
        "command": "cd /Volumes/MacDriver/stock-analysis && if ! docker-compose ps --format json 2>/dev/null | jq -e '.[] | select(.Service == \"timescaledb\" and .Health == \"healthy\")' > /dev/null; then echo 'ℹ️ TimescaleDB 未运行或不健康，建议执行: docker-compose up -d'; fi"
      }
    ]
  }
}
```

---

### 方案 B: Docker 容器内执行（完全隔离）

**优点**:
- ✅ 与生产环境一致
- ✅ 不污染宿主机环境
- ✅ 格式化工具版本统一

**缺点**:
- ⚠️ 每次 Hook 执行都需要启动容器（较慢）
- ⚠️ 依赖 Docker 服务运行

**前提条件**:
```bash
# 在 Backend Dockerfile 中添加工具
# 编辑 backend/Dockerfile，在 RUN pip install 之前添加：
RUN pip install --no-cache-dir black autopep8 isort
```

**Hooks 配置** (使用 Docker):
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
        "name": "auto-format-python-docker",
        "matcher": "Edit|Write",
        "type": "command",
        "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" == */backend/*.py ]] || [[ \"$FILE\" == */core/*.py ]]; then cd /Volumes/MacDriver/stock-analysis && CONTAINER_FILE=$(echo \"$FILE\" | sed 's|.*/backend/|/app/|' | sed 's|.*/core/src/|/app/src/|'); docker-compose exec -T backend black \"$CONTAINER_FILE\" --line-length 100 --quiet 2>/dev/null && echo '✅ Docker 容器内已格式化'; fi"
      }
    ],
    "SessionStart": [
      {
        "name": "ensure-docker-running",
        "type": "command",
        "command": "cd /Volumes/MacDriver/stock-analysis && docker-compose ps --format json 2>/dev/null | jq -e '.[] | select(.Service == \"backend\" and .State == \"running\")' > /dev/null || (echo '⚠️ Backend 容器未运行，Hooks 功能受限' && exit 1)"
      }
    ]
  }
}
```

---

### 方案 C: 混合模式（智能选择）

**优点**:
- ✅ 自动选择可用环境
- ✅ 灵活性最高
- ✅ 容错性好

**Hooks 配置** (智能选择):
```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "hooks": {
    "PreToolUse": [
      {
        "name": "protect-sensitive-files",
        "matcher": "Edit|Write",
        "type": "command",
        "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" =~ \\.(env|db)$ ]]; then echo '{\"allow\": false, \"message\": \"❌ 禁止修改敏感文件\"}' >&2 && exit 2; else echo '{\"allow\": true}'; fi"
      },
      {
        "name": "prevent-volume-deletion",
        "matcher": "Bash",
        "type": "command",
        "command": "CMD=$(jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -qE 'docker.*(rm|down).*-v'; then echo '{\"allow\": false, \"message\": \"⚠️ 禁止删除 Docker volumes\"}' >&2 && exit 2; else echo '{\"allow\": true}'; fi"
      }
    ],
    "PostToolUse": [
      {
        "name": "auto-format-python-smart",
        "matcher": "Edit|Write",
        "type": "command",
        "command": "FILE=$(jq -r '.tool_input.file_path // empty'); if [[ \"$FILE\" == *.py ]] && [[ \"$FILE\" != */stock_env/* ]]; then VENV_BLACK=\"/Volumes/MacDriver/stock-analysis/stock_env/bin/black\"; if [ -f \"$VENV_BLACK\" ]; then \"$VENV_BLACK\" \"$FILE\" --line-length 100 --quiet 2>/dev/null && echo '✅ 已格式化（本地）'; elif command -v docker-compose &>/dev/null; then cd /Volumes/MacDriver/stock-analysis && CONTAINER_FILE=$(echo \"$FILE\" | sed 's|.*/backend/|/app/|'); docker-compose exec -T backend black \"$CONTAINER_FILE\" --line-length 100 --quiet 2>/dev/null && echo '✅ 已格式化（Docker）'; fi; fi"
      }
    ],
    "SessionStart": [
      {
        "name": "check-environment",
        "type": "command",
        "command": "cd /Volumes/MacDriver/stock-analysis && echo 'ℹ️ 检查开发环境...' && docker-compose ps --services --filter 'status=running' 2>/dev/null | grep -q timescaledb && echo '✅ TimescaleDB 运行中' || echo '⚠️ TimescaleDB 未运行'"
      }
    ]
  }
}
```

---

## 🎯 推荐配置（针对您的环境）

基于您的实际情况，我推荐 **方案 A（宿主机安装）+ 简化版 Hooks**：

### 最终推荐配置

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
      },
      {
        "name": "prevent-data-loss",
        "matcher": "Bash",
        "type": "command",
        "command": "CMD=$(jq -r '.tool_input.command // empty'); if echo \"$CMD\" | grep -qE '(docker-compose.*down.*-v|docker.*volume.*rm|DROP DATABASE|TRUNCATE.*stock_)'; then echo '{\"allow\": false, \"message\": \"⚠️ 危险操作被阻止\"}' >&2 && exit 2; else echo '{\"allow\": true}'; fi"
      }
    ],
    "SessionStart": [
      {
        "name": "docker-health-check",
        "type": "command",
        "command": "cd /Volumes/MacDriver/stock-analysis && docker-compose ps 2>/dev/null | grep -q 'timescaledb.*healthy' || echo 'ℹ️ 提示：TimescaleDB 未运行，执行 docker-compose up -d 启动服务'"
      }
    ]
  }
}
```

### 为什么推荐这个配置？

1. **✅ 不依赖格式化工具**: 去掉了 `PostToolUse` 格式化 Hook，避免工具未安装导致的错误
2. **✅ 保留核心安全功能**: 敏感文件保护和数据丢失防护
3. **✅ 友好提示**: SessionStart 检查 Docker 服务状态，但不强制要求
4. **✅ 零配置**: 无需安装额外工具即可使用

---

## 📦 可选：安装格式化工具

如果您想启用代码自动格式化，执行以下步骤：

```bash
# 1. 激活虚拟环境
source /Volumes/MacDriver/stock-analysis/stock_env/bin/activate

# 2. 安装工具
pip install black autopep8 isort

# 3. 验证
which black
# 应输出: /Volumes/MacDriver/stock-analysis/stock_env/bin/black

# 4. 在 Hooks 配置中添加 PostToolUse（参考方案 A）
```

---

## 🧪 测试步骤

### 1. 测试敏感文件保护
```bash
# 在 Claude Code 中尝试
"修改 .env 文件，添加一行注释"
# 预期: ❌ 禁止修改 .env 和 .db 文件
```

### 2. 测试数据丢失防护
```bash
# 在 Claude Code 中尝试
"执行 docker-compose down -v"
# 预期: ⚠️ 危险操作被阻止
```

### 3. 测试 Docker 健康检查
```bash
# 重启 Claude Code 后应该看到
# ℹ️ 提示：TimescaleDB 未运行... (如果服务未启动)
# 或没有提示（如果服务正常）
```

---

## 🔧 故障排除

### 问题：Hook 报错 "command not found: jq"

**原因**: macOS 未安装 jq

**解决**:
```bash
brew install jq
```

### 问题：Docker 检查总是失败

**原因**: docker-compose 命令路径问题

**解决**: 使用绝对路径
```bash
which docker-compose
# 在 Hook 中使用完整路径，如：
# /usr/local/bin/docker-compose ps
```

### 问题：虚拟环境工具找不到

**原因**: 虚拟环境路径错误

**解决**: 检查实际路径
```bash
ls /Volumes/MacDriver/stock-analysis/stock_env/bin/
# 更新 Hook 中的路径
```

---

## 📊 配置对比

| 特性 | 无 Hooks | 简化版（推荐） | 完整版 |
|-----|---------|--------------|--------|
| 敏感文件保护 | ❌ | ✅ | ✅ |
| 数据丢失防护 | ❌ | ✅ | ✅ |
| 代码自动格式化 | ❌ | ❌ | ✅ |
| Docker 健康检查 | ❌ | ✅ | ✅ |
| 自动运行测试 | ❌ | ❌ | ✅ |
| 需要安装工具 | 0 | 0 | 2-3 个 |
| 复杂度 | 低 | 低 | 中 |

---

## ✅ 立即行动

**推荐**: 使用简化版配置（零依赖）

1. 复制上面的"最终推荐配置"
2. 保存到 `.claude/settings.json`
3. 重启 Claude Code（Cmd+Shift+P → Reload Window）
4. 测试敏感文件保护功能

**完整文档**: [HOOKS_ANALYSIS.md](HOOKS_ANALYSIS.md)

---

**适配日期**: 2026-01-26
**环境**: Docker + 虚拟环境
**状态**: ✅ 已优化
