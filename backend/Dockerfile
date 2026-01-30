# Backend Docker 镜像
# 注意: core模块通过docker-compose挂载访问，不在此打包

FROM python:3.11-slim

WORKDIR /app

# 设置环境变量
# PYTHONPATH: 使core/src目录下的模块可直接导入
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/core/src:/app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY backend/requirements.txt .
RUN sed -i '/TA-Lib/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# 复制backend应用代码（core通过挂载访问）
COPY backend/app ./app
COPY backend/*.py ./

# 创建必要的目录
RUN mkdir -p /data /app/logs

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
