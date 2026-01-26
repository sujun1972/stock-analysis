# MCP (Model Context Protocol) 配置指南

## 已配置的 MCP 服务器

### 1. PostgreSQL/TimescaleDB MCP

**服务名称**: `stock-timescaledb`

**配置位置**: `~/.claude/settings.json`

**连接信息**:
```json
{
  "mcpServers": {
    "stock-timescaledb": {
      "command": "mcp-server-postgres",
      "args": [
        "postgresql://stock_user:stock_password_123@localhost:5432/stock_analysis"
      ]
    }
  }
}
```

**功能**:
- 直接查询 TimescaleDB 数据库
- 无需手动编写 SQL
- 快速分析股票数据、技术指标

### 2. GitHub MCP

**服务名称**: `github`

**配置位置**: `~/.claude/settings.json`

**连接信息**:
```json
{
  "mcpServers": {
    "github": {
      "transport": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

**功能**:
- 管理 GitHub Issues 和 Pull Requests
- 代码审查和评论
- 查看仓库信息和提交历史
- 创建和管理分支

**认证方式**: 首次使用时需要通过 `/mcp` 命令进行 OAuth 认证

## 使用示例

重启 Claude Code 后，您可以直接询问：

### 数据库查询（TimescaleDB MCP）
```
"数据库中有哪些表？"
"stock_daily 表的结构是什么？"
"一共存储了多少条股票数据？"
"找出过去 30 天涨幅超过 10% 的股票"
"查询 000001 平安银行的最近 10 条记录"
"统计每支股票的数据完整性"
"检查 technical_indicators 表是否有空值"
"验证 600519 贵州茅台的 MACD 指标是否已计算"
```

### GitHub 操作（GitHub MCP）
```
"列出所有 open 状态的 Issues"
"创建一个 Issue：优化 LightGBM 模型性能"
"查看 PR #123 的详细信息"
"为当前分支创建 Pull Request"
"查看最近 5 次提交"
"搜索包含 'performance' 关键词的 Issues"
"审查 PR #456 并提供代码改进建议"
```

## 激活配置

**重要**: 需要重启 Claude Code 才能加载 MCP 服务器配置。

### VSCode Extension
1. 在 VSCode 中按 `Cmd+Shift+P` (macOS) 或 `Ctrl+Shift+P` (Windows/Linux)
2. 输入 "Reload Window"
3. 重新打开 Claude Code

### CLI
```bash
# 退出当前会话
exit

# 重新启动
claude-code
```

## GitHub MCP 认证

首次使用 GitHub MCP 时，需要进行 OAuth 认证：

```bash
# 在 Claude Code 中输入
/mcp
```

然后：
1. 选择 "Authenticate" for GitHub
2. 按照浏览器提示完成 GitHub 登录
3. 授权 Claude Code 访问您的 GitHub 账户
4. 认证完成后，token 会自动保存并刷新

## 验证连接

重启后，您可以测试连接：

### 测试 TimescaleDB MCP
```
"数据库中有哪些表？"
"stock_daily 表有多少条记录？"
```

如果看到 `stock_daily`, `technical_indicators`, `predictions` 等表，说明配置成功！

### 测试 GitHub MCP
```
"列出这个仓库的所有 Issues"
"查看最近的提交历史"
```

如果能返回 Issues 列表或提交信息，说明 GitHub MCP 已正常工作！

## 安全注意事项

### 生产环境配置

如果您需要在生产环境使用，请：

1. **使用环境变量**（推荐）:
```json
{
  "mcpServers": {
    "stock-timescaledb": {
      "command": "mcp-server-postgres",
      "args": [
        "postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
      ],
      "env": {
        "POSTGRES_USER": "stock_user",
        "POSTGRES_PASSWORD": "your_secure_password",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "stock_analysis"
      }
    }
  }
}
```

2. **只读权限**:
```sql
-- 为 Claude 创建只读用户
CREATE USER claude_readonly WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE stock_analysis TO claude_readonly;
GRANT USAGE ON SCHEMA public TO claude_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_readonly;
```

3. **网络隔离**: 确保数据库不暴露到公网

## 完整配置示例

当前 `~/.claude/settings.json` 的完整配置：

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "mcpServers": {
    "stock-timescaledb": {
      "command": "mcp-server-postgres",
      "args": [
        "postgresql://stock_user:stock_password_123@localhost:5432/stock_analysis"
      ]
    },
    "github": {
      "transport": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    }
  }
}
```

## 其他推荐的 MCP 服务器

### Slack MCP (用于通知)
如果您想接收交易信号或回测报告通知：

```bash
npm install -g @modelcontextprotocol/server-slack
```

配置：
```json
{
  "slack": {
    "transport": "http",
    "url": "https://slack.com/api/mcp",
    "env": {
      "SLACK_TOKEN": "xoxb-your-token-here"
    }
  }
}
```

### 自定义 AkShare MCP
未来可以开发自定义 MCP 服务器，让 Claude 直接获取实时股票数据：

**功能设想**:
- 获取实时行情数据
- 查询技术指标
- 获取财务数据
- 查看资金流向

这将使 Claude 能够直接访问 A 股市场数据，而无需手动运行数据同步脚本。

## 故障排除

### 问题：MCP 服务器未启动
**解决方案**:
```bash
# 检查 PostgreSQL MCP 是否已安装
which mcp-server-postgres

# 如果未安装
npm install -g @modelcontextprotocol/server-postgres

# 检查 GitHub MCP（HTTP 方式不需要本地安装）
# 只需确保网络连接正常
```

### 问题：数据库连接失败
**解决方案**:
```bash
# 检查 TimescaleDB 是否运行
docker-compose ps timescaledb

# 测试连接
psql postgresql://stock_user:stock_password_123@localhost:5432/stock_analysis -c "SELECT 1;"
```

### 问题：数据库权限不足
**解决方案**:
```sql
-- 检查用户权限
\du stock_user

-- 授予必要权限
GRANT ALL PRIVILEGES ON DATABASE stock_analysis TO stock_user;
```

### 问题：GitHub MCP 认证失败
**解决方案**:
1. 确保您已登录 GitHub 账户
2. 检查网络连接是否正常
3. 尝试重新认证：
   ```bash
   # 在 Claude Code 中
   /mcp
   # 选择 "Re-authenticate" for GitHub
   ```
4. 如果仍然失败，检查 GitHub OAuth Apps 授权：
   - 访问 https://github.com/settings/applications
   - 确认 Claude Code 已被授权

## 相关文档

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [PostgreSQL MCP Server](https://github.com/modelcontextprotocol/servers/tree/main/src/postgres)
- [Claude Code MCP 指南](https://code.claude.com/docs/en/mcp.md)

## 实际应用场景

### 场景 1: 数据质量检查
```
"检查数据库中哪些股票的数据不完整"
"找出最近一周没有更新的股票"
"验证技术指标计算是否有异常值"
```

### 场景 2: 性能分析
```
"查询回测结果表，找出收益率最高的策略"
"统计不同时间段的交易信号分布"
"分析预测准确率最高的模型"
```

### 场景 3: 项目管理
```
"创建 Issue：前端显示技术指标图表"
"查看所有标记为 'bug' 的 Issues"
"为优化分支创建 PR，目标分支为 main"
"查看最近的代码提交，分析哪些文件被修改最频繁"
```

### 场景 4: 快速调试
```
"查询 000001 的最新 MACD 值"
"验证数据同步日志，检查是否有失败记录"
"查看实验记录表，找出最佳的超参数配置"
```

---

**配置日期**: 2026-01-26
**已配置的 MCP 服务器**:
- ✅ PostgreSQL/TimescaleDB MCP (stock-timescaledb)
- ✅ GitHub MCP (github)

**连接状态**: 待验证（需重启 Claude Code 并完成 GitHub 认证）
