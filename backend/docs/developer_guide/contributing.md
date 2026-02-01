# 贡献指南

**版本**: v1.0.0
**最后更新**: 2026-02-01

---

## 欢迎贡献

感谢你对 Stock-Analysis Backend 项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码补丁
- ✅ 增加测试用例

---

## 快速开始

### 1. Fork 项目

点击 GitHub 页面右上角的 "Fork" 按钮

### 2. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/stock-analysis.git
cd stock-analysis/backend
```

### 3. 创建开发分支

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 4. 设置开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖（包括开发依赖）
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装 pre-commit 钩子
pre-commit install
```

---

## 开发流程

### 1. 代码规范

我们遵循 **PEP 8** 规范，并使用以下工具确保代码质量：

#### Black（代码格式化）

```bash
# 格式化代码
black app/ tests/

# 检查格式
black app/ tests/ --check
```

#### isort（导入排序）

```bash
# 排序导入
isort app/ tests/

# 检查导入顺序
isort app/ tests/ --check-only
```

#### Flake8（代码检查）

```bash
# 检查代码
flake8 app/ tests/
```

#### mypy（类型检查）

```bash
# 类型检查
mypy app/
```

### 2. 代码风格

#### 命名规范

```python
# ✅ 推荐
class DataService:  # 类名：大驼峰
    def get_stock_data(self, stock_code: str):  # 方法名：小写+下划线
        max_retry = 3  # 变量名：小写+下划线
        API_URL = "http://..."  # 常量：大写+下划线

# ❌ 不推荐
class dataService:  # 类名应该是大驼峰
    def GetStockData(self, StockCode):  # 方法名应该是小写+下划线
        MaxRetry = 3  # 变量名应该是小写
        api_url = "http://..."  # 常量应该是大写
```

#### 类型提示

```python
from typing import List, Optional, Dict, Any
from datetime import date

# ✅ 推荐：完整的类型提示
async def download_stock_data(
    stock_code: str,
    start_date: date,
    end_date: date,
    batch_size: int = 100
) -> Dict[str, Any]:
    """下载股票数据

    Args:
        stock_code: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        batch_size: 批次大小

    Returns:
        包含下载结果的字典
    """
    pass

# ❌ 不推荐：缺少类型提示
async def download_stock_data(stock_code, start_date, end_date, batch_size=100):
    pass
```

#### 文档字符串（Docstring）

我们使用 **Google Style** 文档字符串：

```python
def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 0.03
) -> float:
    """计算夏普比率

    Args:
        returns: 收益率列表
        risk_free_rate: 无风险利率，默认 3%

    Returns:
        夏普比率

    Raises:
        ValueError: 当收益率列表为空时

    Example:
        >>> returns = [0.01, -0.02, 0.03, 0.015]
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe Ratio: {sharpe:.2f}")
        Sharpe Ratio: 1.85
    """
    if not returns:
        raise ValueError("收益率列表不能为空")

    # 实现...
    return sharpe_ratio
```

### 3. 测试

#### 编写测试

所有新功能和 Bug 修复都应该包含测试：

```python
# tests/test_data_service.py
import pytest
from app.services.data_service import DataService

@pytest.mark.asyncio
async def test_download_stock_data():
    """测试下载股票数据"""
    service = DataService()

    result = await service.download_stock_data(
        stock_code="000001.SZ",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )

    assert result["status"] == "success"
    assert "data" in result
    assert len(result["data"]) > 0

@pytest.mark.asyncio
async def test_download_invalid_stock_code():
    """测试下载无效股票代码"""
    service = DataService()

    with pytest.raises(ValueError):
        await service.download_stock_data(
            stock_code="INVALID",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
```

#### 运行测试

```bash
# 运行所有测试
pytest tests/

# 运行特定测试文件
pytest tests/test_data_service.py

# 运行特定测试函数
pytest tests/test_data_service.py::test_download_stock_data

# 查看覆盖率
pytest tests/ --cov=app --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

#### 测试覆盖率要求

- 新代码覆盖率应达到 **80%+**
- 核心模块（services/）覆盖率应达到 **90%+**

### 4. 提交代码

#### Commit 规范

我们使用 **Conventional Commits** 规范：

```bash
# 格式
<type>(<scope>): <subject>

# 类型
feat:     新功能
fix:      Bug 修复
docs:     文档更新
style:    代码格式（不影响功能）
refactor: 重构
test:     添加测试
chore:    构建/工具链变更
perf:     性能优化

# 示例
git commit -m "feat(api): 添加批量下载股票数据接口"
git commit -m "fix(backtest): 修复回测引擎计算错误"
git commit -m "docs(readme): 更新快速开始指南"
git commit -m "test(service): 添加数据服务单元测试"
```

#### Commit 最佳实践

```bash
# ✅ 推荐：清晰、简洁、描述性强
git commit -m "feat(ml): 添加 LightGBM 模型训练支持"
git commit -m "fix(backtest): 修复滑点计算精度问题"
git commit -m "docs(api): 更新回测接口文档和示例"

# ❌ 不推荐：模糊、笼统
git commit -m "update"
git commit -m "fix bug"
git commit -m "add new feature"
```

### 5. 创建 Pull Request

#### 准备工作

```bash
# 1. 确保所有测试通过
pytest tests/

# 2. 确保代码格式正确
black app/ tests/ --check
isort app/ tests/ --check-only
flake8 app/ tests/
mypy app/

# 3. 更新到最新主分支
git fetch upstream
git rebase upstream/main

# 4. 推送到你的 Fork
git push origin feature/your-feature-name
```

#### PR 描述模板

```markdown
## 变更说明

简要描述本次 PR 的目的和内容。

## 变更类型

- [ ] Bug 修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 性能优化
- [ ] 测试增强

## 相关 Issue

Closes #123

## 测试

描述你如何测试了这些变更：

- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过

## Checklist

- [ ] 代码遵循项目规范
- [ ] 添加了必要的文档
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 代码已经过自我审查
```

---

## 项目结构

添加新功能时，请遵循以下结构：

```
backend/app/
├── api/endpoints/          # 添加新端点
├── services/               # 添加业务逻辑
├── repositories/           # 添加数据访问层
├── strategies/             # 添加新策略
├── models/                 # 添加数据模型
├── interfaces/             # 添加类型定义
└── utils/                  # 添加工具函数
```

### 添加新 API 端点

```python
# 1. 创建端点文件 app/api/endpoints/new_feature.py
from fastapi import APIRouter, Depends
from app.services.new_feature_service import NewFeatureService

router = APIRouter()

@router.get("/")
async def get_feature(
    service: NewFeatureService = Depends()
):
    """获取功能数据"""
    result = await service.get_data()
    return {"status": "success", "data": result}

# 2. 注册路由 app/api/__init__.py
from .endpoints import new_feature

router.include_router(
    new_feature.router,
    prefix="/new-feature",
    tags=["new-feature"]
)

# 3. 添加测试 tests/test_new_feature.py
@pytest.mark.asyncio
async def test_get_feature():
    # 测试代码
    pass
```

### 添加新服务

```python
# app/services/new_feature_service.py
from typing import Dict, Any
from loguru import logger

class NewFeatureService:
    """新功能服务

    负责处理新功能相关的业务逻辑。
    """

    def __init__(self):
        self.logger = logger

    async def get_data(self) -> Dict[str, Any]:
        """获取数据

        Returns:
            包含数据的字典
        """
        try:
            # 业务逻辑
            data = await self._fetch_data()
            return {"result": data}
        except Exception as e:
            self.logger.error(f"获取数据失败: {e}")
            raise

    async def _fetch_data(self):
        """私有方法：获取数据"""
        pass
```

---

## 代码审查

### 审查清单

作为审查者，请检查以下内容：

#### 功能性
- [ ] 代码实现了 PR 描述的功能
- [ ] 边界条件得到处理
- [ ] 错误情况得到处理

#### 代码质量
- [ ] 代码遵循项目规范
- [ ] 命名清晰、有意义
- [ ] 逻辑清晰、易于理解
- [ ] 无重复代码（DRY 原则）

#### 测试
- [ ] 包含单元测试
- [ ] 测试覆盖率足够
- [ ] 测试用例全面（正常/异常/边界）

#### 文档
- [ ] 包含必要的文档字符串
- [ ] 复杂逻辑有注释说明
- [ ] API 文档已更新（如有必要）

#### 性能
- [ ] 无明显性能问题
- [ ] 数据库查询已优化
- [ ] 使用异步 I/O（如需要）

#### 安全
- [ ] 输入已验证
- [ ] 无 SQL 注入风险
- [ ] 敏感信息未硬编码

---

## 发布流程

### 版本号规范

我们使用 **语义化版本** (Semantic Versioning)：

```
MAJOR.MINOR.PATCH

- MAJOR: 不兼容的 API 变更
- MINOR: 向后兼容的新功能
- PATCH: 向后兼容的 Bug 修复
```

示例：
- `1.0.0` -> `1.0.1`（Bug 修复）
- `1.0.1` -> `1.1.0`（新功能）
- `1.1.0` -> `2.0.0`（破坏性变更）

### 发布步骤

```bash
# 1. 更新版本号
# 编辑 app/main.py 中的 version

# 2. 更新 CHANGELOG.md
# 添加版本变更说明

# 3. 创建 release 分支
git checkout -b release/v1.1.0

# 4. 提交变更
git commit -m "chore(release): 发布 v1.1.0"

# 5. 创建标签
git tag -a v1.1.0 -m "Release v1.1.0"

# 6. 推送
git push origin release/v1.1.0
git push origin v1.1.0

# 7. 在 GitHub 创建 Release
```

---

## 获取帮助

### 文档

- 📖 [架构文档](../architecture/overview.md)
- 📚 [API 参考](../api_reference/README.md)
- 🎓 [用户指南](../user_guide/quick_start.md)

### 沟通渠道

- 💬 GitHub Discussions（讨论功能设计）
- 🐛 GitHub Issues（报告 Bug）
- 📧 邮件列表

### 常见问题

**Q: 我应该先创建 Issue 还是直接提交 PR？**

A: 对于 Bug 修复，可以直接提交 PR。对于新功能，建议先创建 Issue 讨论设计方案。

**Q: 如何快速找到可以贡献的内容？**

A: 查看 GitHub Issues 中标记为 `good first issue` 或 `help wanted` 的问题。

**Q: 我的 PR 多久会被审查？**

A: 通常在 1-3 个工作日内会有初步反馈。

**Q: 代码风格检查失败怎么办？**

A: 运行 `black app/ tests/` 和 `isort app/ tests/` 自动修复大部分问题。

---

## 行为准则

我们致力于营造开放、友好的社区环境：

- 🤝 尊重不同观点和经验
- 💬 使用友好、包容的语言
- 🎯 关注对项目最有利的事情
- 👥 尊重他人的时间和努力
- 📚 乐于分享知识和经验

---

## 致谢

感谢所有贡献者的付出！你的贡献让这个项目变得更好。

查看完整贡献者列表：[Contributors](https://github.com/your-org/stock-analysis/graphs/contributors)

---

**维护团队**: Quant Team
**文档版本**: v1.0.0
**最后更新**: 2026-02-01
