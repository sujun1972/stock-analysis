# Backend Claude Skills

Backend 项目的 Claude Code Skills 集合，用于指导 AI 助手在开发过程中遵循项目的最佳实践和编码规范。

## 📚 Skills 列表

### 1. [exception-handling](exception-handling.md)
**异常处理系统使用指南**

- **适用场景**: FastAPI 端点开发、异步服务、数据库操作、策略执行
- **核心内容**:
  - 业务异常类体系（DataQueryError、ValidationError、StrategyExecutionError 等）
  - FastAPI 错误处理装饰器（@handle_api_errors）
  - 异步重试机制（retry_async/retry_sync）
  - 与 ApiResponse 集成
- **快速开始**:
  ```python
  from app.core.exceptions import DataQueryError
  from app.api.error_handler import handle_api_errors

  @router.get("/stocks/{stock_code}")
  @handle_api_errors
  async def get_stock(stock_code: str):
      if not stock:
          raise DataQueryError(
              "股票不存在",
              error_code="STOCK_NOT_FOUND",
              stock_code=stock_code
          )
  ```

### 2. [api-response](api-response.md)
**API 响应格式使用指南**

- **适用场景**: 所有 FastAPI 端点、数据查询接口、策略执行接口
- **核心内容**:
  - ApiResponse 类的使用（success/error/warning/paginated）
  - 统一响应格式规范
  - 元数据和错误上下文
  - 与异常系统集成
- **快速开始**:
  ```python
  from app.models.api_response import ApiResponse

  @router.get("/stocks/{stock_code}")
  async def get_stock(stock_code: str):
      stock = await stock_service.get_by_code(stock_code)

      if not stock:
          return ApiResponse.not_found(
              message=f"股票 {stock_code} 不存在",
              data={"stock_code": stock_code}
          )

      return ApiResponse.success(data=stock)
  ```

---

## 🎯 Skills 使用指南

### 何时使用 Skills？

1. **开发新功能时** - 参考 skill 确保遵循项目规范
2. **重构现有代码时** - 使用 skill 统一代码风格
3. **遇到问题时** - 在 skill 中查找最佳实践和示例
4. **Code Review 时** - 对照 skill 检查代码质量

### 如何使用 Skills？

#### 方法 1: 直接阅读 Markdown 文档

```bash
# 查看异常处理指南
cat backend/.claude/skills/exception-handling.md

# 查看 API 响应格式指南
cat backend/.claude/skills/api-response.md
```

#### 方法 2: 在 Claude Code 中调用

Claude Code 会自动识别项目中的 skills，并在相关场景下主动使用。

#### 方法 3: 在 VS Code 中搜索

在 VS Code 中打开 `.claude/skills/` 目录，使用全文搜索查找示例代码。

---

## 📖 核心概念

### 1. 统一异常处理

Backend 项目使用分层的异常处理系统：

```
FastAPI 端点
    ↓
@handle_api_errors 装饰器（自动捕获异常）
    ↓
业务异常类（BackendError 系列）
    ↓
ApiResponse（统一响应格式）
    ↓
HTTP 响应（JSON）
```

**两种模式**:

- **模式 A**: `@handle_api_errors` + API 异常类（快速开发）
- **模式 B**: try-except + 业务异常 + ApiResponse（详细控制）

### 2. 统一响应格式

所有 API 端点返回统一的 `ApiResponse` 格式：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": {...},
  "timestamp": "2026-02-01T10:00:00"
}
```

**三种状态**:
- **Success (200)**: 操作成功
- **Warning (206)**: 操作完成但有警告
- **Error (4xx/5xx)**: 操作失败

### 3. 错误代码规范

所有错误都应包含 `error_code`：

```python
# ✅ 推荐
raise DataQueryError(
    "股票不存在",
    error_code="STOCK_NOT_FOUND",
    stock_code="000001"
)

# ❌ 避免
raise Exception("股票不存在")
```

**命名规范**: `UPPER_SNAKE_CASE`
- `STOCK_NOT_FOUND`
- `INVALID_DATE_RANGE`
- `DATABASE_CONNECTION_FAILED`
- `API_RATE_LIMIT_EXCEEDED`

---

## 🚀 快速参考

### 常用异常类

| 异常类 | 用途 | HTTP 状态码 |
|--------|------|------------|
| `BadRequestError` | 参数错误 | 400 |
| `ValidationError` | 数据验证失败 | 400 |
| `NotFoundError` | 资源不存在 | 404 |
| `DataQueryError` | 数据查询失败 | 500 |
| `StrategyExecutionError` | 策略执行失败 | 500 |
| `DatabaseError` | 数据库错误 | 500 |
| `ExternalAPIError` | 外部 API 错误 | 500 |

### 常用 ApiResponse 方法

| 方法 | 状态码 | 用途 |
|------|--------|------|
| `ApiResponse.success()` | 200 | 成功响应 |
| `ApiResponse.created()` | 201 | 创建成功 |
| `ApiResponse.warning()` | 206 | 警告响应 |
| `ApiResponse.bad_request()` | 400 | 错误请求 |
| `ApiResponse.not_found()` | 404 | 资源不存在 |
| `ApiResponse.internal_error()` | 500 | 服务器错误 |
| `ApiResponse.paginated()` | 200 | 分页响应 |

### 常用装饰器

| 装饰器 | 用途 |
|--------|------|
| `@handle_api_errors` | 自动捕获异步端点异常 |
| `@handle_api_errors_sync` | 自动捕获同步端点异常 |
| `@retry_async()` | 异步函数自动重试 |
| `@retry_sync()` | 同步函数自动重试 |

---

## 💡 最佳实践总结

### ✅ 推荐做法

1. **使用业务异常类**，而非通用 Exception
2. **总是提供 error_code**，便于监控和分类
3. **添加丰富的 context**，帮助调试
4. **使用 ApiResponse**，保持响应格式一致
5. **合理使用 warning 状态**，处理部分成功的情况
6. **外部调用使用重试机制**，提高健壮性

### ❌ 避免做法

1. ❌ 使用 `raise Exception("错误")`
2. ❌ 缺少 `error_code`
3. ❌ 错误消息中包含敏感信息
4. ❌ 忽略数据质量问题
5. ❌ 不同端点返回不同的响应格式
6. ❌ 缺少错误上下文信息

---

## 🔗 相关资源

### 代码文件

- [app/core/exceptions.py](../../app/core/exceptions.py) - 业务异常类定义
- [app/api/error_handler.py](../../app/api/error_handler.py) - API 错误处理装饰器
- [app/models/api_response.py](../../app/models/api_response.py) - 统一响应模型
- [app/utils/retry.py](../../app/utils/retry.py) - 重试机制工具

### 文档

- [API Response 文档](../../app/models/README_API_RESPONSE.md)
- [Backend 架构文档](../../docs/architecture/)

### 示例

参考现有 API 端点：
- `app/api/v1/stocks.py` - 股票数据查询 API
- `app/api/v1/backtest.py` - 回测执行 API
- `app/api/v1/strategies.py` - 策略管理 API

---

## 📝 贡献指南

### 如何添加新的 Skill？

1. 在 `.claude/skills/` 目录下创建 `<skill-name>.json` 和 `<skill-name>.md`
2. 在 `<skill-name>.json` 中定义元数据
3. 在 `<skill-name>.md` 中编写详细指南
4. 更新本 README.md，添加新 skill 到列表中

### Skill 文档结构建议

```markdown
# Skill 标题

**作用**: 简短描述
**适用范围**: 列举使用场景

---

## 概述
## 基本使用
## 最佳实践
## 常见场景示例
## 快速参考
## 总结
```

---

## 🎓 学习路径

### 新手入门

1. 先阅读 [api-response.md](api-response.md)，了解响应格式
2. 再阅读 [exception-handling.md](exception-handling.md)，学习异常处理
3. 参考现有 API 端点代码，实践应用

### 进阶学习

1. 深入理解异常类层次结构
2. 学习装饰器的组合使用
3. 掌握重试策略的选择
4. 理解 warning 状态的使用场景

---

## ❓ 常见问题

### Q: 何时使用 @handle_api_errors，何时手动 try-except？

**A**:
- **简单端点**：使用 `@handle_api_errors`，让装饰器自动处理
- **复杂业务**：手动 `try-except`，可以返回更详细的错误信息

### Q: 何时使用 warning 状态？

**A**: 当操作成功完成，但存在需要用户注意的情况时：
- 数���质量较低
- 部分数据缺失但已填充
- 交易次数少，回测结果可能不可靠
- 使用了降级方案

### Q: error_code 如何命名？

**A**:
- 使用 `UPPER_SNAKE_CASE` 格式
- 语义清晰，描述具体错误
- 可分类：`STOCK_NOT_FOUND`, `DB_CONNECTION_FAILED`, `API_RATE_LIMIT_EXCEEDED`

---

**版本**: 1.0.0
**创建日期**: 2026-02-01
**维护者**: Stock Analysis Team
