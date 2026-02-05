"""
Stock Analysis Backend API
主应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import router as api_router
from app.api.exception_handlers import register_exception_handlers
from app.core.config import settings

# 创建FastAPI应用
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A股AI量化交易系统后端API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """健康检查"""
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
