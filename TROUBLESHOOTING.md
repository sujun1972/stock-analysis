# 🔧 故障排除指南

本文档提供项目常见问题的解决方案，涵盖Docker、Backend API、本地开发等场景。

---

## 🐳 Docker 相关问题

### 1. Docker服务启动失败

**症状：**
```bash
docker-compose up -d
# ERROR: Cannot start service backend: ...
```

**诊断：**
```bash
# 检查Docker是否运行
docker ps

# 查看服务状态
docker-compose ps

# 查看详细日志
docker-compose logs backend
docker-compose logs timescaledb
```

**解决方案：**

**方案A - 端口冲突：**
```bash
# 检查8000端口是否被占用
lsof -i :8000
# 或
netstat -an | grep 8000

# 修改docker-compose.yml中的端口映射
# ports:
#   - "8001:8000"  # 使用8001端口
```

**方案B - 数据卷权限：**
```bash
# 删除并重新创建数据卷
docker-compose down -v
docker-compose up -d
```

**方案C - 完全重启：**
```bash
# 停止所有服务
docker-compose down

# 清理镜像（可选）
docker-compose rm -f

# 重新构建和启动
docker-compose up -d --build
```

---

### 2. Backend API 无法访问

**症状：**
```bash
curl http://localhost:8000/health
# curl: (7) Failed to connect to localhost port 8000: Connection refused
```

**解决方案：**

```bash
# 1. 检查容器是否运行
docker-compose ps

# 2. 查看backend日志
docker-compose logs -f backend

# 3. 检查容器内部服务
docker-compose exec backend curl http://localhost:8000/health

# 4. 重启backend服务
docker-compose restart backend

# 5. 如果还是失败，查看完整启动日志
docker-compose up backend
```

**常见错误：**
- 依赖安装失败 → 检查 `backend/requirements.txt`
- 数据库连接失败 → 确保 TimescaleDB 已启动
- 环境变量缺失 → 检查 `.env` 文件

---

### 3. 数据库连接失败

**症状：**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案：**

```bash
# 1. 检查数据库容器状态
docker-compose ps timescaledb

# 2. 查看数据库日志
docker-compose logs timescaledb

# 3. 测试数据库连接
docker-compose exec timescaledb psql -U stock_user -d stock_analysis

# 4. 检查数据库健康状态
docker-compose exec timescaledb pg_isready -U stock_user

# 5. 重启数据库
docker-compose restart timescaledb

# 6. 如果数据损坏，重新初始化
docker-compose down -v  # 警告：会删除所有数据！
docker-compose up -d
```

---

### 4. Docker挂载目录问题

**症状：**
```
ModuleNotFoundError: No module named 'src'
```

**原因：**
`core/src` 未正确挂载到容器内的 `/app/src`

**解决方案：**

```bash
# 1. 检查docker-compose.yml挂载配置
cat docker-compose.yml | grep -A 5 "volumes:"

# 应该包含：
#   - ./core/src:/app/src

# 2. 验证挂载
docker-compose exec backend ls -la /app/src

# 3. 重新启动服务
docker-compose down
docker-compose up -d
```

---

## 💻 本地开发问题

### 5. 模块导入失败

**症状：**
```python
ModuleNotFoundError: No module named 'core'
# 或
ModuleNotFoundError: No module named 'src'
```

**原因与解决方案：**

**错误路径（旧）：**
```python
from src.data_fetcher import DataFetcher  # ❌ 错误
```

**正确路径（新）：**
```python
from core.src.data_fetcher import DataFetcher  # ✅ 正确
```

**或者在项目根目录运行：**
```bash
# 方法1：使用-m模块运行
python -m core.src.main

# 方法2：直接运行
python core/src/main.py
```

---

### 6. 虚拟环境激活失败

**症状：**
- 命令找不到
- Python版本不对
- 模块导入失败

**解决方案：**

```bash
# 1. 确保在项目根目录
cd /path/to/stock-analysis
pwd  # 应显示 .../stock-analysis

# 2. 检查虚拟环境是否存在
ls stock_env/bin/activate

# 3. 激活虚拟环境
source stock_env/bin/activate  # macOS/Linux
# 或
stock_env\Scripts\activate  # Windows

# 4. 验证（应显示虚拟环境路径）
which python
# 输出应该是: .../stock-analysis/stock_env/bin/python

python --version
# 输出应该是: Python 3.9+ 或 3.10+
```

**如果虚拟环境不存在，重新创建：**
```bash
python3 -m venv stock_env
source stock_env/bin/activate
pip install -r requirements.txt
```

---

### 7. 依赖包未安装

**症状：**
```
ModuleNotFoundError: No module named 'lightgbm'
ModuleNotFoundError: No module named 'akshare'
ModuleNotFoundError: No module named 'fastapi'
```

**解决方案：**
```bash
# 1. 确保虚拟环境已激活
which python  # 应显示 stock_env/bin/python

# 2. 安装所有依赖
pip install -r requirements.txt

# 3. 验证安装
pip list | grep lightgbm
pip list | grep akshare
pip list | grep fastapi

# 4. 如果特定包安装失败，单独安装
pip install lightgbm
pip install akshare
```

#### 4. TA-Lib 安装失败

**症状：**
```
ERROR: Failed building wheel for TA-Lib
```

**解决方案：**

**macOS:**
```bash
# 先安装系统级依赖
brew install ta-lib

# 然后安装Python包
pip install TA-Lib
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ta-lib
pip install TA-Lib
```

**Windows:**
1. 下载预编译包：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
2. 安装： `pip install TA_Lib‑0.4.28‑cp312‑cp312‑win_amd64.whl`

---

### 8. 数据下载超时/限流

**症状：**
- 请求超时
- 连接被拒绝
- 数据为空
- `HTTPError: 429 Too Many Requests`

**解决方案：**

**方案A - 增加延迟：**
```bash
# 增加请求间隔（避免被限流）
python core/scripts/download_data.py --years 5 --delay 2.0

# 或者使用数据库下载脚本（更稳定）
python core/scripts/download_data_to_db.py --years 5 --delay 1.5
```

**方案B - 减少下载量：**
```bash
# 先下载少量股票测试
python core/scripts/download_data.py --years 1 --max-stocks 10
```

**方案C - 使用AkShare（推荐）：**
```bash
# AkShare免费无限制
# 编辑.env文件
echo "DATA_SOURCE=akshare" >> .env

# 运行测试
python core/scripts/test_akshare.py
```

---

### 9. 测试脚本失败

**症状：**
```
AssertionError: ...
ValueError: ...
FileNotFoundError: ...
```

**解决方案：**

```bash
# 1. 确保虚拟环境已激活
source stock_env/bin/activate

# 2. 重新安装依赖
pip install --upgrade -r requirements.txt

# 3. 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 4. 重新运行测试（注意路径）
python core/tests/test_phase1_data_pipeline.py
python core/tests/test_phase2_features.py
python core/tests/test_phase3_models.py
python core/tests/test_phase4_backtest.py
```

**如果特定测试失败：**
```bash
# 查看详细错误信息
python core/tests/test_phase1_data_pipeline.py -v

# 或使用pytest（如已安装）
pytest core/tests/ -v
```

#### 7. 权限问题

**症状：**
```
Permission denied: 'data/raw/daily/000001.csv'
```

**解决方案：**
```bash
# 检查并修复权限
chmod -R 755 data/

# 或重新创建数据目录
rm -rf data/
mkdir -p data/{raw,features,models}
```

#### 8. 内存不足

**症状：**
```
MemoryError
Killed (信号 9)
```

**解决方案：**
```python
# 分批处理数据
# 在脚本中添加：
import gc

for stock in stocks:
    # 处理单只股票
    process_stock(stock)

    # 释放内存
    gc.collect()
```

#### 9. Python版本不兼容

**症状：**
```
SyntaxError: invalid syntax
```

**解决方案：**
```bash
# 检查Python版本（需要3.8+）
python --version

# 如果版本过低，重新创建虚拟环境
python3.10 -m venv stock_env
source stock_env/bin/activate
pip install -r requirements.txt
```

---

## 🔍 快速诊断命令

### Docker环境检查

```bash
# 1. 检查Docker服务状态
docker --version
docker-compose --version
docker ps

# 2. 检查项目服务状态
docker-compose ps

# 3. 测试Backend API
curl http://localhost:8000/health
curl http://localhost:8000/api/docs

# 4. 测试数据库连接
docker-compose exec timescaledb psql -U stock_user -d stock_analysis -c "SELECT version();"

# 5. 查看实时日志
docker-compose logs -f --tail=50 backend
```

### 本地环境检查

```bash
# 1. 检查虚拟环境
which python
python --version
# 应显示: Python 3.9+ 或 3.10+

# 2. 检查关键依赖
python -c "import lightgbm; print(f'LightGBM: {lightgbm.__version__}')"
python -c "import akshare; print(f'AkShare: {akshare.__version__}')"
python -c "import talib; print(f'TA-Lib: {talib.__version__}')"
python -c "import fastapi; print(f'FastAPI: {fastapi.__version__}')"

# 3. 测试核心模块导入（注意路径）
python -c "from core.src.data_fetcher import DataFetcher; print('✅ DataFetcher')"
python -c "from core.src.features.technical_indicators import TechnicalIndicators; print('✅ TechnicalIndicators')"
python -c "from core.src.models.lightgbm_model import LightGBMStockModel; print('✅ LightGBMStockModel')"
python -c "from core.src.backtest.backtest_engine import BacktestEngine; print('✅ BacktestEngine')"
```

### 检查项目结构

```bash
# 检查目录结构（macOS/Linux）
tree -L 2 -I 'stock_env|__pycache__|*.pyc'

# 或者使用find
find . -maxdepth 2 -type d | grep -v "stock_env\|__pycache__\|\.git"

# 检查关键目录
ls -la backend/
ls -la core/src/
ls -la data/
ls -la docs/
```

### 检查配置文件

```bash
# 1. 检查.env文件
cat .env
# 或
grep -v "^#" .env | grep -v "^$"

# 2. 检查docker-compose配置
cat docker-compose.yml | grep -A 5 "environment:"

# 3. 验证环境变量
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(f'DATA_SOURCE: {os.getenv(\"DATA_SOURCE\")}')"
```

---

## 获取帮助

### 详细日志

运行命令时添加 `-v` 或 `--verbose` 标志（如果支持）：

```bash
python scripts/download_data.py --years 1 --max-stocks 3 --verbose
```

### 查看完整错误堆栈

```bash
python your_script.py 2>&1 | tee error.log
```

### 报告问题

提交Issue时请包含：
1. 错误信息（完整的堆栈跟踪）
2. Python版本：`python --version`
3. 系统信息：`uname -a`
4. 依赖版本：`pip list`
5. 复现步骤

---

## 🧹 清理与重置

### Docker环境重置

```bash
# 警告：这会删除所有Docker容器、卷和数据！

# 1. 停止并删除所有容器
docker-compose down

# 2. 删除所有数据卷（包括数据库数据）
docker-compose down -v

# 3. 清理Docker镜像（可选）
docker system prune -a

# 4. 重新构建和启动
docker-compose up -d --build

# 5. 验证服务
docker-compose ps
curl http://localhost:8000/health
```

### 本地环境重置

```bash
# 警告：这会删除虚拟环境和所有数据！

# 1. 退出虚拟环境
deactivate

# 2. 删除虚拟环境
rm -rf stock_env/

# 3. 删除数据（可选，谨慎！）
rm -rf data/timescaledb/
rm -rf data/models/
rm -rf data/results/

# 4. 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 5. 重新创建虚拟环境
python3 -m venv stock_env
source stock_env/bin/activate

# 6. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 7. 验证安装
python core/scripts/test_akshare.py
```

### 部分清理（推荐）

```bash
# 只清理缓存，不删除数据

# 1. 清理Python缓存
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# 2. 重启Docker服务
docker-compose restart

# 3. 重新安装Python依赖
source stock_env/bin/activate
pip install --upgrade -r requirements.txt
```

---

## ✅ 系统状态检查清单

### Docker部署检查清单

- [ ] ✅ Docker Desktop已运行
- [ ] ✅ docker-compose.yml 配置正确
- [ ] ✅ .env 文件已创建并配置
- [ ] ✅ Backend容器运行中 (`docker-compose ps`)
- [ ] ✅ TimescaleDB容器运行中
- [ ] ✅ Backend API可访问 (`curl http://localhost:8000/health`)
- [ ] ✅ API文档可访问 (`http://localhost:8000/api/docs`)
- [ ] ✅ 数据库连接正常

### 本地开发检查清单

- [ ] ✅ 虚拟环境已激活 (`which python` 显示 stock_env 路径)
- [ ] ✅ Python版本 >= 3.9 (`python --version`)
- [ ] ✅ 所有依赖已安装 (`pip list | grep -E "lightgbm|akshare|fastapi"`)
- [ ] ✅ TA-Lib已安装 (`python -c "import talib"`)
- [ ] ✅ 核心模块可导入（运行"本地环境检查"命令）
- [ ] ✅ 测试脚本运行正常 (`python core/tests/test_phase1_data_pipeline.py`)
- [ ] ✅ 数据目录存在且可写 (`ls -la data/`)

### 项目结构检查清单

- [ ] ✅ `backend/` 目录存在
- [ ] ✅ `core/src/` 目录存在
- [ ] ✅ `data/` 目录存在
- [ ] ✅ `docs/` 目录存在
- [ ] ✅ `docker-compose.yml` 存在
- [ ] ✅ `requirements.txt` 存在
- [ ] ✅ `.env` 文件已创建

**全部打勾后，系统即可正常使用！** ✅

---

## 📚 相关文档

- [README.md](README.md) - 项目主文档
- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [docs/DATABASE_USAGE.md](docs/DATABASE_USAGE.md) - 数据库使用
- [backend/README.md](backend/README.md) - Backend API文档
- [core/README.md](core/README.md) - 核心代码文档

---

**最后更新：2026-01-20**
