# 安装指南

**Installation Guide for Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 📋 系统要求

### 硬件要求

**最低配置**:
- CPU: 双核处理器
- 内存: 8GB RAM
- 硬盘: 10GB可用空间

**推荐配置**:
- CPU: 四核及以上（支持多进程回测）
- 内存: 16GB+ RAM（处理大规模数据）
- 硬盘: 50GB+ SSD（存储历史数据）
- GPU: NVIDIA GPU with CUDA 11.0+（深度学习加速，可选）

### 软件要求

**必需软件**:
- Python 3.9+ (推荐 Python 3.10)
- pip 21.0+
- Git 2.30+

**可选软件**:
- Docker 20.10+ (容器化部署)
- PostgreSQL 14+ (TimescaleDB扩展)
- Redis 6.0+ (缓存，可选)

---

## 🚀 快速安装

### 方法一：标准安装（推荐）

#### 1. 克隆项目

```bash
# 克隆仓库
git clone https://github.com/your-org/stock-analysis.git
cd stock-analysis/core

# 检查Python版本
python --version  # 应显示 Python 3.9+
```

#### 2. 创建虚拟环境

**macOS/Linux**:
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 验证激活成功
which python  # 应显示虚拟环境路径
```

**Windows**:
```cmd
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate

# 验证激活成功
where python  # 应显示虚拟环境路径
```

#### 3. 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装核心依赖
pip install -r requirements.txt

# 安装开发依赖（可选）
pip install -r requirements-dev.txt

# 验证安装
pip list | grep pandas  # 应显示pandas版本
```

#### 4. 配置初始化

```bash
# 运行初始化命令
stock-cli init

# 这将创建以下文件：
# - config/default_config.yaml
# - logs/
# - data/
# - models/
```

#### 5. 验证安装

```bash
# 检查CLI工具
stock-cli --version

# 运行简单测试
python -c "from src.features import AlphaFactors; print('✅ 安装成功！')"

# 运行测试套件（可选）
pytest tests/unit/test_installation.py -v
```

---

### 方法二：Docker安装

#### 1. 安装Docker

**macOS**:
```bash
# 使用Homebrew
brew install --cask docker

# 启动Docker Desktop
open /Applications/Docker.app
```

**Linux (Ubuntu/Debian)**:
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 启动Docker服务
sudo systemctl start docker
sudo systemctl enable docker

# 添加用户到docker组（避免sudo）
sudo usermod -aG docker $USER
```

**Windows**:
- 下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

#### 2. 使用Docker Compose

```bash
# 克隆项目
git clone https://github.com/your-org/stock-analysis.git
cd stock-analysis/core

# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 预期输出：
# NAME                COMMAND             STATUS
# stock-core          python app.py       Up
# timescaledb         postgres            Up
# redis               redis-server        Up
```

#### 3. 进入容器

```bash
# 进入core容器
docker-compose exec stock-core bash

# 运行CLI命令
stock-cli --version

# 运行Python脚本
python scripts/demo.py
```

#### 4. 停止服务

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（慎用）
docker-compose down -v
```

---

## 🔧 依赖说明

### 核心依赖

**数据处理**:
```
pandas>=2.0.0         # 数据分析
numpy>=1.24.0         # 数值计算
polars>=0.18.0        # 高性能数据处理（可选）
```

**机器学习**:
```
lightgbm>=4.0.0       # 梯度提升模型（推荐）
pytorch>=2.0.0        # 深度学习框架
scikit-learn>=1.3.0   # 经典机器学习
```

**金融数据**:
```
akshare>=1.12.0       # A股数据接口（免费）
tushare>=1.3.0        # Tushare数据接口（需Token）
ta-lib>=0.4.28        # 技术分析库
```

**数据库**:
```
psycopg2-binary>=2.9.0     # PostgreSQL驱动
sqlalchemy>=2.0.0          # ORM框架
redis>=4.5.0               # Redis客户端
```

**工具库**:
```
pydantic>=2.0.0       # 数据验证
loguru>=0.7.0         # 日志系统
click>=8.1.0          # CLI框架
rich>=13.0.0          # 终端美化
```

### 开发依赖

```
pytest>=7.4.0              # 测试框架
pytest-cov>=4.1.0          # 覆盖率测试
black>=23.7.0              # 代码格式化
isort>=5.12.0              # 导入排序
pylint>=2.17.0             # 代码检查
mypy>=1.5.0                # 类型检查
pre-commit>=3.3.0          # Git钩子
```

---

## 🗄️ 数据库安装

### TimescaleDB安装

#### macOS

```bash
# 使用Homebrew
brew install timescaledb

# 初始化数据库
timescaledb-tune

# 启动PostgreSQL
brew services start postgresql
```

#### Linux (Ubuntu/Debian)

```bash
# 添加TimescaleDB仓库
sudo sh -c "echo 'deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main' > /etc/apt/sources.list.d/timescaledb.list"

wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -

# 安装TimescaleDB
sudo apt-get update
sudo apt-get install timescaledb-2-postgresql-14

# 配置数据库
sudo timescaledb-tune

# 重启PostgreSQL
sudo systemctl restart postgresql
```

#### Windows

1. 下载 [TimescaleDB Windows安装包](https://docs.timescale.com/install/latest/self-hosted/installation-windows/)
2. 运行安装程序并按照向导完成安装
3. 打开PostgreSQL配置文件 `postgresql.conf`，添加：
   ```
   shared_preload_libraries = 'timescaledb'
   ```
4. 重启PostgreSQL服务

#### Docker（推荐）

```bash
# 使用Docker运行TimescaleDB
docker run -d \
  --name timescaledb \
  -p 5432:5432 \
  -e POSTGRES_PASSWORD=yourpassword \
  timescale/timescaledb:latest-pg14

# 验证安装
docker exec -it timescaledb psql -U postgres -c "SELECT default_version, comment FROM pg_available_extensions WHERE name = 'timescaledb';"
```

### 数据库初始化

```bash
# 创建数据库
createdb stock_analysis

# 连接数据库
psql stock_analysis

# 启用TimescaleDB扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

# 退出
\q

# 运行初始化脚本
stock-cli db init

# 验证表结构
stock-cli db status
```

---

## 🐍 Python环境配置

### 使用pyenv管理Python版本

#### 安装pyenv

**macOS**:
```bash
# 使用Homebrew
brew install pyenv

# 添加到Shell配置
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# 重新加载配置
source ~/.zshrc
```

**Linux**:
```bash
# 安装依赖
sudo apt-get install -y make build-essential libssl-dev zlib1g-dev \
  libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
  libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

# 安装pyenv
curl https://pyenv.run | bash

# 添加到Shell配置
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc

source ~/.bashrc
```

#### 安装指定Python版本

```bash
# 查看可用版本
pyenv install --list | grep 3.10

# 安装Python 3.10
pyenv install 3.10.13

# 设置全局Python版本
pyenv global 3.10.13

# 验证
python --version  # 应显示 Python 3.10.13
```

### 使用conda环境（可选）

```bash
# 创建conda环境
conda create -n stock-analysis python=3.10

# 激活环境
conda activate stock-analysis

# 安装依赖
pip install -r requirements.txt

# 退出环境
conda deactivate
```

---

## ⚙️ 配置文件设置

### 1. 数据库配置

**文件**: `config/database.yaml`

```yaml
database:
  # TimescaleDB配置
  timescaledb:
    host: localhost
    port: 5432
    database: stock_analysis
    user: postgres
    password: yourpassword
    pool_size: 10
    max_overflow: 20

  # Redis配置（可选）
  redis:
    host: localhost
    port: 6379
    db: 0
    password: null
    ttl: 3600  # 缓存过期时间（秒）
```

### 2. 数据源配置

**文件**: `config/data_sources.yaml`

```yaml
data_sources:
  # AkShare（免费，推荐）
  akshare:
    enabled: true
    rate_limit: 10  # 每秒请求数
    timeout: 30

  # Tushare Pro（需Token）
  tushare:
    enabled: false
    token: "YOUR_TUSHARE_TOKEN"  # 从 https://tushare.pro 获取
    rate_limit: 200
    timeout: 30
```

### 3. 日志配置

**文件**: `config/logging.yaml`

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"

  # 文件日志
  file:
    enabled: true
    path: logs/stock_analysis.log
    rotation: "100 MB"  # 日志轮转大小
    retention: "30 days"  # 保留时间
    compression: "zip"

  # 控制台日志
  console:
    enabled: true
    colorize: true
```

### 4. 环境变量

**文件**: `.env` (需创建)

```bash
# 数据库连接
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/stock_analysis

# Redis连接
REDIS_URL=redis://localhost:6379/0

# Tushare Token（可选）
TUSHARE_TOKEN=your_token_here

# 日志级别
LOG_LEVEL=INFO

# 并行任务数
N_JOBS=4

# GPU加速
USE_GPU=false
```

**加载环境变量**:
```bash
# 安装python-dotenv
pip install python-dotenv

# 在代码中加载
from dotenv import load_dotenv
load_dotenv()
```

---

## 🔍 安装验证

### 运行完整检查

```bash
# 运行安装检查脚本
python scripts/check_installation.py
```

**预期输出**:
```
✅ Python版本: 3.10.13
✅ 必需依赖: 全部安装
✅ 数据库连接: 成功
✅ CLI工具: 可用
✅ 测试套件: 通过
✅ 配置文件: 完整

🎉 安装成功！
```

### 手动验证

#### 1. Python依赖检查

```python
# scripts/check_dependencies.py
import sys

required = {
    'pandas': '2.0.0',
    'numpy': '1.24.0',
    'lightgbm': '4.0.0',
    'torch': '2.0.0',
}

for package, min_version in required.items():
    try:
        mod = __import__(package)
        version = getattr(mod, '__version__', '未知')
        print(f"✅ {package}: {version}")
    except ImportError:
        print(f"❌ {package}: 未安装")
        sys.exit(1)

print("\n🎉 所有依赖已正确安装！")
```

运行：
```bash
python scripts/check_dependencies.py
```

#### 2. 数据库连接测试

```python
# scripts/check_database.py
from src.data.database_manager import DatabaseManager

try:
    db = DatabaseManager()
    result = db.test_connection()
    if result:
        print("✅ 数据库连接成功")
        print(f"   版本: {db.get_version()}")
        print(f"   TimescaleDB: {db.has_timescaledb()}")
    else:
        print("❌ 数据库连接失败")
except Exception as e:
    print(f"❌ 错误: {e}")
```

运行：
```bash
python scripts/check_database.py
```

#### 3. 功能测试

```python
# scripts/quick_test.py
from src.providers import DataProviderFactory
from src.features import AlphaFactors
import pandas as pd

# 测试数据获取
print("测试数据获取...")
provider = DataProviderFactory.create_provider('akshare')
data = provider.get_daily_data('000001.SZ', '2024-01-01', '2024-01-31')
print(f"✅ 获取了 {len(data)} 条数据")

# 测试特征计算
print("\n测试特征计算...")
alpha = AlphaFactors(data)
features = alpha.calculate_momentum_factors()
print(f"✅ 计算了 {len(features.columns)} 个特征")

print("\n🎉 功能测试通过！")
```

运行：
```bash
python scripts/quick_test.py
```

---

## ❓ 常见问题

### Q1: pip install失败怎么办？

**A**: 常见解决方案：

```bash
# 1. 升级pip
pip install --upgrade pip setuptools wheel

# 2. 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3. 单独安装问题包
pip install pandas --no-cache-dir
```

### Q2: TA-Lib安装失败？

**A**: TA-Lib需要先安装C库：

**macOS**:
```bash
brew install ta-lib
pip install ta-lib
```

**Linux**:
```bash
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
pip install ta-lib
```

**Windows**:
- 下载预编译包：https://www.lfd.uci.edu/~gohlke/pythonlibs/#ta-lib
- 运行：`pip install TA_Lib‑0.4.28‑cp310‑cp310‑win_amd64.whl`

### Q3: PyTorch GPU版本如何安装？

**A**: 根据CUDA版本选择：

```bash
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 验证GPU可用性
python -c "import torch; print(f'GPU可用: {torch.cuda.is_available()}')"
```

### Q4: 数据库连接超时？

**A**: 检查以下几点：

1. PostgreSQL服务是否启动：
   ```bash
   # macOS
   brew services list | grep postgresql

   # Linux
   sudo systemctl status postgresql
   ```

2. 端口是否开放：
   ```bash
   netstat -an | grep 5432
   ```

3. 防火墙设置：
   ```bash
   # Linux
   sudo ufw allow 5432/tcp
   ```

4. 配置文件中的连接信息是否正确

### Q5: 虚拟环境激活失败？

**A**: 根据Shell类型使用正确的命令：

```bash
# bash/zsh
source venv/bin/activate

# fish
source venv/bin/activate.fish

# csh/tcsh
source venv/bin/activate.csh

# PowerShell (Windows)
venv\Scripts\Activate.ps1
```

---

## 📚 下一步

安装完成后，建议按以下顺序学习：

1. ✅ **快速开始** - [quick_start.md](quick_start.md) - 30秒上手
2. 📖 **CLI指南** - [CLI_GUIDE.md](CLI_GUIDE.md) - 命令行工具详解
3. 🎨 **可视化指南** - [VISUALIZATION_GUIDE.md](VISUALIZATION_GUIDE.md) - 数据可视化
4. 🧬 **特征工程** - [FEATURE_CONFIG_GUIDE.md](FEATURE_CONFIG_GUIDE.md) - 因子计算
5. 🤖 **模型训练** - [MODEL_USAGE_GUIDE.md](MODEL_USAGE_GUIDE.md) - 机器学习

---

## 🆘 获取帮助

如遇到安装问题，请通过以下方式获取帮助：

- 📧 **问题反馈**: [GitHub Issues](https://github.com/your-org/stock-analysis/issues)
- 💬 **讨论区**: [GitHub Discussions](https://github.com/your-org/stock-analysis/discussions)
- 📚 **完整文档**: [docs/README.md](../README.md)

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
