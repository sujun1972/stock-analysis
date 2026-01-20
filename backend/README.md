# Stock Analysis Backend

A股AI量化交易系统 - 后端API服务

## 技术栈

- **框架**: FastAPI (高性能异步Web框架)
- **数据库**: PostgreSQL + TimescaleDB
- **ORM**: SQLAlchemy (可选)
- **数据处理**: Pandas, NumPy
- **机器学习**: LightGBM, scikit-learn
- **技术分析**: TA-Lib
- **数据源**: AkShare, Tushare

## 项目结构

```
backend/
├── app/
│   ├── api/              # API路由
│   │   ├── endpoints/    # 端点实现
│   │   │   ├── stocks.py    # 股票列表
│   │   │   ├── data.py      # 数据下载和查询
│   │   │   ├── features.py  # 特征工程
│   │   │   ├── models.py    # 模型训练和预测
│   │   │   └── backtest.py  # 回测
│   │   └── __init__.py
│   ├── core/             # 核心配置
│   │   ├── config.py     # 应用配置
│   │   └── __init__.py
│   ├── models/           # 数据库模型（暂未使用）
│   ├── schemas/          # Pydantic模型
│   ├── services/         # 业务逻辑层
│   │   ├── data_service.py      # 数据服务
│   │   ├── database_service.py  # 数据库服务
│   │   └── feature_service.py   # 特征服务
│   ├── main.py           # 应用入口
│   └── __init__.py
├── src/                  # Docker挂载目录（core/src -> /app/src）
├── Dockerfile            # Docker镜像构建文件
├── requirements.txt      # Python依赖
├── .dockerignore
└── README.md
```

**注意**: `src/` 目录是通过 Docker Compose 挂载的 `../core/src`，包含核心股票分析代码。

## API端点

### 股票列表 (`/api/stocks`)

- `GET /api/stocks/list` - 获取股票列表
- `GET /api/stocks/{code}` - 获取单只股票信息
- `POST /api/stocks/update` - 更新股票列表

### 数据管理 (`/api/data`)

- `GET /api/data/daily/{code}` - 获取日线数据
- `POST /api/data/download` - 下载股票数据
- `GET /api/data/download/status/{task_id}` - 查询下载状态

### 特征工程 (`/api/features`)

- `GET /api/features/{code}` - 获取特征数据
- `POST /api/features/calculate/{code}` - 计算特征

### 模型管理 (`/api/models`)

- `POST /api/models/train` - 训练模型
- `GET /api/models/predict/{code}` - 获取预测结果
- `GET /api/models/evaluation/{model_name}` - 获取模型评估

### 回测 (`/api/backtest`)

- `POST /api/backtest/run` - 运行回测
- `GET /api/backtest/result/{task_id}` - 获取回测结果
- `GET /api/backtest/history` - 获取历史回测

## 快速开始

### 使用Docker Compose（推荐）

```bash
# 1. 进入项目根目录
cd /Volumes/MacDriver/stock-analysis

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 访问API文档
open http://localhost:8000/api/docs
```

### 本地开发

```bash
# 1. 创建虚拟环境
cd backend
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
export DATABASE_HOST=localhost
export DATABASE_PORT=5432
export DATABASE_NAME=stock_analysis
export DATABASE_USER=stock_user
export DATABASE_PASSWORD=stock_password_123

# 4. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 5. 访问API文档
open http://localhost:8000/api/docs
```

## API文档

启动服务后访问：

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

## 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| ENVIRONMENT | 环境 | development |
| DATABASE_HOST | 数据库主机 | timescaledb |
| DATABASE_PORT | 数据库端口 | 5432 |
| DATABASE_NAME | 数据库名称 | stock_analysis |
| DATABASE_USER | 数据库用户 | stock_user |
| DATABASE_PASSWORD | 数据库密码 | stock_password_123 |
| TUSHARE_TOKEN | Tushare Token | - |

## 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 预期输出
{
  "status": "healthy",
  "environment": "development"
}
```

## 数据库连接

Backend自动连接到TimescaleDB数据库：

```python
from app.core.config import settings

# 数据库URL
print(settings.DATABASE_URL)
# postgresql://stock_user:stock_password_123@timescaledb:5432/stock_analysis
```

## 开发指南

### 添加新API端点

1. 在 `app/api/endpoints/` 创建新文件或编辑现有文件
2. 定义路由和处理函数
3. 在 `app/api/__init__.py` 注册路由

示例：

```python
# app/api/endpoints/my_feature.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/hello")
async def hello():
    return {"message": "Hello World"}
```

```python
# app/api/__init__.py
from .endpoints import my_feature

router.include_router(
    my_feature.router,
    prefix="/my-feature",
    tags=["my-feature"]
)
```

### 添加业务逻辑

将业务逻辑放在 `app/services/` 目录：

```python
# app/services/stock_service.py
def get_stock_data(code: str):
    # 业务逻辑
    pass
```

### 添加数据模型

Pydantic模型放在 `app/schemas/`:

```python
# app/schemas/stock.py
from pydantic import BaseModel

class StockInfo(BaseModel):
    code: str
    name: str
    market: str
```

数据库模型放在 `app/models/`:

```python
# app/models/stock.py
from sqlalchemy import Column, String
from app.core.database import Base

class Stock(Base):
    __tablename__ = "stocks"
    code = Column(String, primary_key=True)
    name = Column(String)
```

## 与核心代码集成

Backend 通过 Docker 挂载访问核心分析代码（`../core/src` -> `/app/src`）：

```python
# 在容器内可以直接导入核心代码
from src.database.db_manager import DatabaseManager
from src.features.technical_indicators import TechnicalIndicators
from src.features.alpha_factors import AlphaFactors
from src.data_fetcher import DataFetcher
```

**Docker Compose 挂载配置**（在项目根目录的 `docker-compose.yml`）：
```yaml
volumes:
  - ./backend:/app          # Backend 代码
  - ./core/src:/app/src     # 核心分析代码（挂载为 src/）
  - ./data:/data            # 数据目录
```

这样的设计允许：
- Backend 专注于提供 API 服务
- 核心代码可以被 Backend 和本地脚本共享
- 保持代码的单一来源（DRY原则）

## 日志

使用loguru进行日志记录：

```python
from loguru import logger

logger.info("信息日志")
logger.error("错误日志")
```

## 测试

```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest tests/
```

## 部署

### 生产环境

1. 修改 `docker-compose.yml` 中的环境变量
2. 设置 `ENVIRONMENT=production`
3. 使用强密码
4. 配置反向代理（Nginx）
5. 启用HTTPS

### 性能优化

- 使用Gunicorn或uWSGI作为WSGI服务器
- 启用Redis缓存
- 数据库连接池优化
- 静态文件CDN

## 未来计划

- [ ] 集成Redis缓存
- [ ] 后台任务队列（Celery）
- [ ] WebSocket实时推送
- [ ] 用户认证和权限管理
- [ ] API限流
- [ ] 数据库ORM层完善
- [ ] 单元测试和集成测试
- [ ] CI/CD流水线

## 相关文档

- [项目根目录README](../README.md)
- [快速开始指南](../QUICKSTART.md)
- [数据库使用指南](../docs/DATABASE_USAGE.md)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [TimescaleDB文档](https://docs.timescale.com/)

## 许可

MIT License
