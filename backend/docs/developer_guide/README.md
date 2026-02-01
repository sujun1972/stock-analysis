# 开发者指南

Backend 项目的开发者指南文档集合。

---

## 📚 文档列表

### 核心指南

#### 1. [API Response 使用指南](api_response_guide.md)
**统一 API 响应格式和最佳实践**

- ApiResponse 类的完整使用说明
- 成功/警告/错误三种响应状态
- 与异常系统集成
- 分页响应和请求追踪
- 测试示例和迁移指南

**快速开始**:
```python
from app.models.api_response import ApiResponse

# 成功响应
return ApiResponse.success(data=result)

# 警告响应（新功能）
return ApiResponse.warning(
    data=result,
    message="操作完成，但存在警告",
    warning_code="LOW_QUALITY"
)

# 错误响应
return ApiResponse.not_found(message="资源不存在")
```

---

#### 2. [贡献指南](contributing.md)
**如何为项目贡献代码**

- Fork 和克隆流程
- 开发环境设置
- 代码规范和检查工具
- 提交和 Pull Request 流程
- Code Review 标准

---

### Claude Skills（最佳实践）

Backend 项目的 Claude Code Skills 位于 [`backend/.claude/skills/`](../../.claude/skills/)，提供 AI 辅助开发的最佳实践指南。

#### [Exception Handling Skill](../../.claude/skills/exception-handling.md)
**异常处理系统使用指南**

- 18 个业务异常类
- FastAPI 错误处理装饰器
- 异步重试机制
- error_code 和 context 规范

**快速参考**:
```python
from app.core.exceptions import DataQueryError
from app.api.error_handler import handle_api_errors

@router.get("/stocks/{code}")
@handle_api_errors
async def get_stock(code: str):
    if not stock:
        raise DataQueryError(
            "股票不存在",
            error_code="STOCK_NOT_FOUND",
            stock_code=code
        )
```

---

#### [API Response Skill](../../.claude/skills/api-response.md)
**API 响应格式详细指南**

- 详细的最佳实践
- 完整的示例代码
- 决策树和快速参考
- 与异常系统集成

---

#### [Skills 总览](../../.claude/skills/README.md)
**所有 Skills 的使用指南**

- Skills 使用方法
- 核心概念和规范
- 快速参考表
- 学习路径

---

## 🎯 开发流程

### 1. 开发新功能

```bash
# 1. 创建功能分支
git checkout -b feature/my-feature

# 2. 参考相关 Skills 编写代码
# - API 端点参考: api_response_guide.md
# - 异常处理参考: exception-handling skill
# - 响应格式参考: api-response skill

# 3. 运行测试
pytest tests/

# 4. 代码检查
black app/
isort app/
flake8 app/

# 5. 提交代码
git add .
git commit -m "feat: 添加新功能"

# 6. 推送并创建 PR
git push origin feature/my-feature
```

### 2. 修复 Bug

```bash
# 1. 创建 Bug 修复分支
git checkout -b fix/bug-description

# 2. 编写测试复现 Bug
# tests/unit/test_bug_fix.py

# 3. 修复代码
# 参考 Skills 确保符合项目规范

# 4. 确保测试通过
pytest tests/unit/test_bug_fix.py

# 5. 提交并创建 PR
```

---

## 📖 编码规范

### API 端点开发

**推荐模式**:

```python
from fastapi import APIRouter
from app.models.api_response import ApiResponse
from app.core.exceptions import ValidationError, DataQueryError
from app.api.error_handler import handle_api_errors

router = APIRouter()

# 简单端点：使用装饰器
@router.get("/simple")
@handle_api_errors
async def simple_endpoint():
    data = await service.get_data()
    return ApiResponse.success(data=data)

# 复杂端点：手动异常处理
@router.post("/complex")
async def complex_endpoint(request: Request):
    try:
        # 验证
        if not request.valid:
            raise ValidationError(
                "参数验证失败",
                error_code="INVALID_PARAMS"
            )

        # 业务逻辑
        result = await service.process(request)

        # 检查质量
        if result.quality < 0.8:
            return ApiResponse.warning(
                data=result.dict(),
                message="处理完成，但质量较低",
                warning_code="LOW_QUALITY"
            )

        return ApiResponse.success(data=result)

    except ValidationError as e:
        return ApiResponse.bad_request(
            message=e.message,
            data={"error_code": e.error_code, **e.context}
        )
```

### 异常处理

**规范**:
1. 总是使用业务异常类（`BackendError` 系列）
2. 提供 `error_code`（大写下划线命名）
3. 添加丰富的 `context`

```python
# ✅ 推荐
raise DataQueryError(
    "股票数据不存在",
    error_code="STOCK_NOT_FOUND",
    stock_code="000001",
    date_range="2024-01-01至2024-12-31"
)

# ❌ 避免
raise Exception("数据不存在")
```

### 响应格式

**规范**:
1. 统一使用 `ApiResponse`
2. 提供有意义的 `message`
3. 成功时添加有用的元数据
4. 错误时包含 `error_code`

```python
# ✅ 推荐
return ApiResponse.success(
    data=result,
    message="回测完成",
    total_trades=150,
    sharpe_ratio=1.52,
    elapsed_time="5.2s"
)

# ❌ 避免
return {"code": 200, "data": result}
```

---

## 🔗 相关文档

### 架构文档
- [技术栈](../architecture/tech_stack.md)
- [系统架构](../architecture/)

### API 文档
- [API 参考](../api_reference/README.md)

### 部署文档
- [部署指南](../deployment/)

---

## ❓ 常见问题

### Q: 何时使用 `@handle_api_errors`，何时手动 try-except？

**A**:
- **简单端点**：使用 `@handle_api_errors`，快速开发
- **复杂业务逻辑**：手动 `try-except`，精细控制错误响应

### Q: 何时使用 warning 状态？

**A**: 当操作成功但存在需要注意的问题时：
- 数据质量较低
- 部分数据缺失已填充
- 使用了降级方案
- 结果可能不可靠

### Q: error_code 如何命名？

**A**:
- 使用 `UPPER_SNAKE_CASE` 格式
- 语义清晰：`STOCK_NOT_FOUND`, `INVALID_DATE_RANGE`
- 可分类：`DB_*`, `API_*`, `VALIDATION_*`

---

## 📚 学习资源

### 推荐阅读顺序

1. **新手入门**:
   - [API Response 使用指南](api_response_guide.md)
   - [Exception Handling Skill](../../.claude/skills/exception-handling.md)

2. **深入学习**:
   - [API Response Skill](../../.claude/skills/api-response.md)（详细最佳实践）
   - [Skills README](../../.claude/skills/README.md)（核心概念）

3. **实践**:
   - 参考现有 API 端点代码
   - 编写自己的 API 端点
   - Code Review 时对照 Skills 检查

---

**版本**: 1.0.0
**最后更新**: 2026-02-01
**维护者**: Stock Analysis Team
