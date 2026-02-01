# Backend 测试文档

## 📁 目录结构

```
tests/
├── conftest.py                           # Pytest 全局配置
├── unit/                                 # 单元测试
│   ├── api/
│   │   └── test_stocks_api.py           # Stocks API 单元测试
│   ├── core_adapters/                   # Core Adapters 单元测试
│   └── services/                        # Services 单元测试
├── integration/                          # 集成测试
│   └── api/
│       └── test_stocks_api_integration.py  # Stocks API 集成测试
└── README.md                            # 本文档
```

## 🧪 测试分类

### 1. 单元测试 (Unit Tests)

**路径**: `tests/unit/`

**特点**:
- 使用 Mock 隔离外部依赖
- 测试单个函数/方法的逻辑
- 运行速度快
- 不需要数据库连接

**运行**:
```bash
pytest tests/unit/ -v
```

**示例**:
```python
# tests/unit/api/test_stocks_api.py
async def test_get_stock_list_success():
    """测试成功获取股票列表（使用 Mock）"""
    with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
        mock_adapter.get_stock_list = AsyncMock(return_value=mock_stocks)
        response = await get_stock_list(...)
        assert response["code"] == 200
```

### 2. 集成测试 (Integration Tests)

**路径**: `tests/integration/`

**特点**:
- 测试多个组件的集成
- 需要真实的数据库连接
- 验证端到端的数据流
- 运行速度较慢

**运行**:
```bash
pytest tests/integration/ -v -m integration
```

**示例**:
```python
# tests/integration/api/test_stocks_api_integration.py
async def test_get_stock_list_integration():
    """测试真实的 API 调用（需要数据库）"""
    async with AsyncClient(app=app, base_url=BASE_URL) as client:
        response = await client.get("/api/stocks/list")
        assert response.status_code == 200
```

### 3. 性能测试 (Performance Tests)

**路径**: `tests/integration/` (标记为 `@pytest.mark.performance`)

**特点**:
- 测试并发性能
- 测试响应时间
- 默认跳过，手动运行

**运行**:
```bash
pytest tests/integration/ -v -m performance
```

## 🚀 快速开始

### 安装依赖

```bash
cd backend
pip install -r requirements-dev.txt
```

### 运行所有测试

```bash
pytest
```

### 运行特定测试

```bash
# 只运行单元测试
pytest tests/unit/ -v

# 只运行集成测试
pytest tests/integration/ -v -m integration

# 运行特定文件
pytest tests/unit/api/test_stocks_api.py -v

# 运行特定测试类
pytest tests/unit/api/test_stocks_api.py::TestGetStockList -v

# 运行特定测试方法
pytest tests/unit/api/test_stocks_api.py::TestGetStockList::test_get_stock_list_success -v
```

### 查看覆盖率

```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 打开 HTML 报告
open htmlcov/index.html
```

## 📊 测试覆盖范围

### Stocks API 测试矩阵

| 端点 | 单元测试 | 集成测试 | 性能测试 |
|------|---------|---------|---------|
| GET /api/stocks/list | ✅ | ✅ | ✅ |
| GET /api/stocks/{code} | ✅ | ✅ | - |
| GET /api/stocks/{code}/daily | ✅ | ✅ | - |
| POST /api/stocks/update | ✅ | ✅ | - |
| GET /api/stocks/{code}/minute | ✅ | ✅ | - |

### 测试场景

#### GET /api/stocks/list

**单元测试**:
- [x] 成功获取股票列表
- [x] 按市场过滤
- [x] 搜索功能
- [x] 分页功能
- [x] 空结果处理
- [x] 错误处理

**集成测试**:
- [x] 真实 API 调用
- [x] 市场过滤集成
- [x] 搜索集成
- [x] 分页集成
- [x] 边界测试

**性能测试**:
- [x] 并发请求
- [x] 响应时间

#### GET /api/stocks/{code}

**单元测试**:
- [x] 成功获取股票信息
- [x] 股票不存在
- [x] 错误处理

**集成测试**:
- [x] 真实 API 调用
- [x] 股票不存在

#### GET /api/stocks/{code}/daily

**单元测试**:
- [x] 成功获取日线数据
- [x] 记录数限制
- [x] 空数据处理
- [x] 无效日期格式

**集成测试**:
- [x] 真实 API 调用
- [x] 数据限制

#### GET /api/stocks/{code}/minute

**单元测试**:
- [x] 成功获取分时数据
- [x] 非交易日处理
- [x] 空数据处理
- [x] 默认日期处理
- [x] 无效日期格式

**集成测试**:
- [x] 真实 API 调用

## 🛠️ 测试工具

### Pytest 插件

```bash
pytest-asyncio     # 异步测试支持
pytest-cov         # 覆盖率报告
pytest-mock        # Mock 支持
httpx              # HTTP 客户端（异步）
```

### Mock 策略

```python
# 1. Mock 整个 Adapter
with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
    mock_adapter.get_stock_list = AsyncMock(return_value=mock_data)

# 2. Mock 特定方法
@patch('app.core_adapters.data_adapter.DataAdapter.get_stock_list')
async def test_example(mock_get_stock_list):
    mock_get_stock_list.return_value = mock_data

# 3. Mock 异步方法
mock_adapter.get_stock_list = AsyncMock(return_value=mock_data)
```

## 📝 编写测试的最佳实践

### 1. 使用 AAA 模式

```python
async def test_example():
    # Arrange: 准备测试数据
    mock_data = [...]

    # Act: 执行测试
    response = await get_stock_list(...)

    # Assert: 验证结果
    assert response["code"] == 200
```

### 2. 清晰的测试命名

```python
# ✅ 好的命名
async def test_get_stock_list_with_market_filter():
    """测试按市场过滤股票列表"""

# ❌ 不好的命名
async def test_1():
    """测试"""
```

### 3. 独立的测试

每个测试应该：
- 独立运行
- 不依赖其他测试
- 可以任意顺序运行

### 4. 使用夹具 (Fixtures)

```python
@pytest.fixture
def sample_stocks():
    """样例股票数据"""
    return [{"code": "000001", ...}]

async def test_example(sample_stocks):
    # 使用夹具
    assert len(sample_stocks) > 0
```

## 🐛 调试测试

### 1. 运行单个测试

```bash
pytest tests/unit/api/test_stocks_api.py::test_get_stock_list_success -v
```

### 2. 打印调试信息

```bash
pytest -v -s  # -s 显示 print 输出
```

### 3. 进入调试模式

```bash
pytest --pdb  # 失败时进入 pdb
```

### 4. 查看详细日志

```bash
pytest -v --log-cli-level=DEBUG
```

## 📈 CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          pip install -r requirements-dev.txt
          pytest tests/unit/ -v
```

## 📚 参考资料

- [Pytest 官方文档](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI 测试指南](https://fastapi.tiangolo.com/tutorial/testing/)

## ✅ 测试检查清单

在提交代码前，确保：

- [ ] 所有单元测试通过
- [ ] 代码覆盖率 > 80%
- [ ] 集成测试通过（如果修改了 API）
- [ ] 没有跳过的测试（除非有充分理由）
- [ ] 测试命名清晰
- [ ] 测试文档完整

## 🔄 持续改进

TODO:
- [ ] 添加更多边界测试
- [ ] 增加性能基准测试
- [ ] 添加 E2E 测试
- [ ] 集成 mutation testing
