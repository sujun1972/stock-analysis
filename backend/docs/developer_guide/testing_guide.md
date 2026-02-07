# Backend 测试框架实施指南

**版本**: v1.0
**创建日期**: 2026-02-01
**目标**: 从 0% 到 60% 测试覆盖率

---

## 目录

1. [测试策略](#测试策略)
2. [测试框架选型](#测试框架选型)
3. [环境搭建](#环境搭建)
4. [测试编写指南](#测试编写指南)
5. [最佳实践](#最佳实践)
6. [CI/CD 集成](#cicd-集成)

---

## 测试策略

### 测试金字塔

```
           /\
          /E2E\ (5%)
         /────\  端到端测试
        /      \  - 关键业务流程
       / 集成测试 \ (25%)
      /  (25%)  \  - API 测试
     /            \  - 数据库集成
    /  单元测试     \ (70%)
   /   (70%)      \  - Service 层
  /________________\  - Repository 层
                      - Utils 层
```

### 覆盖率目标

| 阶段 | 时间 | 目标覆盖率 | 重点 |
|------|------|-----------|------|
| Phase 1 | Week 1-2 | 30% | Service 层核心功能 |
| Phase 2 | Week 3-4 | 50% | API 集成测试 |
| Phase 3 | Week 5-6 | 60%+ | 边界情况、异常处理 |

---

## 测试框架选型

### 推荐技术栈

```python
# requirements-dev.txt

# 核心测试框架
pytest>=7.4.0                # 强大的测试框架
pytest-asyncio>=0.21.0       # 异步测试支持
pytest-cov>=4.1.0            # 覆盖率报告
pytest-mock>=3.11.0          # Mock 工具

# HTTP 测试
httpx>=0.25.0                # 异步 HTTP 客户端

# 测试数据
factory-boy>=3.3.0           # 测试数据工厂
faker>=19.0.0                # 假数据生成

# 代码质量
black>=23.0.0                # 代码格式化
flake8>=6.0.0                # 代码检查
mypy>=1.4.0                  # 类型检查
isort>=5.12.0                # 导入排序

# 性能测试
locust>=2.15.0               # 负载测试
```

### 为什么选择 pytest?

**优势**:
- ✅ 简洁的语法（无需继承 TestCase）
- ✅ 强大的 fixture 机制
- ✅ 丰富的插件生态
- ✅ 详细的错误报告
- ✅ 参数化测试支持

**示例对比**:

```python
# ❌ unittest (冗长)
import unittest

class TestStockService(unittest.TestCase):
    def test_get_stock_list(self):
        service = StockService()
        result = service.get_stock_list()
        self.assertEqual(len(result), 100)

# ✅ pytest (简洁)
def test_get_stock_list():
    service = StockService()
    result = service.get_stock_list()
    assert len(result) == 100
```

---

## 环境搭建

### Step 1: 安装依赖

```bash
# 1. 创建开发依赖文件
cat > requirements-dev.txt <<'EOF'
# 测试框架
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-xdist>=3.3.0          # 并行测试

# HTTP 测试
httpx>=0.25.0

# 测试数据
factory-boy>=3.3.0
faker>=19.0.0

# 代码质量
black>=23.0.0
flake8>=6.0.0
mypy>=1.4.0
isort>=5.12.0

# 性能测试
locust>=2.15.0
EOF

# 2. 安装
pip install -r requirements-dev.txt
```

### Step 2: 创建测试目录结构

```bash
# 创建目录
mkdir -p backend/tests/{unit/{services,repositories,utils},integration/api,e2e,fixtures,performance}

# 创建初始化文件
touch backend/tests/__init__.py
touch backend/tests/unit/__init__.py
touch backend/tests/integration/__init__.py
touch backend/tests/e2e/__init__.py
```

**目录结构**:

```
backend/tests/
├── __init__.py
├── conftest.py                    # 全局 fixtures
├── pytest.ini                     # pytest 配置
├── unit/                          # 单元测试 (70%)
│   ├── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── test_database_service.py
│   │   ├── test_backtest_service.py
│   │   ├── test_feature_service.py
│   │   └── test_data_service.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── test_stock_repository.py
│   │   └── test_config_repository.py
│   └── utils/
│       ├── __init__.py
│       ├── test_data_cleaning.py
│       └── test_retry.py
├── integration/                   # 集成测试 (25%)
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── test_stocks_api.py
│   │   ├── test_backtest_api.py
│   │   ├── test_ml_api.py
│   │   └── test_auth_api.py
│   └── database/
│       ├── __init__.py
│       └── test_database_integration.py
├── e2e/                           # 端到端测试 (5%)
│   ├── __init__.py
│   └── test_full_workflow.py
├── fixtures/                      # 测试数据
│   ├── __init__.py
│   ├── stock_data.py
│   └── factories.py
└── performance/                   # 性能测试
    ├── __init__.py
    └── locustfile.py
```

### Step 3: 配置 pytest

```ini
# backend/tests/pytest.ini
[pytest]
# 测试路径
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# 异步支持
asyncio_mode = auto

# 覆盖率配置
addopts =
    --cov=app
    --cov-report=html
    --cov-report=term-missing
    --cov-report=xml
    --cov-fail-under=30
    -v
    --tb=short
    --strict-markers

# 标记
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests (> 1s)
    async: Async tests

# 日志配置
log_cli = true
log_cli_level = INFO
```

### Step 4: 创建全局 Fixtures

```python
# backend/tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.config import settings
from app.core.database import get_db
from app.models.db_models import Base

# ==================== 事件循环 ====================

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环 (session 级别)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# ==================== 数据库 ====================

@pytest.fixture(scope="session")
async def test_engine():
    """测试数据库引擎"""
    engine = create_async_engine(
        settings.TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True
    )

    # 创建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # 清理
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()

@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """数据库会话 (每个测试独立事务)"""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()  # 测试结束后回滚

# ==================== HTTP 客户端 ====================

@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """HTTP 测试客户端"""

    # 覆盖数据库依赖
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    # 清理
    app.dependency_overrides.clear()

# ==================== 认证 ====================

@pytest.fixture
def auth_headers():
    """认证头"""
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": "test_user"})
    return {"Authorization": f"Bearer {token}"}
```

---

## 测试编写指南

### 1. 单元测试 (Unit Tests)

#### 1.1 Service 层测试

**目标**: 测试业务逻辑，隔离外部依赖

**示例**: DatabaseService

```python
# tests/unit/services/test_database_service.py
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app.services.database_service import DatabaseService
from app.core.exceptions import DataNotFoundError

class TestDatabaseService:
    """DatabaseService 单元测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock 数据库"""
        db = Mock()
        db.execute_query = AsyncMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """创建 Service 实例"""
        return DatabaseService(db=mock_db)

    # ==================== 正常场景 ====================

    async def test_get_stock_list_success(self, service, mock_db):
        """测试获取股票列表 - 成功"""
        # Arrange (准备)
        mock_db.execute_query.return_value = {
            'total': 100,
            'data': [
                {'code': '000001', 'name': '平安银行'},
                {'code': '000002', 'name': '万科A'}
            ]
        }

        # Act (执行)
        result = await service.get_stock_list(limit=10)

        # Assert (断言)
        assert result['total'] == 100
        assert len(result['data']) == 2
        assert result['data'][0]['code'] == '000001'
        mock_db.execute_query.assert_called_once()

    async def test_get_stock_list_with_filter(self, service, mock_db):
        """测试获取股票列表 - 带筛选"""
        # Arrange
        mock_db.execute_query.return_value = {
            'total': 50,
            'data': [{'code': '000001', 'name': '平安银行'}]
        }

        # Act
        result = await service.get_stock_list(market="主板", limit=10)

        # Assert
        assert result['total'] == 50
        assert mock_db.execute_query.called

    # ==================== 边界情况 ====================

    async def test_get_stock_list_empty_result(self, service, mock_db):
        """测试获取股票列表 - 空结果"""
        # Arrange
        mock_db.execute_query.return_value = {'total': 0, 'data': []}

        # Act
        result = await service.get_stock_list()

        # Assert
        assert result['total'] == 0
        assert result['data'] == []

    # ==================== 异常场景 ====================

    async def test_get_stock_list_database_error(self, service, mock_db):
        """测试获取股票列表 - 数据库错误"""
        # Arrange
        mock_db.execute_query.side_effect = Exception("Database connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await service.get_stock_list()

        assert "Database connection failed" in str(exc_info.value)

# ==================== 参数化测试 ====================

@pytest.mark.parametrize("market,expected_count", [
    ("主板", 50),
    ("创业板", 30),
    ("科创板", 20),
])
async def test_get_stock_list_by_market(service, mock_db, market, expected_count):
    """测试不同市场的股票列表"""
    mock_db.execute_query.return_value = {
        'total': expected_count,
        'data': []
    }

    result = await service.get_stock_list(market=market)
    assert result['total'] == expected_count
```

#### 1.2 Repository 层测试

**示例**: StockRepository

```python
# tests/unit/repositories/test_stock_repository.py
import pytest
from app.repositories.stock_repository import StockRepository
from app.models.db_models import StockBasic

class TestStockRepository:
    """StockRepository 单元测试"""

    @pytest.fixture
    async def repository(self, db_session):
        """创建 Repository 实例"""
        return StockRepository(session=db_session)

    @pytest.fixture
    async def sample_stocks(self, db_session):
        """创建测试数据"""
        stocks = [
            StockBasic(
                code="000001",
                name="平安银行",
                market="主板",
                industry="银行",
                status="正常"
            ),
            StockBasic(
                code="000002",
                name="万科A",
                market="主板",
                industry="房地产",
                status="正常"
            )
        ]
        db_session.add_all(stocks)
        await db_session.commit()
        return stocks

    async def test_get_by_market(self, repository, sample_stocks):
        """测试按市场查询"""
        # Act
        result = await repository.get_by_market("主板")

        # Assert
        assert len(result) == 2
        assert all(s.market == "主板" for s in result)

    async def test_search_by_code(self, repository, sample_stocks):
        """测试按代码搜索"""
        # Act
        result = await repository.search("000001")

        # Assert
        assert len(result) == 1
        assert result[0].code == "000001"

    async def test_search_by_name(self, repository, sample_stocks):
        """测试按名称搜索"""
        # Act
        result = await repository.search("平安")

        # Assert
        assert len(result) == 1
        assert "平安" in result[0].name
```

#### 1.3 Utils 层测试

**示例**: 数据清洗工具

```python
# tests/unit/utils/test_data_cleaning.py
import pytest
import pandas as pd
import numpy as np
from app.utils.data_cleaning import clean_value, clean_records, remove_outliers

class TestDataCleaning:
    """数据清洗工具测试"""

    def test_clean_value_none(self):
        """测试清洗 None 值"""
        assert clean_value(None) is None

    def test_clean_value_nan(self):
        """测试清洗 NaN 值"""
        assert clean_value(np.nan) is None

    def test_clean_value_inf(self):
        """测试清洗无穷大"""
        assert clean_value(np.inf) is None
        assert clean_value(-np.inf) is None

    def test_clean_value_normal(self):
        """测试正常值"""
        assert clean_value(3.14) == 3.14
        assert clean_value("test") == "test"

    @pytest.mark.parametrize("input_val,expected", [
        (None, None),
        (np.nan, None),
        (np.inf, None),
        (123.45, 123.45),
        ("hello", "hello"),
    ])
    def test_clean_value_parametrized(self, input_val, expected):
        """参数化测试"""
        assert clean_value(input_val) == expected

    def test_remove_outliers(self):
        """测试移除异常值"""
        # Arrange
        df = pd.DataFrame({
            'value': [1, 2, 3, 4, 5, 100]  # 100 是异常值
        })

        # Act
        result = remove_outliers(df, 'value', threshold=3)

        # Assert
        assert len(result) == 5
        assert 100 not in result['value'].values
```

---

### 2. 集成测试 (Integration Tests)

#### 2.1 API 集成测试

**目标**: 测试完整的 API 端点，包括路由、验证、数据库交互

**示例**: Stocks API

```python
# tests/integration/api/test_stocks_api.py
import pytest
from httpx import AsyncClient

class TestStocksAPI:
    """Stocks API 集成测试"""

    async def test_get_stocks_returns_200(self, client: AsyncClient):
        """测试获取股票列表 - 返回 200"""
        # Act
        response = await client.get("/api/stocks")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert 'data' in data

    async def test_get_stocks_with_pagination(self, client: AsyncClient):
        """测试分页"""
        # Act
        response = await client.get("/api/stocks?page=1&page_size=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'items' in data['data']
        assert len(data['data']['items']) <= 10
        assert data['data']['page'] == 1
        assert data['data']['page_size'] == 10

    async def test_get_stocks_with_market_filter(self, client: AsyncClient):
        """测试市场筛选"""
        # Act
        response = await client.get("/api/stocks?market=主板")

        # Assert
        assert response.status_code == 200
        data = response.json()
        for item in data['data']['items']:
            assert item['market'] == "主板"

    async def test_get_stock_detail(self, client: AsyncClient):
        """测试获取股票详情"""
        # Act
        response = await client.get("/api/stocks/000001")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data['data']['code'] == "000001"

    async def test_get_stock_detail_not_found(self, client: AsyncClient):
        """测试获取不存在的股票"""
        # Act
        response = await client.get("/api/stocks/999999")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data['code'] == 404

    async def test_search_stocks(self, client: AsyncClient):
        """测试搜索股票"""
        # Act
        response = await client.get("/api/stocks?search=平安")

        # Assert
        assert response.status_code == 200
        data = response.json()
        for item in data['data']['items']:
            assert "平安" in item['name'] or "平安" in item['code']
```

#### 2.2 认证 API 测试

```python
# tests/integration/api/test_auth_api.py
import pytest
from httpx import AsyncClient

class TestAuthAPI:
    """认证 API 测试"""

    async def test_login_success(self, client: AsyncClient):
        """测试登录成功"""
        # Act
        response = await client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data['data']
        assert data['data']['token_type'] == "bearer"

    async def test_login_invalid_credentials(self, client: AsyncClient):
        """测试登录失败 - 错误凭证"""
        # Act
        response = await client.post(
            "/api/auth/login",
            json={
                "username": "admin",
                "password": "wrong_password"
            }
        )

        # Assert
        assert response.status_code == 401

    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """测试访问受保护端点 - 无 token"""
        # Act
        response = await client.get("/api/stocks/favorites")

        # Assert
        assert response.status_code == 401

    async def test_protected_endpoint_with_token(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """测试访问受保护端点 - 有 token"""
        # Act
        response = await client.get(
            "/api/stocks/favorites",
            headers=auth_headers
        )

        # Assert
        assert response.status_code == 200
```

---

### 3. 端到端测试 (E2E Tests)

**目标**: 测试完整的业务流程

**示例**: 回测工作流

```python
# tests/e2e/test_full_workflow.py
import pytest
from httpx import AsyncClient

@pytest.mark.e2e
class TestBacktestWorkflow:
    """回测完整工作流测试"""

    async def test_full_backtest_workflow(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """测试完整回测流程"""

        # Step 1: 获取股票列表
        response = await client.get(
            "/api/stocks?market=主板&limit=5",
            headers=auth_headers
        )
        assert response.status_code == 200
        stocks = response.json()['data']['items']
        stock_codes = [s['code'] for s in stocks]

        # Step 2: 创建回测任务
        response = await client.post(
            "/api/backtest",
            headers=auth_headers,
            json={
                "stock_codes": stock_codes,
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "strategy": {
                    "type": "ma_cross",
                    "short_window": 5,
                    "long_window": 20
                }
            }
        )
        assert response.status_code == 200
        task_id = response.json()['data']['task_id']

        # Step 3: 查询回测结果
        response = await client.get(
            f"/api/backtest/{task_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()['data']

        # 验证回测结果
        assert 'total_return' in result
        assert 'sharpe_ratio' in result
        assert 'max_drawdown' in result
```

---

## 最佳实践

### 1. AAA 模式 (Arrange-Act-Assert)

```python
async def test_example():
    # Arrange (准备) - 设置测试数据和 Mock
    service = StockService()
    expected_result = 100

    # Act (执行) - 调用被测函数
    result = await service.get_stock_count()

    # Assert (断言) - 验证结果
    assert result == expected_result
```

### 2. 使用 Fixtures 管理依赖

```python
# ✅ 好的做法
@pytest.fixture
def stock_service():
    return StockService()

def test_get_stocks(stock_service):
    result = stock_service.get_stocks()
    assert result is not None

# ❌ 不好的做法
def test_get_stocks():
    service = StockService()  # 每个测试都重复创建
    result = service.get_stocks()
    assert result is not None
```

### 3. 参数化测试减少重复

```python
# ✅ 好的做法
@pytest.mark.parametrize("market,expected_count", [
    ("主板", 50),
    ("创业板", 30),
    ("科创板", 20),
])
def test_get_stocks_by_market(market, expected_count):
    result = get_stocks(market)
    assert len(result) == expected_count

# ❌ 不好的做法
def test_get_stocks_main_board():
    assert len(get_stocks("主板")) == 50

def test_get_stocks_chinext():
    assert len(get_stocks("创业板")) == 30

def test_get_stocks_star():
    assert len(get_stocks("科创板")) == 20
```

### 4. 使用 Factory 生成测试数据

```python
# tests/fixtures/factories.py
import factory
from faker import Faker
from app.models.db_models import StockBasic

fake = Faker('zh_CN')

class StockFactory(factory.Factory):
    """股票数据工厂"""
    class Meta:
        model = StockBasic

    code = factory.Sequence(lambda n: f"{n:06d}")
    name = factory.LazyAttribute(lambda _: fake.company())
    market = factory.Iterator(["主板", "创业板", "科创板"])
    industry = factory.LazyAttribute(lambda _: fake.job())
    status = "正常"

# 使用
def test_with_factory():
    stocks = StockFactory.create_batch(10)
    assert len(stocks) == 10
```

### 5. Mock 外部依赖

```python
# ✅ 好的做法 - Mock 外部 API
@patch('app.services.data_service.fetch_external_data')
async def test_fetch_stock_data(mock_fetch):
    # Arrange
    mock_fetch.return_value = {"code": "000001", "price": 10.5}

    # Act
    result = await fetch_stock_data("000001")

    # Assert
    assert result['price'] == 10.5
    mock_fetch.assert_called_once_with("000001")
```

### 6. 测试命名规范

```python
# ✅ 好的命名
def test_get_stock_list_returns_correct_count():
    """清晰描述测试意图"""
    pass

def test_get_stock_list_with_invalid_market_raises_validation_error():
    """描述输入和预期行为"""
    pass

# ❌ 不好的命名
def test_1():
    pass

def test_stocks():
    pass
```

---

## CI/CD 集成

### GitHub Actions 配置

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: timescale/timescaledb:latest-pg14
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        env:
          DATABASE_HOST: localhost
          DATABASE_PORT: 5432
          DATABASE_NAME: test_db
          DATABASE_USER: test_user
          DATABASE_PASSWORD: test_pass
          REDIS_HOST: localhost
          REDIS_PORT: 6379
        run: |
          pytest tests/ \
            --cov=app \
            --cov-report=xml \
            --cov-report=html \
            --cov-fail-under=30 \
            -v

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Archive coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: htmlcov/
```

---

## 测试执行命令

### 基本命令

```bash
# 运行所有测试
pytest

# 运行特定目录
pytest tests/unit/
pytest tests/integration/

# 运行特定文件
pytest tests/unit/services/test_database_service.py

# 运行特定测试
pytest tests/unit/services/test_database_service.py::TestDatabaseService::test_get_stock_list_success

# 运行带标记的测试
pytest -m unit          # 只运行单元测试
pytest -m integration   # 只运行集成测试
pytest -m "not slow"    # 排除慢速测试
```

### 覆盖率报告

```bash
# 生成覆盖率报告
pytest --cov=app --cov-report=html --cov-report=term

# 查看未覆盖的代码
pytest --cov=app --cov-report=term-missing

# 覆盖率不达标时失败
pytest --cov=app --cov-fail-under=60
```

### 并行测试

```bash
# 使用多核并行测试
pytest -n auto          # 自动检测 CPU 核心数
pytest -n 4             # 使用 4 个进程
```

### 性能测试

```bash
# 使用 Locust 进行负载测试
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

---

## 测试数据管理

### 使用 Fixtures 文件

```python
# tests/fixtures/stock_data.py
SAMPLE_STOCKS = [
    {
        "code": "000001",
        "name": "平安银行",
        "market": "主板",
        "industry": "银行"
    },
    {
        "code": "000002",
        "name": "万科A",
        "market": "主板",
        "industry": "房地产"
    }
]

SAMPLE_DAILY_DATA = [
    {
        "code": "000001",
        "date": "2023-01-01",
        "open": 10.0,
        "high": 10.5,
        "low": 9.8,
        "close": 10.3,
        "volume": 1000000
    }
]
```

---

## 下一步

1. ✅ 按照本指南搭建测试环境
2. ✅ 编写第一批单元测试（DatabaseService）
3. ✅ 配置 CI/CD 自动化测试
4. ✅ 逐步提升覆盖率到 60%

---

**文档版本**: v1.0
**最后更新**: 2026-02-01
**维护者**: 开发团队
