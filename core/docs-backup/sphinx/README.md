# Sphinx API 文档

本目录包含使用 Sphinx 自动生成的 Stock Analysis Core API 文档。

## 📚 文档说明

- **版本**: v3.0.0
- **生成工具**: Sphinx 9.1.0
- **主题**: Read the Docs Theme
- **语言**: 简体中文

## 🚀 快速开始

### 1. 安装依赖

```bash
# 在 core 目录下
source venv/bin/activate
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints
```

### 2. 生成 API 文档

```bash
# 方法1: 使用 make (推荐)
cd docs/sphinx
make html

# 方法2: 使用构建脚本
cd docs/sphinx
./build.sh

# 方法3: 手动构建
cd docs/sphinx
../../venv/bin/sphinx-build -b html source build/html
```

### 3. 查看文档

```bash
# 在浏览器中打开
open build/html/index.html

# 或使用本地服务器
cd build/html
python -m http.server 8000
# 访问 http://localhost:8000
```

## 📂 目录结构

```
docs/sphinx/
├── source/              # 源文件目录
│   ├── conf.py         # Sphinx 配置文件
│   ├── index.rst       # 文档首页
│   ├── api/            # 自动生成的 API 文档 (197个模块)
│   ├── _static/        # 静态资源
│   └── _templates/     # 模板文件
├── build/              # 构建输出目录
│   └── html/           # HTML 文档 (13MB)
├── Makefile            # Make 构建文件
├── make.bat            # Windows 构建脚本
├── build.sh            # 快速构建脚本
└── README.md           # 本文件
```

## 🔄 更新文档

当源代码发生变化时，重新生成 API 文档：

```bash
cd docs/sphinx

# 1. 重新生成 API RST 文件
../../venv/bin/sphinx-apidoc -f -o source/api ../../src -e

# 2. 构建 HTML 文档
make html

# 或使用一键脚本
./build.sh --clean
```

## ⚙️ 配置说明

### Sphinx 配置 (source/conf.py)

主要配置项：

- **主题**: `sphinx_rtd_theme` (Read the Docs)
- **扩展**:
  - `sphinx.ext.autodoc` - 自动提取 docstrings
  - `sphinx.ext.napoleon` - 支持 Google/NumPy 风格文档
  - `sphinx.ext.viewcode` - 添加源代码链接
  - `sphinx.ext.intersphinx` - 跨项目引用
  - `sphinx_autodoc_typehints` - 类型提示支持

### API 文档生成选项

```bash
sphinx-apidoc [OPTIONS] -o <output_dir> <module_dir>

常用选项:
  -f, --force           覆盖现有文件
  -e, --separate        每个模块单独一个文件
  -o <dir>              输出目录
  -M, --module-first    模块名在前
  --implicit-namespaces 支持命名空间包
```

## 📊 文档统计

- **模块总数**: 197个
- **HTML页面**: 200个
- **文档大小**: 21MB
- **生成时间**: ~6秒
- **构建警告**: 196个

## ⚠️ 已知问题

**当前状态**: ⚠️ 文档结构完整，但内容有限

**问题**: 大部分模块（196/197）无法正常导入，导致只显示模块名称，不显示详细内容

**原因**:
1. **循环导入**: `src/data_pipeline/__init__.py` ↔ `src/pipeline.py`
2. **缺少依赖**: TA-Lib, torch 等可选依赖未安装
3. **模块初始化**: 某些模块在导入时执行代码

**影响**:
- ✅ 可以查看模块结构和组织
- ❌ 无法显示类、函数、参数的详细说明
- ⚠️ 需要直接查看源代码了解 API 详情

**解决方案**:

详见 → [API_DOCS_STATUS.md](API_DOCS_STATUS.md)

**临时解决办法**:
```bash
# 查看模块结构使用 Sphinx 文档
open build/html/index.html

# 查看详细 API 直接查看源代码
code ../../src/data_pipeline/data_loader.py
# 或使用 IDE，会正确显示 docstrings
```

**优先级**: P1（高）
**预计修复**: 2周内完成关键模块修复

## 🛠️ 故障排查

### 构建失败

```bash
# 检查 Sphinx 安装
../../venv/bin/sphinx-build --version

# 清理构建缓存
make clean

# 重新构建
make html
```

### 模块导入错误

确保 `source/conf.py` 中的路径配置正确：

```python
sys.path.insert(0, os.path.abspath('../../../src'))
```

### 警告过多

大部分警告是因为缺少 docstrings，可以：

1. 为模块/类/函数添加文档字符串
2. 使用 `-W` 参数将警告视为错误

## 📝 文档编写规范

### Google 风格 Docstring 示例

```python
def calculate_returns(prices: pd.Series, method: str = 'simple') -> pd.Series:
    """计算收益率。

    Args:
        prices: 价格序列
        method: 计算方法，'simple' 或 'log'

    Returns:
        收益率序列

    Raises:
        ValueError: 当 method 不支持时

    Examples:
        >>> prices = pd.Series([100, 105, 110])
        >>> calculate_returns(prices)
        0    NaN
        1   0.05
        2   0.048
        dtype: float64
    """
    pass
```

### NumPy 风格 Docstring 示例

```python
def backtest(strategy, data):
    """运行回测。

    Parameters
    ----------
    strategy : BaseStrategy
        交易策略实例
    data : pd.DataFrame
        历史数据

    Returns
    -------
    BacktestResult
        回测结果对象

    See Also
    --------
    parallel_backtest : 并行回测
    """
    pass
```

## 📦 Git 版本控制

### 提交到 Git

Sphinx 文档目录已配置 `.gitignore`，以下文件会被忽略：

**自动忽略**:
- `build/` - 构建输出目录（29MB，自动生成）
- `__pycache__/` - Python 缓存
- `.DS_Store` - macOS 系统文件

**应该提交的文件**:
- `source/` - 源文件和配置
  - `conf.py` - Sphinx 配置
  - `index.rst` - 文档首页
  - `api/*.rst` - API 文档 RST 文件（197个）
- `Makefile` - 构建配置
- `build.sh` - 构建脚本
- `README.md` - 本文档
- `.gitignore` - Git 忽略规则

### 推荐工作流

```bash
# 1. 修改源代码后，重新生成 API 文档
./build.sh --rebuild-api

# 2. 检查 Git 状态（build/ 应该被忽略）
git status

# 3. 提交源文件和配置
git add source/ Makefile build.sh README.md .gitignore
git commit -m "docs: 更新 Sphinx API 文档"

# 4. 不要提交 build/ 目录！
# .gitignore 已自动处理
```

### 团队协作

其他开发者克隆仓库后：

```bash
# 1. 安装依赖
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

# 2. 构建文档
cd docs/sphinx
./build.sh

# 3. 查看文档
open build/html/index.html
```

## 🔗 相关资源

- [Sphinx 官方文档](https://www.sphinx-doc.org/)
- [reStructuredText 语法](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html)
- [Napoleon 扩展](https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html)
- [Read the Docs 主题](https://sphinx-rtd-theme.readthedocs.io/)

## 📞 支持

如有问题，请查看：

- 项目主文档: [../README.md](../README.md)
- 开发指南: [../developer_guide/contributing.md](../developer_guide/contributing.md)
- Issue 追踪: https://github.com/your-org/stock-analysis/issues

---

**维护者**: Quant Team
**最后更新**: 2026-02-01
**文档版本**: v3.0.0
