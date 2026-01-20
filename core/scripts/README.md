# Scripts 脚本目录

本目录包含各种辅助脚本，用于数据下载、测试和分析。

## 📁 脚本列表

### 数据下载脚本

1. **download_data.py** - CSV数据下载
   ```bash
   python core/scripts/download_data.py --years 5 --max-stocks 10
   ```
   - 下载股票数据到CSV文件
   - 用于离线数据分析

2. **download_data_to_db.py** - 数据库数据下载
   ```bash
   python core/scripts/download_data_to_db.py --years 5 --max-stocks 10
   ```
   - 下载股票数据到TimescaleDB
   - 用于数据库填充

### 测试脚本

3. **test_akshare.py** - AkShare数据源测试
   ```bash
   # 从项目根目录运行
   python core/scripts/test_akshare.py

   # 或使用虚拟环境
   source stock_env/bin/activate
   python core/scripts/test_akshare.py
   ```
   - 测试AkShare API连接
   - 验证数据下载功能
   - 包含3个测试用例

### 分析脚本

4. **run_analysis.sh** - 运行本地分析
   ```bash
   ./core/scripts/run_analysis.sh
   ```
   - 激活虚拟环境
   - 运行core/src/main.py

5. **start_jupyter.sh** - 启动Jupyter
   ```bash
   ./core/scripts/start_jupyter.sh
   ```
   - 启动Jupyter Notebook
   - 用于数据探索和可视化

## 🎯 使用场景

### 场景1: 初次使用，填充数据库

```bash
# 1. 激活虚拟环境
source stock_env/bin/activate

# 2. 下载股票列表和数据
python core/scripts/download_data_to_db.py --years 3 --max-stocks 50

# 3. 验证数据
docker exec stock_timescaledb psql -U stock_user -d stock_analysis -c "SELECT COUNT(*) FROM stock_daily;"
```

### 场景2: 测试AkShare连接

```bash
# 测试数据源是否可用
source stock_env/bin/activate
python core/scripts/test_akshare.py
```

### 场景3: 本地数据分析

```bash
# 启动Jupyter进行探索性分析
./core/scripts/start_jupyter.sh

# 或运行批量分析
./core/scripts/run_analysis.sh
```

## 📝 注意事项

1. **路径问题**:
   - 所有脚本都假设从**项目根目录**运行
   - 如果从其他目录运行，需要调整路径

2. **依赖问题**:
   - 本地运行需要激活虚拟环境：`source stock_env/bin/activate`
   - Docker运行使用Backend容器，无需虚拟环境

3. **数据源限流**:
   - AkShare有访问频率限制
   - 建议下载时设置`--delay 0.5`延迟参数

## 🔄 vs Backend API

| 用途 | 脚本 | Backend API |
|------|------|-------------|
| 快速测试 | ✅ test_akshare.py | ❌ |
| 批量下载 | ✅ download_data_to_db.py | ✅ POST /api/data/download |
| 数据探索 | ✅ Jupyter | ❌ |
| 生产使用 | ❌ | ✅ |

**建议**:
- **开发/测试**: 使用脚本，快速灵活
- **生产/Web**: 使用Backend API，稳定可靠

## 📚 相关文档

- [Core目录说明](../README.md)
- [项目架构](../../docs/ARCHITECTURE.md)
- [快速开始指南](../../QUICKSTART.md)

---

**最后更新**: 2026-01-20
