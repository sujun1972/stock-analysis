# 贡献指南

**Contributing to Stock-Analysis Core**

**版本**: v3.0.0
**最后更新**: 2026-02-01

---

## 🎉 欢迎贡献！

感谢你对 Stock-Analysis Core 的兴趣！我们欢迎各种形式的贡献，无论是报告Bug、提出新功能建议、改进文档，还是提交代码。

---

## 🚀 快速开始

### 1. Fork 项目

```bash
# 1. Fork项目到你的GitHub账号
# 2. 克隆你的Fork
git clone https://github.com/YOUR_USERNAME/stock-analysis.git
cd stock-analysis/core

# 3. 添加上游仓库
git remote add upstream https://github.com/original/stock-analysis.git

# 4. 创建开发分支
git checkout -b feature/your-feature-name
```

### 2. 设置开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装预提交钩子
pre-commit install
```

### 3. 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/features/test_alpha_factors.py

# 查看覆盖率
pytest --cov=src --cov-report=html
```

---

## 📋 贡献类型

### 1. 报告 Bug

**提交Issue前请检查**:
- [ ] 是否已有相同的Issue
- [ ] 使用最新版本是否仍存在问题
- [ ] 是否阅读过相关文档

**Bug报告模板**:

```markdown
## Bug描述
简要描述遇到的问题

## 复现步骤
1. 步骤1
2. 步骤2
3. ...

## 预期行为
描述你期望发生的结果

## 实际行为
描述实际发生的结果

## 环境信息
- OS: [e.g., macOS 13.0]
- Python: [e.g., 3.9.17]
- 版本: [e.g., v3.0.0]

## 错误日志
```python
# 粘贴错误堆栈
```

## 附加信息
其他相关信息或截图
```

### 2. 提出新功能

**功能请求模板**:

```markdown
## 功能描述
清晰简洁地描述你想要的功能

## 使用场景
描述这个功能解决什么问题

## 实现建议
如果有想法，可以描述如何实现

## 替代方案
是否考虑过其他解决方案？

## 附加信息
其他相关信息或示例
```

### 3. 改进文档

**文档贡献包括**:
- 修正拼写错误
- 改进示例代码
- 补充缺失文档
- 翻译文档

**文档标准**:
- 使用清晰简洁的语言
- 提供可运行的代码示例
- 包含必要的截图或图表
- 遵循现有文档格式

### 4. 提交代码

详见下方"开发流程"部分。

---

## 🔄 开发流程

### 1. 开发前准备

```bash
# 同步上游仓库
git fetch upstream
git checkout main
git merge upstream/main

# 创建功能分支
git checkout -b feature/new-alpha-factor
```

### 2. 编写代码

**代码要求**:
- ✅ 遵循 [代码规范](coding_standards.md)
- ✅ 编写充分的测试（覆盖率≥90%）
- ✅ 添加必要的文档字符串
- ✅ 更新相关文档

**示例：添加新的Alpha因子**

```python
# src/features/alpha_factors/custom_factors.py

def calculate_custom_momentum(
    data: pd.DataFrame,
    short_window: int = 5,
    long_window: int = 20
) -> pd.Series:
    """
    计算自定义动量因子

    Args:
        data: 包含价格数据的DataFrame
        short_window: 短期窗口
        long_window: 长期窗口

    Returns:
        pd.Series: 动量因子值

    Raises:
        ValueError: 当窗口参数不合法时

    Examples:
        >>> data = pd.DataFrame({'close': [100, 102, 101, 103, 105]})
        >>> momentum = calculate_custom_momentum(data)
        >>> assert not momentum.isna().all()
    """
    if short_window >= long_window:
        raise ValueError("short_window must be less than long_window")

    short_ma = data['close'].rolling(short_window).mean()
    long_ma = data['close'].rolling(long_window).mean()

    return (short_ma - long_ma) / long_ma
```

### 3. 编写测试

**测试要求**:
- ✅ 单元测试覆盖率≥90%
- ✅ 测试边界条件
- ✅ 测试异常情况
- ✅ 使用有意义的测试名称

```python
# tests/unit/features/test_custom_factors.py

import pytest
import pandas as pd
from src.features.alpha_factors.custom_factors import calculate_custom_momentum

class TestCustomMomentum:
    @pytest.fixture
    def sample_data(self):
        """测试数据"""
        return pd.DataFrame({
            'close': [100, 102, 101, 103, 105, 107, 106, 108, 110]
        })

    def test_basic_calculation(self, sample_data):
        """测试基本计算"""
        result = calculate_custom_momentum(sample_data, 3, 5)

        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        # 前期数据应该是NaN
        assert result.iloc[:4].isna().all()

    def test_invalid_windows(self, sample_data):
        """测试无效窗口参数"""
        with pytest.raises(ValueError, match="short_window must be less"):
            calculate_custom_momentum(sample_data, 20, 5)

    def test_empty_data(self):
        """测试空数据"""
        empty_df = pd.DataFrame({'close': []})
        result = calculate_custom_momentum(empty_df)
        assert len(result) == 0

    @pytest.mark.parametrize("short,long", [
        (5, 10),
        (5, 20),
        (10, 30)
    ])
    def test_different_windows(self, sample_data, short, long):
        """测试不同窗口参数"""
        result = calculate_custom_momentum(sample_data, short, long)
        assert not result.isna().all()
```

### 4. 提交代码

**提交信息规范**:

```bash
# 格式: <type>(<scope>): <subject>

# 类型 (type):
# - feat: 新功能
# - fix: Bug修复
# - docs: 文档变更
# - style: 代码格式（不影响功能）
# - refactor: 重构
# - test: 测试相关
# - chore: 构建/工具变更

# 示例
git add src/features/alpha_factors/custom_factors.py
git add tests/unit/features/test_custom_factors.py
git commit -m "feat(features): add custom momentum alpha factor

- Implement custom momentum calculation
- Add unit tests with 95% coverage
- Update documentation"
```

### 5. 创建 Pull Request

**PR检查清单**:

- [ ] 代码遵循项目规范
- [ ] 所有测试通过
- [ ] 测试覆盖率≥90%
- [ ] 文档已更新
- [ ] 提交信息清晰
- [ ] PR描述详细

**PR模板**:

```markdown
## 变更类型
- [ ] Bug修复
- [ ] 新功能
- [ ] 重构
- [ ] 文档更新
- [ ] 其他

## 变更描述
简要描述本次PR的变更内容

## 相关Issue
Closes #123

## 测试
- [ ] 添加了新测试
- [ ] 所有测试通过
- [ ] 测试覆盖率: XX%

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已更新文档
- [ ] 已添加必要的测试
- [ ] 所有CI检查通过

## 截图（如适用）
粘贴相关截图

## 附加信息
其他需要说明的信息
```

---

## ✅ 代码审查标准

### 审查要点

**功能性**:
- ✅ 代码实现是否符合需求
- ✅ 是否有未处理的边界情况
- ✅ 是否有潜在的Bug

**代码质量**:
- ✅ 是否遵循项目代码规范
- ✅ 命名是否清晰
- ✅ 逻辑是否易懂
- ✅ 是否有重复代码

**测试**:
- ✅ 测试覆盖率是否足够
- ✅ 测试是否有效
- ✅ 是否测试了边界情况

**文档**:
- ✅ 是否有清晰的文档字符串
- ✅ 复杂逻辑是否有注释
- ✅ 是否更新了相关文档

### 审查流程

1. **自动检查**: CI会自动运行测试和代码质量检查
2. **代码审查**: 至少需要1位维护者审查批准
3. **修改反馈**: 根据审查意见修改代码
4. **合并**: 审查通过后合并到main分支

---

## 🎯 贡献指南

### 新手友好任务

标记为 `good first issue` 的Issue适合新手：

- 文档改进
- 简单Bug修复
- 添加测试
- 代码注释

### 高级任务

- 新功能开发
- 性能优化
- 架构改进
- 复杂Bug修复

### 寻找贡献方向

1. 查看 [技术债务列表](../planning/tech_debt.md)
2. 查看 [开发路线图](../ROADMAP.md)
3. 浏览 [Open Issues](https://github.com/your-org/stock-analysis/issues)
4. 参与 [Discussions](https://github.com/your-org/stock-analysis/discussions)

---

## 🏆 贡献者权益

### 认可

- ✅ 贡献者名单（CONTRIBUTORS.md）
- ✅ Release Notes致谢
- ✅ 项目文档署名

### 成长

- ✅ 代码审查反馈
- ✅ 技术讨论参与
- ✅ 核心贡献者机会

---

## 📞 联系方式

### 获取帮助

- **GitHub Issues**: 报告Bug或请求功能
- **GitHub Discussions**: 技术讨论和问答
- **Email**: team@stock-analysis.com

### 社区规范

- 尊重他人
- 建设性反馈
- 保持友好
- 遵守开源协议

---

## 📚 参考文档

### 开发指南
- 🎨 [代码规范](coding_standards.md) - PEP 8、命名规范、类型提示
- 🧪 [测试指南](testing.md) - 如何编写测试、最佳实践
  - 📋 [运行测试](../../tests/README.md) - 交互式菜单、测试统计（2,900+测试）
  - 🔗 [集成测试](../../tests/integration/README.md) - 端到端测试
  - ⚡ [性能测试](../../tests/performance/README.md) - 性能基准

### 项目文档
- 🏗️ [架构文档](../architecture/overview.md) - 系统架构设计
- 📖 [开发路线图](../ROADMAP.md) - 项目规划

---

## ❓ 常见问题

### Q: 如何选择要贡献的Issue？

A: 新手可以从标记 `good first issue` 的Issue开始。查看Issue标签和难度评级。

### Q: PR多久会被审查？

A: 通常在1-3个工作日内会有初步反馈。复杂PR可能需要更长时间。

### Q: 如何成为核心贡献者？

A: 持续高质量贡献，积极参与社区讨论。维护者会邀请活跃贡献者。

### Q: 测试覆盖率不够90%怎么办？

A: 添加更多测试用例，特别是边界情况和异常处理。参考现有测试代码。

### Q: 不确定实现方式怎么办？

A: 先创建Issue讨论方案，或提交Draft PR寻求反馈。

---

## 🙏 致谢

感谢所有为项目做出贡献的开发者！

查看完整贡献者名单: [CONTRIBUTORS.md](../../CONTRIBUTORS.md)

---

**文档版本**: v3.0.0
**维护团队**: Quant Team
**最后更新**: 2026-02-01
