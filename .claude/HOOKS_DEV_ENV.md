# Hooks 配置 - 开发环境专用版

## 🎯 针对您的开发环境优化

您的开发命令：
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

配置已完美适配！

---

## ✅ 更新内容

### 新增 Hook：智能命令建议

**场景**: 当您使用简单的 `docker-compose up` 时，提示使用开发环境命令

**示例**:
```bash
# 如果您输入
"执行 docker-compose restart backend"

# 会收到提示
ℹ️ 提示：开发环境建议使用: docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

---

## 📋 当前配置的 4 个 Hooks

### 1. 🔒 敏感文件保护 (PreToolUse)
```
尝试修改 .env 或 .db → ❌ 被阻止
```

**保护文件**:
- `.env` - API Keys (Tushare, DeepSeek)
- `*.db` - SQLite 数据库

---

### 2. 🚫 数据丢失防护 (PreToolUse)
```
docker-compose down -v → ❌ 被阻止
```

**阻止的危险命令**:
- `docker-compose down -v` (删除 volumes)
- `docker-compose -f ... -f ... down -v`
- `docker volume rm`
- `DROP DATABASE`
- `TRUNCATE stock_*`

**保护的数据**:
- TimescaleDB volumes (5,800,778 条记录)
- 4,575 支股票数据
- 回测历史和实验记录

**错误提示**:
```
⚠️ 危险操作：会删除数据库数据（5,800,778 条记录）
如需重启开发环境，使用不带 -v 的命令
```

---

### 3. 💡 智能命令建议 (PreToolUse) 🆕
```
docker-compose up → ℹ️ 建议使用开发环境命令
```

**触发条件**:
- 使用 `docker-compose up|restart|down`
- 未指定 `-f` 参数

**友好提示**:
```
ℹ️ 提示：开发环境建议使用:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml [命令]
```

**不会阻止执行**，只是提示！

---

### 4. 🏥 开发环境健康检查 (SessionStart)
```
启动 Claude Code → 自动检查服务状态
```

**检查结果**:

**✅ 服务正常**:
```
✅ 开发环境运行正常 (Backend, Frontend, TimescaleDB)
```

**⚠️ 服务未运行**:
```
ℹ️ 提示：开发环境未运行，建议执行:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**检查项**:
- TimescaleDB 健康状态
- Backend 容器状态
- Frontend 容器状态
- Admin 容器状态

---

## 🎬 实际使用示例

### 示例 1: 启动开发环境

**用户**: "启动开发环境"

**Claude 会执行**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Hook 不会干预** ✅

---

### 示例 2: 重启 Backend（错误命令）

**用户**: "重启 Backend 容器"

**Claude 可能执行**:
```bash
docker-compose restart backend
```

**Hook 提示**:
```
ℹ️ 提示：开发环境建议使用:
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

**命令仍会执行**，但您知道更好的方式！

---

### 示例 3: 清理环境（危险命令）

**用户**: "清理 Docker 环境，删除所有 volumes"

**Claude 可能尝试**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

**Hook 阻止**:
```
❌ 危险操作被阻止
⚠️ 会删除数据库数据（5,800,778 条记录）
如需重启开发环境，使用不带 -v 的命令
```

**命令不会执行** 🛡️

---

### 示例 4: 修改 .env 文件

**用户**: "在 .env 中添加新的 API Key"

**Claude 尝试编辑 .env**

**Hook 阻止**:
```
❌ 禁止修改 .env 和 .db 文件（包含敏感 API Keys）
```

**文件不会被修改** 🔒

---

## 🔧 配置详情

### 完整配置文件

查看 [.claude/settings.json](.claude/settings.json)

### 开发环境特性

**热重载支持**:
- ✅ Backend: `--reload` 模式，修改 Python 自动重启
- ✅ Frontend: `npm run dev`，修改 TypeScript 即时刷新
- ✅ Admin: `npm run dev`，修改 TypeScript 即时刷新

**卷挂载**:
- `./backend:/app` - Backend 代码
- `./core/src:/app/core/src` - 核心模块
- `./frontend/src:/app/src` - Frontend 代码
- `./admin/app:/app/app` - Admin 代码 (Next.js App Router)

**环境变量**:
- `ENVIRONMENT=development`
- `DEBUG=true`
- `NODE_ENV=development`

---

## 🧪 测试 Hooks

### 测试 1: 敏感文件保护
```
"编辑 .env 文件，添加一行注释"
```
**预期**: ❌ 被阻止

### 测试 2: 数据丢失防护
```
"执行 docker-compose down -v 清理环境"
```
**预期**: ❌ 被阻止，提示使用不带 -v 的命令

### 测试 3: 智能命令建议
```
"执行 docker-compose restart backend"
```
**预期**: ℹ️ 提示使用开发环境命令，但仍会执行

### 测试 4: 健康检查
```
重启 Claude Code
```
**预期**: 显示服务状态（正常或未运行）

---

## 📊 与原配置的区别

| 特性 | 原配置 | 开发环境配置 |
|-----|-------|-------------|
| Docker 命令检测 | `docker-compose ps` | `docker-compose -f ... -f ... ps` |
| 启动命令提示 | `docker-compose up -d` | `docker-compose -f ... -f ... up -d` |
| 智能命令建议 | ❌ 无 | ✅ 新增 |
| 数据丢失防护 | ✅ 基础 | ✅ 增强（提示不带 -v 的命令）|
| 健康检查详情 | ✅ 基础 | ✅ 显示 3 个服务状态 |

---

## 🚀 快速使用

### 立即生效

**无需任何安装**，只需重启 Claude Code：

```
VSCode: Cmd+Shift+P → "Reload Window"
```

### 推荐工作流

**1. 启动开发环境**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**2. 查看日志**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
```

**3. 重启服务**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

**4. 停止环境（保留数据）**:
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
```

**5. 清理环境（⚠️ 会删除数据）**:
```bash
# Hook 会阻止带 -v 的命令！
# 如果确实需要清理，手动执行：
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

---

## 💡 Pro Tips

### Tip 1: 使用别名简化命令

在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
alias dc-dev='docker-compose -f docker-compose.yml -f docker-compose.dev.yml'
```

然后可以使用：
```bash
dc-dev up -d
dc-dev logs -f backend
dc-dev restart backend
dc-dev down
```

### Tip 2: 快速检查服务状态

```bash
dc-dev ps
```

### Tip 3: 进入容器调试

```bash
# 进入 Backend 容器
dc-dev exec backend bash

# 进入 TimescaleDB 容器
dc-dev exec timescaledb psql -U stock_user -d stock_analysis
```

### Tip 4: 查看实时日志

```bash
# 所有服务
dc-dev logs -f

# 单个服务
dc-dev logs -f backend

# 最近 100 行
dc-dev logs --tail=100 backend
```

---

## 🔍 故障排除

### 问题：Hook 提示命令但仍执行了错误的命令

**原因**: `suggest-dev-command` 只是提示，不会阻止执行

**解决**: 这是设计行为，避免过度干预。如果需要强制使用开发命令，可以修改 Hook 将 `exit 2` 添加到条件中。

### 问题：健康检查显示服务未运行，但实际已运行

**原因**: 使用了不同的 docker-compose 文件启动

**解决**:
```bash
# 检查当前运行的容器
docker ps

# 如果容器存在但 Hook 检测不到，重新启动：
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart
```

### 问题：想要清理 volumes 但被 Hook 阻止

**原因**: 数据丢失防护 Hook 阻止了带 `-v` 的命令

**解决**:
1. 确认您真的需要删除数据
2. 在终端手动执行命令（绕过 Hook）
3. 或临时禁用 Hook（不推荐）

---

## 📚 相关文档

- **Docker 环境适配**: [HOOKS_DOCKER_CONFIG.md](HOOKS_DOCKER_CONFIG.md)
- **完整 Hooks 分析**: [HOOKS_ANALYSIS.md](HOOKS_ANALYSIS.md)
- **开发环境文档**: [docs/DEV_ENVIRONMENT.md](../docs/DEV_ENVIRONMENT.md)

---

## ✅ 配置状态

**开发环境**: `docker-compose -f docker-compose.yml -f docker-compose.dev.yml`
**配置状态**: ✅ 已优化
**功能状态**: ✅ 开箱即用
**依赖工具**: ✅ 零依赖

**最后更新**: 2025-02-15 (新增 Admin 热重载支持)
