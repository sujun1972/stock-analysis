# Backend 优化实施路线图

**版本**: v2.2 (任务 0.1-0.2 已完成)
**制定日期**: 2026-02-01
**最后更新**: 2026-02-01 23:30
**预计完成**: 2026-04-15 (10 周)
**负责人**: 开发团队

**重要变更**: 发现 Backend 架构设计缺陷，取消了部分优化任务（Core 已有完整实现）

---

## 📊 任务进度跟踪

### Phase 0: 架构修正 (Week 1-4)

| 任务 | 状态 | 完成日期 | 交付物 |
|-----|------|---------|--------|
| 0.1 审计 Core 功能清单 | ✅ 完成 | 2026-02-01 | [审计报告](./core_功能审计报告.md) |
| 0.2 创建 Core Adapters | ✅ 完成 | 2026-02-01 | [Adapters 实现](../../app/core_adapters/) |
| 0.3 重写 Stocks API | ⏳ 待开始 | - | - |
| 0.4 重写 Features API | ⏳ 待开始 | - | - |
| 0.5 重写所有 API 端点 | ⏳ 待开始 | - | - |
| 0.6 删除冗余代码 | ⏳ 待开始 | - | - |

**Phase 0 整体进度**: 2/6 任务完成 (33.3%)

---

## 路线图总览

本路线图基于[深度分析报告](./optimization_analysis.md)，提供详细的实施计划、时间表和资源分配。

**⚠️ 重要更新**: 发现 Backend 架构设计缺陷，路线图已调整

```
┌─────────────────────────────────────────────────────────┐
│             优化路线图时间线 (10 周)                      │
├─────────────────────────────────────────────────────────┤
│ Week 1-2   │ 🔴 架构修正：Backend 改为调用 Core        │
│ Week 3-4   │ 🔴 删除冗余代码 + 功能验证                  │
│ Week 5-6   │ 🔴 安全修复 + 测试框架搭建                  │
│ Week 7-8   │ 🟡 Redis 缓存 + 异常处理统一               │
│ Week 9-10  │ 🟢 性能优化 + 监控系统                      │
└─────────────────────────────────────────────────────────┘

🔴 P0 - 必须完成  🟡 P1 - 应该完成  🟢 P2 - 可选完成

已取消的优化（Core 已有完整实现）：
❌ SQLAlchemy ORM 迁移
❌ Repository 层完善
❌ 异步驱动迁移
❌ 依赖注入容器
```

---

## Phase 0: 架构修正（优先级最高）(Week 1-4)

### 背景

在代码审查中发现：**Backend 重复实现了 Core 项目已有的功能**

- ❌ Backend 有 `DatabaseService`、`DataService`、`FeatureService`
- ✅ Core 已有 `DatabaseManager`、`DataQueryManager`、`FeatureEngineer`
- 🔴 **代码重复率 40%+**（约 6,000 行重复代码）

**正确架构**: Backend 应该是 **薄层 API 网关**，调用 Core 的方法

详细分析见 [优化分析报告 - 架构设计缺陷](./optimization_analysis.md#八点三架构设计缺陷最重要发现)

---

### Week 1: 审计 Core 功能 + 创建 Adapters

#### 任务 0.1: 审计 Core 功能清单 (P0) ✅ **已完成**

**预计时间**: 1 天
**实际时间**: 1 天
**负责人**: 后端开发
**优先级**: 🔴 P0
**完成日期**: 2026-02-01

**子任务**:

1. ✅ **列出 Core 所有模块** (半天)
   - 扫描了 Core 项目 205 个 Python 文件
   - 详细记录了 16 个主要模块
   - 统计了各模块代码量：
     - `database/`: 2,357 行
     - `features/`: 3,803 行
     - `backtest/`: 4,282 行
     - `models/`: ~4,500 行
     - `data_pipeline/`: ~3,000 行
     - 总计: ~35,000 行

2. ✅ **对比 Backend 实现** (半天)
   - 详细对比了 Backend Services 与 Core 模块
   - 识别出 8 个完全重复的文件 (1,797 行)
   - 识别出 3 个部分重复的文件 (1,181 行)
   - 总重复率: 41.0%

**验收标准**:
- ✅ 完整的 Core 功能清单（Markdown 表格）- **已完成**
- ✅ Backend vs Core 功能对比表 - **已完成**
- ✅ 识别所有重复代码 - **已完成**

**交付物**:
- 📄 [Core 功能审计报告](./core_功能审计报告.md) (完整的 8 章节审计文档)

**关键发现**:
- 🔴 Backend 存在 1,797 行完全重复代码 (24.8%)
- 🔴 总重复率达到 41.0% (含部分重复)
- ✅ 验证了架构修正的必要性
- ✅ Core 项目功能完整，可以完全替代 Backend Services

---

#### 任务 0.2: 创建 Core Adapters (P0) ✅ **已完成**

**预计时间**: 3 天
**实际时间**: 1 天
**负责人**: 后端开发
**优先级**: 🔴 P0
**完成日期**: 2026-02-01

**目标**: 为 Core 功能创建异步包装器

**子任务**:

1. **创建 Adapters 目录** (1 小时)
   ```bash
   mkdir -p backend/app/core_adapters
   touch backend/app/core_adapters/__init__.py
   touch backend/app/core_adapters/data_adapter.py
   touch backend/app/core_adapters/feature_adapter.py
   touch backend/app/core_adapters/backtest_adapter.py
   ```

2. **实现 DataAdapter** (1 天)
   ```python
   # backend/app/core_adapters/data_adapter.py
   """
   Core 数据模块的异步适配器

   将 Core 的同步方法包装为异步方法，供 FastAPI 使用
   """
   import asyncio
   from typing import List, Dict, Optional
   from datetime import date

   # 导入 Core 的类
   from src.database.data_query_manager import DataQueryManager
   from src.database.data_insert_manager import DataInsertManager

   class DataAdapter:
       """数据访问适配器"""

       def __init__(self):
           self.query_manager = DataQueryManager()
           self.insert_manager = DataInsertManager()

       async def get_stock_list(
           self,
           market: Optional[str] = None,
           status: str = "正常"
       ) -> List[Dict]:
           """异步获取股票列表"""
           return await asyncio.to_thread(
               self.query_manager.get_stock_list,
               market=market,
               status=status
           )

       async def get_stock_daily_data(
           self,
           code: str,
           start_date: date,
           end_date: date
       ) -> List[Dict]:
           """异步获取日线数据"""
           return await asyncio.to_thread(
               self.query_manager.get_daily_data,
               code=code,
               start_date=start_date,
               end_date=end_date
           )

       # ... 其他方法
   ```

3. **实现 FeatureAdapter** (1 天)
   ```python
   # backend/app/core_adapters/feature_adapter.py
   import asyncio
   from src.features.feature_engineer import FeatureEngineer

   class FeatureAdapter:
       """特征工程适配器"""

       def __init__(self):
           self.engineer = FeatureEngineer()

       async def calculate_features(
           self,
           code: str,
           start_date: date,
           end_date: date
       ):
           """异步计算特征"""
           return await asyncio.to_thread(
               self.engineer.calculate,
               code=code,
               start_date=start_date,
               end_date=end_date
           )
   ```

4. **实现 BacktestAdapter** (1 天)
   ```python
   # backend/app/core_adapters/backtest_adapter.py
   import asyncio
   from src.backtest.backtest_engine import BacktestEngine

   class BacktestAdapter:
       """回测引擎适配器"""

       def __init__(self):
           self.engine = BacktestEngine()

       async def run_backtest(
           self,
           stock_codes: List[str],
           strategy_params: Dict,
           start_date: date,
           end_date: date
       ):
           """异步运行回测"""
           return await asyncio.to_thread(
               self.engine.run,
               stock_codes=stock_codes,
               strategy_params=strategy_params,
               start_date=start_date,
               end_date=end_date
           )
   ```

**验收标准**:
- ✅ 至少 3 个 Adapter 已创建（Data, Feature, Backtest）- **已完成 (4 个)**
- ✅ 所有 Adapter 方法都是异步的 - **已完成 (45 个异步方法)**
- ✅ 单元测试通过 - **已完成 (50 个测试用例)**

**交付物**:
- 📄 [DataAdapter](../../app/core_adapters/data_adapter.py) (250 行, 11 个方法)
- 📄 [FeatureAdapter](../../app/core_adapters/feature_adapter.py) (320 行, 12 个方法)
- 📄 [BacktestAdapter](../../app/core_adapters/backtest_adapter.py) (380 行, 10 个方法)
- 📄 [ModelAdapter](../../app/core_adapters/model_adapter.py) (380 行, 12 个方法)
- 📄 [单元测试](../../tests/unit/core_adapters/) (47 个测试用例)
- 📄 [集成测试](../../tests/integration/core_adapters/) (3 个测试用例)
- 📄 [README 文档](../../app/core_adapters/README.md)
- 📄 [实现总结](../../app/core_adapters/IMPLEMENTATION_SUMMARY.md)

**关键成果**:
- ✅ 创建了 4 个完整的 Adapter (超出要求)
- ✅ 实现了 45 个异步方法
- ✅ 编写了 50 个测试用例 (覆盖率 90%+)
- ✅ 完整的文档和使用指南
- ✅ 支持 150+ 核心功能

---

### Week 2: 重写第一批 API 端点

#### 任务 0.3: 重写 Stocks API (P0)

**预计时间**: 2 天
**负责人**: 后端开发
**优先级**: 🔴 P0

**步骤**:

1. **重写 GET /api/stocks** (半天)
   ```python
   # ❌ 修改前: backend/app/api/endpoints/stocks.py
   from app.services.database_service import DatabaseService

   @router.get("/")
   async def get_stocks(...):
       service = DatabaseService()
       return await service.get_stock_list(...)  # 200 行 SQL 查询

   # ✅ 修改后
   from app.core_adapters.data_adapter import DataAdapter
   from app.models.api_response import ApiResponse

   data_adapter = DataAdapter()

   @router.get("/")
   async def get_stocks(
       market: Optional[str] = None,
       status: str = "正常",
       page: int = Query(1, ge=1),
       page_size: int = Query(20, ge=1, le=100)
   ):
       """
       获取股票列表

       Backend 只负责：
       1. 参数验证（Pydantic 自动）
       2. 调用 Core Adapter
       3. 分页处理
       4. 响应格式化
       """
       # 调用 Core（业务逻辑在 Core）
       stocks = await data_adapter.get_stock_list(
           market=market,
           status=status
       )

       # Backend 的职责：分页
       total = len(stocks)
       start = (page - 1) * page_size
       items = stocks[start:start + page_size]

       # Backend 的职责：响应格式化
       return ApiResponse.paginated(
           items=items,
           total=total,
           page=page,
           page_size=page_size
       )
   ```

2. **重写其他 Stocks 端点** (1 天)
   - GET /api/stocks/{code}
   - GET /api/stocks/search

3. **测试** (半天)
   ```bash
   # API 测试
   pytest tests/integration/api/test_stocks_api.py -v

   # 手动测试
   curl http://localhost:8000/api/stocks?market=主板&page=1
   ```

**验收标准**:
- ✅ Stocks API 全部重写完成
- ✅ 集成测试通过
- ✅ API 响应格式不变

---

#### 任务 0.4: 重写 Features API (P0)

**预计时间**: 2 天

**步骤**: 参考 Stocks API 重写流程

---

### Week 3-4: 重写剩余 API + 删除冗余代码

#### 任务 0.5: 重写所有 API 端点 (P0)

**预计时间**: 1 周

**待重写的端点**:
- [ ] GET /api/backtest
- [ ] POST /api/backtest
- [ ] GET /api/ml/train
- [ ] GET /api/data/download
- [ ] GET /api/market/calendar

---

#### 任务 0.6: 删除冗余代码 (P0)

**预计时间**: 1 周
**负责人**: 后端开发
**优先级**: 🔴 P0

**步骤**:

1. **备份代码** (1 小时)
   ```bash
   git checkout -b refactor/remove-redundant-code
   git add .
   git commit -m "backup: 架构修正前的代码"
   ```

2. **删除重复的 Services** (2 天)
   ```bash
   # 删除文件（~5,000 行）
   rm backend/app/services/database_service.py
   rm backend/app/services/data_service.py
   rm backend/app/services/feature_service.py
   rm backend/app/services/backtest_service.py

   # 保留配置相关的 Service
   # 保留 backend/app/services/config_service.py
   ```

3. **删除 Repository 层** (1 天)
   ```bash
   # 删除整个目录（~800 行）
   rm -rf backend/app/repositories/

   # 原因：Core 已有 DatabaseManager，不需要 Repository
   ```

4. **删除工具函数** (1 天)
   ```bash
   # 检查 utils/ 中的函数
   # 如果 Core 已有，则删除
   ```

5. **更新导入** (1 天)
   ```bash
   # 查找所有导入了已删除文件的地方
   grep -r "from app.services.database_service" backend/app/

   # 更新为 Adapter
   # from app.services.database_service import DatabaseService
   # 改为
   # from app.core_adapters.data_adapter import DataAdapter
   ```

6. **运行测试** (半天)
   ```bash
   pytest tests/ -v
   ```

**验收标准**:
- ✅ Services 目录减少 80% 代码
- ✅ Repositories 目录已删除
- ✅ 所有测试通过
- ✅ Backend 代码量从 17,737 行 → ~3,000 行

---

### Phase 0 验收

**里程碑**: Backend 架构修正完成

**验收标准**:
- ✅ Backend 代码量减少 **83%**
- ✅ 所有 API 端点改为调用 Core
- ✅ 没有重复的业务逻辑
- ✅ 集成测试通过
- ✅ API 响应格式不变

**预期收益**:
- 代码量: 17,737 行 → 3,000 行
- 维护成本: ↓ 90%
- 架构清晰度: 5/10 → 9/10

---

## Phase 1: 安全与测试基础 (Week 5-8)

### Week 1-2: 安全修复 + 测试框架

#### 任务 1.1: 安全漏洞修复 (P0)

**预计时间**: 2 天
**负责人**: 后端开发
**优先级**: 🔴 P0

**子任务**:

1. **移除硬编码密码** (2 小时)
   ```python
   # 修改: app/core/config.py

   # ❌ 修改前
   DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "stock_password_123")

   # ✅ 修改后
   DATABASE_PASSWORD: str = Field(..., description="数据库密码")

   @validator("DATABASE_PASSWORD")
   def validate_password(cls, v):
       if not v:
           raise ValueError("DATABASE_PASSWORD 环境变量必须设置")
       if len(v) < 12:
           raise ValueError("密码长度至少 12 位")
       return v
   ```

2. **添加 JWT 认证系统** (1 天)

   **步骤**:
   ```bash
   # 1. 安装依赖
   pip install python-jose[cryptography] passlib[bcrypt]

   # 2. 创建安全模块
   touch app/core/security.py
   touch app/models/auth.py
   touch app/api/endpoints/auth.py

   # 3. 实现 JWT 工具函数
   # 4. 创建登录/注册端点
   # 5. 添加认证依赖
   ```

   **代码**:
   ```python
   # app/core/security.py
   from datetime import datetime, timedelta
   from jose import JWTError, jwt
   from passlib.context import CryptContext

   SECRET_KEY = os.getenv("JWT_SECRET_KEY")
   ALGORITHM = "HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES = 30

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   def create_access_token(data: dict) -> str:
       to_encode = data.copy()
       expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
       to_encode.update({"exp": expire})
       return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)

   def get_password_hash(password: str) -> str:
       return pwd_context.hash(password)
   ```

3. **SQL 注入审计** (半天)
   - 检查所有 SQL 查询
   - 确保使用参数化查询
   - 添加输入验证

**验收标准**:
- ✅ 无硬编码密码
- ✅ JWT 认证可用
- ✅ 所有 SQL 查询使用参数化

---

#### 任务 1.2: 测试框架搭建 (P0)

**预计时间**: 3 天
**负责人**: 后端开发 + QA
**优先级**: 🔴 P0

**子任务**:

1. **安装测试依赖** (1 小时)
   ```bash
   # 创建 requirements-dev.txt
   cat > requirements-dev.txt <<EOF
   # 测试框架
   pytest>=7.4.0
   pytest-asyncio>=0.21.0
   pytest-cov>=4.1.0
   pytest-mock>=3.11.0

   # HTTP 客户端
   httpx>=0.25.0

   # 测试数据
   factory-boy>=3.3.0
   faker>=19.0.0

   # 代码质量
   black>=23.0.0
   flake8>=6.0.0
   mypy>=1.4.0
   EOF

   pip install -r requirements-dev.txt
   ```

2. **创建测试目录结构** (1 小时)
   ```bash
   mkdir -p tests/{unit/{services,repositories,utils},integration/api,e2e}
   touch tests/__init__.py
   touch tests/conftest.py
   touch tests/unit/__init__.py
   touch tests/integration/__init__.py
   touch tests/e2e/__init__.py
   ```

3. **编写测试配置** (2 小时)
   ```python
   # tests/conftest.py
   import pytest
   import asyncio
   from typing import AsyncGenerator
   from httpx import AsyncClient
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
   from app.main import app
   from app.core.config import settings

   @pytest.fixture(scope="session")
   def event_loop():
       """创建事件循环"""
       loop = asyncio.get_event_loop_policy().new_event_loop()
       yield loop
       loop.close()

   @pytest.fixture
   async def client() -> AsyncGenerator[AsyncClient, None]:
       """HTTP 测试客户端"""
       async with AsyncClient(app=app, base_url="http://test") as ac:
           yield ac

   @pytest.fixture
   async def db_session() -> AsyncGenerator[AsyncSession, None]:
       """数据库测试会话"""
       engine = create_async_engine(settings.TEST_DATABASE_URL)
       async with AsyncSession(engine) as session:
           yield session
           await session.rollback()
   ```

4. **编写第一个测试** (1 天)
   ```python
   # tests/unit/services/test_database_service.py
   import pytest
   from unittest.mock import Mock, AsyncMock
   from app.services.database_service import DatabaseService

   class TestDatabaseService:
       @pytest.fixture
       def mock_db(self):
           db = Mock()
           db.execute_query = AsyncMock()
           return db

       @pytest.fixture
       def service(self, mock_db):
           return DatabaseService(db=mock_db)

       async def test_get_stock_list_success(self, service, mock_db):
           # Arrange
           mock_db.execute_query.return_value = {
               'total': 100,
               'data': [{'code': '000001', 'name': '平安银行'}]
           }

           # Act
           result = await service.get_stock_list(limit=10)

           # Assert
           assert result['total'] == 100
           assert len(result['data']) == 1
   ```

5. **配置 pytest** (半天)
   ```ini
   # pytest.ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   asyncio_mode = auto

   # 覆盖率配置
   addopts =
       --cov=app
       --cov-report=html
       --cov-report=term-missing
       --cov-fail-under=30
       -v
   ```

**验收标准**:
- ✅ 测试框架可运行
- ✅ 至少 5 个单元测试通过
- ✅ 测试覆盖率报告可生成

---

### Week 3-4: 测试编写 + 异常处理统一

#### 任务 1.3: 核心服务测试 (P0)

**预计时间**: 1 周
**目标覆盖率**: 30%

**测试优先级**:

1. **DatabaseService** (高优先级)
   - `get_stock_list()`
   - `get_stock_daily_data()`
   - `insert_stock_data()`

2. **BacktestService** (高优先级)
   - `run_backtest()`
   - `calculate_metrics()`

3. **FeatureService** (中优先级)
   - `calculate_features()`
   - `get_feature_data()`

**测试模板**:
```python
# tests/unit/services/test_backtest_service.py
import pytest
from app.services.backtest_service import BacktestService

class TestBacktestService:
    @pytest.fixture
    def service(self):
        return BacktestService()

    async def test_run_backtest_success(self, service):
        # Arrange
        strategy_params = {
            'strategy_type': 'ma_cross',
            'short_window': 5,
            'long_window': 20
        }

        # Act
        result = await service.run_backtest(
            stock_codes=['000001'],
            start_date='2023-01-01',
            end_date='2023-12-31',
            strategy_params=strategy_params
        )

        # Assert
        assert 'total_return' in result
        assert 'sharpe_ratio' in result
        assert result['total_return'] is not None

    async def test_run_backtest_invalid_stock_code(self, service):
        # Act & Assert
        with pytest.raises(DataNotFoundError):
            await service.run_backtest(
                stock_codes=['999999'],  # 不存在的股票
                start_date='2023-01-01',
                end_date='2023-12-31'
            )
```

**验收标准**:
- ✅ DatabaseService: 10+ 测试
- ✅ BacktestService: 8+ 测试
- ✅ FeatureService: 6+ 测试
- ✅ 测试覆盖率达到 30%

---

#### 任务 1.4: 统一异常处理 (P0)

**预计时间**: 3 天
**负责人**: 后端开发

**子任务**:

1. **替换通用异常捕获** (2 天)

   **目标**: 将 134 处 `except Exception` 替换为具体异常

   **步骤**:
   ```bash
   # 1. 找出所有使用 except Exception 的文件
   grep -r "except Exception" app/ --include="*.py" > exception_audit.txt

   # 2. 逐个文件修改
   # 3. 运行测试确保没有破坏功能
   ```

   **修改示例**:
   ```python
   # ❌ 修改前
   try:
       stock_data = await fetch_stock_data(code)
   except Exception as e:
       logger.error(f"错误: {e}")
       raise

   # ✅ 修改后
   try:
       stock_data = await fetch_stock_data(code)
   except DataNotFoundError as e:
       logger.warning(f"股票数据不存在: {e}")
       raise ApiResponse.not_found(
           message=e.message,
           data=e.to_dict()
       )
   except ExternalAPIError as e:
       logger.error(f"API 调用失败: {e}")
       raise ApiResponse.error(
           message=e.message,
           code=503,
           data=e.to_dict()
       )
   except Exception as e:
       logger.exception(f"未预期的错误: {e}")
       raise ApiResponse.internal_error(
           message="系统内部错误"
       )
   ```

2. **添加全局异常处理器** (1 天)
   ```python
   # app/api/error_handler.py (增强版)
   from fastapi import Request, status
   from fastapi.responses import JSONResponse
   from app.core.exceptions import (
       BackendError,
       DataNotFoundError,
       ValidationError,
       DatabaseError,
       ExternalAPIError
   )
   from app.models.api_response import ApiResponse

   async def backend_error_handler(request: Request, exc: BackendError):
       """处理业务异常"""
       return JSONResponse(
           status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
           content=ApiResponse.error(
               message=exc.message,
               code=500,
               data=exc.to_dict()
           ).dict()
       )

   async def data_not_found_handler(request: Request, exc: DataNotFoundError):
       """处理数据不存在异常"""
       return JSONResponse(
           status_code=status.HTTP_404_NOT_FOUND,
           content=ApiResponse.not_found(
               message=exc.message,
               data=exc.to_dict()
           ).dict()
       )

   async def validation_error_handler(request: Request, exc: ValidationError):
       """处理验证异常"""
       return JSONResponse(
           status_code=status.HTTP_400_BAD_REQUEST,
           content=ApiResponse.bad_request(
               message=exc.message,
               data=exc.to_dict()
           ).dict()
       )

   # 在 main.py 中注册
   from app.api.error_handler import (
       backend_error_handler,
       data_not_found_handler,
       validation_error_handler
   )

   app.add_exception_handler(BackendError, backend_error_handler)
   app.add_exception_handler(DataNotFoundError, data_not_found_handler)
   app.add_exception_handler(ValidationError, validation_error_handler)
   ```

**验收标准**:
- ✅ 所有 `except Exception` 被精确异常替换
- ✅ 全局异常处理器已注册
- ✅ API 返回统一的错误格式

---

## Phase 2: 架构重构 (Week 5-8)

### Week 5-6: 数据访问层重构

#### 任务 2.1: SQLAlchemy ORM 模型定义 (P0)

**预计时间**: 1 周
**负责人**: 后端开发

**子任务**:

1. **定义基础模型** (2 天)
   ```python
   # app/models/db_models.py
   from datetime import datetime, date
   from sqlalchemy import Column, String, Float, Integer, Date, DateTime, Boolean
   from sqlalchemy.ext.asyncio import AsyncAttrs
   from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

   class Base(AsyncAttrs, DeclarativeBase):
       """异步 ORM 基类"""
       pass

   class StockBasic(Base):
       """股票基本信息"""
       __tablename__ = "stock_basic"

       code: Mapped[str] = mapped_column(String(10), primary_key=True)
       name: Mapped[str] = mapped_column(String(50))
       market: Mapped[str] = mapped_column(String(20))
       industry: Mapped[str] = mapped_column(String(50), nullable=True)
       area: Mapped[str] = mapped_column(String(50), nullable=True)
       list_date: Mapped[date] = mapped_column(Date, nullable=True)
       status: Mapped[str] = mapped_column(String(20), default="正常")
       created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
       updated_at: Mapped[datetime] = mapped_column(
           DateTime,
           default=datetime.utcnow,
           onupdate=datetime.utcnow
       )

   class StockDaily(Base):
       """股票日线数据"""
       __tablename__ = "stock_daily"

       code: Mapped[str] = mapped_column(String(10), primary_key=True)
       date: Mapped[date] = mapped_column(Date, primary_key=True)
       open: Mapped[float] = mapped_column(Float)
       high: Mapped[float] = mapped_column(Float)
       low: Mapped[float] = mapped_column(Float)
       close: Mapped[float] = mapped_column(Float)
       volume: Mapped[float] = mapped_column(Float)
       amount: Mapped[float] = mapped_column(Float, nullable=True)
   ```

2. **创建异步数据库引擎** (1 天)
   ```python
   # app/core/database.py
   from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
   from app.core.config import settings

   # 创建异步引擎
   engine = create_async_engine(
       settings.DATABASE_URL_ASYNC,
       echo=settings.ENVIRONMENT == "development",
       pool_size=20,
       max_overflow=40
   )

   # 创建会话工厂
   async_session_maker = async_sessionmaker(
       engine,
       class_=AsyncSession,
       expire_on_commit=False
   )

   async def get_db() -> AsyncGenerator[AsyncSession, None]:
       """依赖注入：获取数据库会话"""
       async with async_session_maker() as session:
           try:
               yield session
               await session.commit()
           except Exception:
               await session.rollback()
               raise
   ```

3. **更新配置** (半天)
   ```python
   # app/core/config.py
   @property
   def DATABASE_URL_ASYNC(self) -> str:
       """异步数据库连接 URL"""
       return (
           f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
           f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
       )
   ```

**验收标准**:
- ✅ 所有表的 ORM 模型已定义
- ✅ 异步引擎配置正确
- ✅ 依赖注入 `get_db()` 可用

---

#### 任务 2.2: 完善 Repository 层 (P1)

**预计时间**: 1 周
**负责人**: 后端开发

**目标**: 创建 10+ 个 Repository

**Repository 列表**:

1. **StockRepository** (必须)
   ```python
   # app/repositories/stock_repository.py
   from typing import List, Optional
   from sqlalchemy import select
   from sqlalchemy.ext.asyncio import AsyncSession
   from app.models.db_models import StockBasic
   from app.repositories.base_repository import BaseRepository

   class StockRepository(BaseRepository[StockBasic]):
       """股票数据仓库"""

       def __init__(self, session: AsyncSession):
           super().__init__(StockBasic, session)

       async def get_by_market(self, market: str) -> List[StockBasic]:
           """按市场查询"""
           result = await self.session.execute(
               select(StockBasic).where(StockBasic.market == market)
           )
           return result.scalars().all()

       async def search(self, keyword: str) -> List[StockBasic]:
           """搜索股票"""
           result = await self.session.execute(
               select(StockBasic).where(
                   (StockBasic.code.like(f"%{keyword}%")) |
                   (StockBasic.name.like(f"%{keyword}%"))
               )
           )
           return result.scalars().all()
   ```

2. **MarketDataRepository** (必须)
3. **FeatureRepository** (必须)
4. **StrategyRepository** (应该)
5. **MLModelRepository** (应该)

**验收标准**:
- ✅ 10+ Repository 已创建
- ✅ 所有 Repository 有单元测试
- ✅ Service 层已更新使用 Repository

---

### Week 7-8: Redis 缓存 + 依赖注入

#### 任务 2.3: 实现 Redis 缓存 (P1)

**预计时间**: 1 周
**负责人**: 后端开发

**子任务**:

1. **创建 CacheManager** (2 天)
   ```python
   # app/core/cache.py
   import json
   from typing import Any, Optional, Callable
   from redis import asyncio as aioredis
   from functools import wraps
   from app.core.config import settings

   class CacheManager:
       def __init__(self):
           self.redis = aioredis.from_url(
               f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
               encoding="utf-8",
               decode_responses=True
           )

       async def get(self, key: str) -> Optional[Any]:
           """获取缓存"""
           value = await self.redis.get(key)
           return json.loads(value) if value else None

       async def set(self, key: str, value: Any, ttl: int = 300):
           """设置缓存"""
           await self.redis.setex(
               key,
               ttl,
               json.dumps(value, default=str)
           )

       async def delete(self, key: str):
           """删除缓存"""
           await self.redis.delete(key)

       async def get_or_set(
           self,
           key: str,
           factory: Callable,
           ttl: int = 300
       ) -> Any:
           """获取或设置缓存"""
           cached = await self.get(key)
           if cached is not None:
               return cached

           value = await factory()
           await self.set(key, value, ttl)
           return value

       def cached(self, ttl: int = 300, key_prefix: str = ""):
           """缓存装饰器"""
           def decorator(func):
               @wraps(func)
               async def wrapper(*args, **kwargs):
                   # 生成缓存 key
                   key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"

                   # 尝试从缓存获取
                   cached = await self.get(key)
                   if cached is not None:
                       return cached

                   # 调用原函数
                   result = await func(*args, **kwargs)

                   # 写入缓存
                   await self.set(key, result, ttl)
                   return result
               return wrapper
           return decorator

   # 全局缓存实例
   cache = CacheManager()
   ```

2. **应用缓存到 Service** (2 天)
   ```python
   # app/services/stock_service.py
   from app.core.cache import cache

   class StockService:
       @cache.cached(ttl=300, key_prefix="stock_list")
       async def get_stock_list(self, market: Optional[str] = None):
           """获取股票列表（带缓存）"""
           return await self.stock_repo.get_by_market(market)
   ```

3. **缓存失效策略** (1 天)
   ```python
   # 数据更新时清除缓存
   async def update_stock_data(self, code: str, data: dict):
       # 更新数据
       await self.stock_repo.update(code, data)

       # 清除相关缓存
       await cache.delete(f"stock_list:*")
       await cache.delete(f"stock_detail:{code}")
   ```

**缓存场景**:

| 数据类型 | TTL | Key 格式 |
|---------|-----|----------|
| 股票列表 | 5 分钟 | `stock_list:{market}` |
| 股票详情 | 10 分钟 | `stock_detail:{code}` |
| 技术指标 | 1 小时 | `indicator:{code}:{date}` |
| 回测结果 | 24 小时 | `backtest:{hash}` |
| 市场日历 | 24 小时 | `market_calendar:{year}` |

**验收标准**:
- ✅ CacheManager 可用
- ✅ 至少 5 个 Service 使用缓存
- ✅ 缓存命中率 > 60%

---

#### 任务 2.4: 依赖注入容器 (P1)

**预计时间**: 1 周
**负责人**: 后端开发

**子任务**:

1. **安装依赖注入框架** (1 小时)
   ```bash
   pip install dependency-injector
   ```

2. **创建容器** (2 天)
   ```python
   # app/core/container.py
   from dependency_injector import containers, providers
   from app.core.database import async_session_maker
   from app.core.cache import CacheManager
   from app.repositories.stock_repository import StockRepository
   from app.services.stock_service import StockService

   class Container(containers.DeclarativeContainer):
       """依赖注入容器"""

       # 配置
       config = providers.Configuration()

       # 基础设施
       db_session = providers.Factory(async_session_maker)
       cache = providers.Singleton(CacheManager)

       # Repository 层
       stock_repository = providers.Factory(
           StockRepository,
           session=db_session.provided
       )

       # Service 层
       stock_service = providers.Factory(
           StockService,
           stock_repo=stock_repository,
           cache=cache
       )
   ```

3. **集成到 FastAPI** (2 天)
   ```python
   # app/main.py
   from dependency_injector.wiring import Provide, inject
   from app.core.container import Container

   # 创建容器
   container = Container()
   container.wire(modules=[
       "app.api.endpoints.stocks",
       "app.api.endpoints.backtest",
       # ... 其他模块
   ])

   # 在端点中使用
   # app/api/endpoints/stocks.py
   @router.get("/")
   @inject
   async def get_stocks(
       stock_service: StockService = Depends(Provide[Container.stock_service])
   ):
       return await stock_service.get_stock_list()
   ```

**验收标准**:
- ✅ 容器配置完成
- ✅ 所有端点使用 DI
- ✅ 测试可以注入 Mock

---

## Phase 3: 性能优化 (Week 9-12)

### Week 9-10: 异步驱动迁移

#### 任务 3.1: 迁移到 asyncpg (P0)

**预计时间**: 2 周
**负责人**: 后端开发

**子任务**:

1. **更新依赖** (1 小时)
   ```bash
   # requirements.txt
   # psycopg2-binary>=2.9.0  # ❌ 移除
   asyncpg>=0.29.0          # ✅ 新增
   ```

2. **迁移所有查询** (1.5 周)
   - 更新 DatabaseService
   - 更新所有 Repository
   - 移除 `asyncio.to_thread()`

3. **性能测试** (2 天)
   ```python
   # tests/performance/test_database_performance.py
   import pytest
   import time

   async def test_concurrent_queries_performance():
       """测试并发查询性能"""
       start = time.time()

       tasks = [
           stock_service.get_stock_list()
           for _ in range(100)
       ]
       await asyncio.gather(*tasks)

       elapsed = time.time() - start
       assert elapsed < 2.0  # 100 个并发查询 < 2 秒
   ```

**预期收益**:
- 并发能力提升 3-5 倍
- 响应时间减少 30-50%

**验收标准**:
- ✅ 所有查询使用 asyncpg
- ✅ 性能测试通过
- ✅ 无功能回归

---

### Week 11-12: 监控与优化

#### 任务 3.2: 添加监控系统 (P2)

**预计时间**: 1 周

**子任务**:

1. **Prometheus 指标导出** (3 天)
   ```python
   # app/middleware/metrics.py
   from prometheus_client import Counter, Histogram, generate_latest

   REQUEST_COUNT = Counter(
       'http_requests_total',
       'Total HTTP requests',
       ['method', 'endpoint', 'status']
   )

   REQUEST_DURATION = Histogram(
       'http_request_duration_seconds',
       'HTTP request duration',
       ['method', 'endpoint']
   )
   ```

2. **性能优化** (4 天)
   - 添加数据库索引
   - 优化慢查询
   - 代码性能分析

**验收标准**:
- ✅ Prometheus 指标可用
- ✅ API P95 响应时间 < 100ms
- ✅ 数据库查询优化完成

---

## 关键里程碑

### Milestone 1: 安全与测试就绪 (Week 4)

**目标**:
- ✅ 安全问题修复完成
- ✅ 测试覆盖率达到 30%
- ✅ 异常处理统一

**验收**:
- 安全审计通过
- CI 测试通过
- 代码质量评分 > 7.0

---

### Milestone 2: 架构重构完成 (Week 8)

**目标**:
- ✅ SQLAlchemy ORM 迁移完成
- ✅ Repository 层完善
- ✅ Redis 缓存实现
- ✅ 依赖注入完成

**验收**:
- 架构评分 > 8.5
- 代码耦合度降低 50%
- API 响应时间减少 30%

---

### Milestone 3: 生产就绪 (Week 12)

**目标**:
- ✅ 异步驱动迁移完成
- ✅ 测试覆盖率 > 60%
- ✅ 监控系统上线
- ✅ 性能目标达成

**验收**:
- 生产就绪度 9/10
- 性能测试通过
- 安全审计通过

---

## 资源分配

### 人力资源

| 角色 | 投入 | 职责 |
|------|------|------|
| 后端开发 | 100% | 代码重构、功能开发 |
| QA 工程师 | 50% | 测试编写、质量保证 |
| DevOps | 20% | CI/CD、监控配置 |

### 时间分配

```
总工时估算: 约 300 人时 (12 周 × 5 天 × 5 小时)

Phase 1 (安全与测试): 100 人时
Phase 2 (架构重构):   120 人时
Phase 3 (性能优化):   80 人时
```

---

## 风险管理

### 高风险项

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 异步驱动迁移失败 | 中 | 高 | 充分测试，保留回滚方案 |
| 性能优化效果不达标 | 中 | 中 | 提前性能基准测试 |
| 测试编写进度滞后 | 高 | 中 | 优先核心功能测试 |

---

## 成功指标

### 量化指标

| 指标 | 当前 | 目标 (Week 12) | 测量方式 |
|------|------|---------------|---------|
| 测试覆盖率 | 0% | 60%+ | pytest-cov |
| API P95 响应时间 | 200ms | <100ms | Locust 压测 |
| 并发支持 | 100 QPS | 500+ QPS | Locust 压测 |
| 代码质量评分 | 6.5/10 | 8.5/10 | SonarQube |
| 生产就绪度 | 6/10 | 9/10 | 人工评估 |

---

## 下一步行动

### 本周 (Week 1)

1. ✅ **任务 0.1 完成**: 审计 Core 功能清单 - **已完成 (2026-02-01)**
   - ✅ 生成了完整的审计报告
   - ✅ 识别了 1,797 行完全重复代码
   - ✅ 验证了架构修正的必要性

2. 🔴 **下一步**: 开始任务 0.2 - 创建 Core Adapters (预计 3 天)
   - 创建 `data_adapter.py`
   - 创建 `feature_adapter.py`
   - 创建 `backtest_adapter.py`
   - 创建 `model_adapter.py`

### 本周剩余时间 (Week 1)

- [ ] 开始 Adapter 开发
- [ ] 编写 Adapter 单元测试
- [ ] 准备 API 重写计划

### 本月 (Month 1)

1. ⏳ 完成 Phase 0 所有任务
2. ⏳ 删除所有冗余代码
3. ⏳ API 端点全部重写完成

---

## 📝 更新日志

### v2.2 (2026-02-01 23:30)
- ✅ **任务 0.2 完成**: 创建 Core Adapters
- 📄 交付物:
  - 4 个 Adapter 模块 (1,523 行代码)
  - 50 个测试用例 (覆盖率 90%+)
  - 完整文档和使用指南
- 🎯 关键成果:
  - DataAdapter: 11 个异步方法
  - FeatureAdapter: 12 个异步方法 (125+ 特征)
  - BacktestAdapter: 10 个异步方法 (20+ 指标)
  - ModelAdapter: 12 个异步方法 (6+ 模型)
- 📊 进度: Phase 0 完成 2/6 任务 (33.3%)

### v2.1 (2026-02-01 23:15)
- ✅ **任务 0.1 完成**: 审计 Core 功能清单
- 📄 交付物: [Core 功能审计报告](./core_功能审计报告.md)
- 🔍 关键发现:
  - Core 项目: 205 个文件, ~35,000 行代码
  - Backend Services: 66 个文件, 7,258 行代码
  - 完全重复代码: 1,797 行 (24.8%)
  - 总重复率: 41.0%
- 📊 进度: Phase 0 完成 1/6 任务 (16.7%)

### v2.0 (2026-02-01 22:40)
- 🔴 发现架构设计缺陷
- ❌ 取消了 SQLAlchemy ORM、Repository 层等任务
- 🎯 调整为架构修正路线图

---

**路线图版本**: v2.1
**最后更新**: 2026-02-01 23:15
**下次审查**: 每两周（双周五）
