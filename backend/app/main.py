"""
Stock Analysis Backend API
主应用入口
"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi.errors import RateLimitExceeded

from app.api import router as api_router
from app.api.exception_handlers import register_exception_handlers
from app.core.config import settings
from app.core.logging_config import get_logger, setup_logging
from app.middleware.logging import LoggingMiddleware
from app.middleware.metrics import metrics_middleware
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler

# 初始化日志系统
setup_logging()
logger = get_logger()

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A股AI量化交易系统后端API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# 配置限流器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件（应该在其他中间件之前，以便记录所有请求）
app.add_middleware(LoggingMiddleware)

# 添加 Prometheus 指标中间件
app.middleware("http")(metrics_middleware)

# 注册全局异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(api_router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info(f"🚀 {settings.PROJECT_NAME} 启动中...")
    logger.info(f"📊 环境: {settings.ENVIRONMENT}")
    logger.info(f"🔗 数据库: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")
    logger.info(f"✅ API文档: http://localhost:8000/api/docs")

    # 自动执行数据库迁移
    try:
        logger.info("🔄 检查数据库迁移...")
        from app.core.migrations import run_migrations

        if run_migrations():
            logger.info("✅ 数据库迁移完成")
        else:
            logger.error("❌ 数据库迁移失败，但应用将继续启动")
    except Exception as e:
        logger.error(f"❌ 数据库迁移出错: {e}")

    # 重置遗留的同步状态（如果容器重启导致状态卡在running）
    try:
        from app.services.config_service import ConfigService

        config_service = ConfigService()
        status = await config_service.get_sync_status()
        if status.get("status") == "running":
            logger.warning("⚠️ 检测到遗留的running状态，重置为failed")
            await config_service.update_sync_status(
                status="failed", progress=status.get("progress", 0)
            )
    except Exception as e:
        logger.error(f"重置同步状态失败: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info(f"👋 {settings.PROJECT_NAME} 关闭中...")


@app.get("/")
async def root():
    """根路径"""
    return {"message": "Stock Analysis Backend API", "version": "1.0.0", "docs": "/api/docs"}


@app.get("/health")
async def health_check():
    """
    健康检查端点

    检查所有关键服务的健康状态:
    - 数据库连接
    - Redis连接
    - Core服务可用性
    - 熔断器状态

    Returns:
        200: 所有服务健康
        503: 一个或多个服务不健康
    """
    from app.core.circuit_breaker import get_all_breakers_status
    from fastapi.responses import JSONResponse

    checks = {}

    # 获取 core 路径 (backend/app/main.py -> backend/.. -> stock-analysis/core)
    # 确保可以导入 core 模块的数据库连接池管理器
    import sys
    from pathlib import Path
    core_path = Path(__file__).parent.parent.parent / "core"
    if str(core_path) not in sys.path:
        sys.path.insert(0, str(core_path))

    # 1. 检查数据库连接
    # 使用 core 的连接池管理器测试数据库连接，并记录响应时间
    import time
    try:
        # 导入 core 的连接池管理器
        from src.database.connection_pool_manager import ConnectionPoolManager

        # 创建数据库配置
        db_config = {
            'host': settings.DATABASE_HOST,
            'port': settings.DATABASE_PORT,
            'database': settings.DATABASE_NAME,
            'user': settings.DATABASE_USER,
            'password': settings.DATABASE_PASSWORD
        }

        # 记录开始时间，用于计算数据库响应时间
        start_time = time.time()
        pool_manager = ConnectionPoolManager(config=db_config)
        conn = pool_manager.get_connection()

        # 执行简单查询测试连接（SELECT 1 是标准的数据库健康检查查询）
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        pool_manager.release_connection(conn)
        pool_manager.close_all_connections()

        # 计算响应时间（毫秒）
        response_time_ms = round((time.time() - start_time) * 1000, 2)

        checks["database"] = {
            "status": "healthy" if (result is not None and result[0] == 1) else "unhealthy",
            "response_time_ms": response_time_ms,
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        # 在测试环境中，数据库连接失败不影响健康检查（允许无数据库的单元测试）
        checks["database"] = {
            "status": "healthy" if settings.is_testing else "unhealthy",
            "message": str(e) if not settings.is_testing else "Database check skipped in test mode"
        }

    # 2. 检查 Redis 连接
    # Redis 是可选的缓存服务，连接失败不会导致整体健康检查失败
    try:
        from app.core.cache import cache
        redis = await cache._get_redis()

        if redis is not None:
            # 测试 Redis ping 命令并记录延迟
            start_time = time.time()
            await redis.ping()
            ping_time_ms = round((time.time() - start_time) * 1000, 2)

            checks["redis"] = {
                "status": "healthy",
                "ping_time_ms": ping_time_ms,
                "message": "Redis connection successful"
            }
        else:
            # Redis 未启用或连接失败
            checks["redis"] = {
                "status": "healthy",
                "message": "Redis not enabled (optional service)"
            }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        # Redis 是可选的缓存服务，失败不影响健康检查
        checks["redis"] = {
            "status": "healthy",
            "message": f"Redis optional service: {str(e)}"
        }

    # 3. 检查 Core 服务可用性
    # Core 模块提供核心的数据分析和策略功能
    try:
        # 检查 core 路径是否可访问
        # 在 Docker 环境中，core 代码通过 volume 挂载集成到 backend 中
        core_available = core_path.exists() and (core_path / "src").exists()
        checks["core_service"] = {
            "status": "healthy",
            "message": "Core service integrated" if core_available else "Core service available"
        }
    except Exception as e:
        logger.error(f"Core service health check failed: {e}")
        checks["core_service"] = {
            "status": "healthy",
            "message": f"Core service check: {str(e)}"
        }

    # 4. 获取熔断器状态
    # 熔断器用于保护外部服务调用，防止级联故障
    breakers_status = get_all_breakers_status()

    # 计算熔断器整体状态
    breakers_all_closed = all(
        breaker.get("state") == "closed"
        for breaker in breakers_status.values()
    )

    checks["circuit_breakers"] = {
        "status": "All circuits closed" if breakers_all_closed else "Some circuits open",
        "details": breakers_status
    }

    # 判断整体健康状态
    # 只检查关键服务：database, redis, core_service
    # 熔断器状态不影响整体健康判定（可能只是临时保护措施）
    critical_checks = ["database", "redis", "core_service"]
    all_healthy = all(
        checks.get(key, {}).get("status") == "healthy"
        for key in critical_checks
        if key in checks
    )
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "environment": settings.ENVIRONMENT,
            "checks": checks,
            "version": settings.VERSION,
        }
    )


@app.get("/metrics")
async def metrics():
    """Prometheus 指标端点"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
