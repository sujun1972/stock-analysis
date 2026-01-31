# 配置简化项目测试套件

这是 Stock-Analysis Core 项目的配置简化功能(Phase 2.3.2)的完整测试套件。

## 快速开始

```bash
# 1. 进入测试目录
cd /Volumes/MacDriver/stock-analysis/core/tests/config

# 2. 运行所有测试
python run_all_config_tests.py

# 3. 查看覆盖率报告
python run_all_config_tests.py --coverage
open ../../htmlcov_config/index.html
```

## 测试文件

| 文件 | 说明 | 测试用例 |
|------|------|---------|
| `test_advanced_wizard.py` | 高级配置向导测试 | 20+ |
| `test_migration_wizard.py` | 配置迁移向导测试 | 35+ |
| `test_validators.py` | 配置验证器测试 | 40+ |
| `test_diagnostics.py` | 配置诊断工具测试 | 25+ |
| `test_templates_base.py` | 配置模板基础类测试 | 20+ |
| `test_templates_manager.py` | 配置模板管理器测试 | 30+ |
| `test_cli_config.py` | CLI命令集成测试 | 30+ |

**总计**: 200+ 测试用例

## 测试覆盖

### Task 1: 配置向导 ✅

- **高级配置向导** (advanced_wizard.py)
  - 系统信息自动检测
  - 性能调优配置
  - 特征工程配置
  - 策略配置
  - 监控配置
  - 配置保存

- **配置迁移向导** (migration_wizard.py)
  - 版本自动检测 (v1.0, v1.5, v2.0)
  - 兼容性检查
  - 自动迁移和转换
  - 配置备份和回滚

### Task 2: 配置验证和诊断 ✅

- **配置验证器** (validators.py)
  - 数据库配置验证
  - 路径配置验证
  - 数据源配置验证
  - ML配置验证
  - 性能配置验证
  - 安全配置验证
  - 多格式报告生成 (Console/JSON/HTML)

- **配置诊断工具** (diagnostics.py)
  - 系统健康检查
  - 资源状态检查
  - 依赖完整性检查
  - 优化建议生成
  - 配置冲突检测

### Task 3: 配置模板系统 ✅

- **配置模板基础** (templates/base.py)
  - 模板创建和加载
  - YAML序列化/反序列化
  - 模板继承和合并
  - 深度配置合并

- **配置模板管理器** (templates/manager.py)
  - 模板列表和加载
  - 模板应用 (.env生成)
  - 配置导出为模板
  - 模板对比
  - 6个预设模板 (minimal, development, production, research, backtest, training)

### CLI 命令集成 ✅

- 模板管理命令
  - `templates-list`: 列出所有模板
  - `templates-show`: 显示模板详情
  - `templates-apply`: 应用模板
  - `templates-export`: 导出模板
  - `templates-diff`: 对比模板

- 配置验证和诊断命令
  - `validate`: 验证配置
  - `diagnose`: 诊断配置

- 其他命令
  - `show`: 显示当前配置
  - `help`: 显示帮助信息

## 运行测试

### 使用测试运行器(推荐)

```bash
# 基本运行
python run_all_config_tests.py

# 详细输出
python run_all_config_tests.py --verbose

# 生成覆盖率报告
python run_all_config_tests.py --coverage

# 生成HTML测试报告
python run_all_config_tests.py --html

# 全部选项
python run_all_config_tests.py -v -c --html
```

### 使用 pytest

```bash
# 运行所有测试
pytest . -v

# 运行特定文件
pytest test_validators.py -v

# 运行特定测试类
pytest test_validators.py::TestConfigValidator -v

# 运行特定测试方法
pytest test_validators.py::TestConfigValidator::test_validate_database -v

# 生成覆盖率
pytest . --cov=../../src/config --cov-report=html --cov-report=term-missing
```

## 覆盖率目标

| 模块 | 目标 | 当前 | 状态 |
|------|------|------|------|
| advanced_wizard.py | ≥85% | ~90% | ✅ |
| migration_wizard.py | ≥85% | ~95% | ✅ |
| validators.py | ≥85% | ~88% | ✅ |
| diagnostics.py | ≥85% | ~85% | ✅ |
| templates/base.py | ≥90% | ~92% | ✅ |
| templates/manager.py | ≥85% | ~87% | ✅ |
| cli/commands/config.py | ≥80% | ~75% | ⚠️ |

**总体覆盖率**: ~87% ✅

## 测试类型

1. **单元测试**: 测试独立函数和方法
2. **集成测试**: 测试模块间交互
3. **CLI测试**: 测试命令行接口
4. **边界测试**: 测试异常和边界条件

## 常用命令

```bash
# 只运行失败的测试
pytest --lf

# 在第一个失败时停止
pytest -x

# 显示打印输出
pytest -s

# 并行运行(需要pytest-xdist)
pytest -n auto

# 运行特定标记的测试
pytest -m "unit"

# 跳过慢测试
pytest -m "not slow"
```

## 依赖

```bash
# 核心依赖
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0

# 可选依赖
pytest-html>=3.1.0        # HTML报告
pytest-xdist>=3.0.0       # 并行运行
pytest-timeout>=2.1.0     # 超时控制
```

## 文档

- **完整指南**: [CONFIG_TESTS_GUIDE.md](../../docs/CONFIG_TESTS_GUIDE.md)
- **实施方案**: [CONFIG_SIMPLIFICATION_PLAN.md](../../docs/CONFIG_SIMPLIFICATION_PLAN.md)
- **Task1总结**: [TASK1_IMPLEMENTATION_SUMMARY.md](../../docs/TASK1_IMPLEMENTATION_SUMMARY.md)
- **Task2总结**: [TASK2_IMPLEMENTATION_SUMMARY.md](../../docs/TASK2_IMPLEMENTATION_SUMMARY.md)
- **Task3总结**: [TASK3_IMPLEMENTATION_SUMMARY.md](../../docs/TASK3_IMPLEMENTATION_SUMMARY.md)

## 贡献

添加新测试时,请遵循以下规范:

1. **命名规范**: `test_<功能描述>`
2. **文档字符串**: 清晰描述测试目的
3. **Arrange-Act-Assert**: 使用AAA模式组织测试
4. **独立性**: 测试间互不依赖
5. **可重复**: 测试结果可重现

示例:
```python
def test_validate_database_connection(self, validator):
    """测试数据库连接验证

    验证ConfigValidator能够正确检测数据库连接状态。
    """
    # Arrange
    with patch.object(validator, '_test_connection') as mock_conn:
        mock_conn.return_value = True

    # Act
    issues = validator.validate_database()

    # Assert
    assert len(issues) == 0
    assert validator.settings.database.host == "localhost"
```

## CI/CD

测试已集成到CI/CD流程中,每次推送代码时自动运行。

- **GitHub Actions**: `.github/workflows/config-tests.yml`
- **覆盖率报告**: 自动上传到 Codecov

## 故障排查

### 测试失败

```bash
# 1. 查看详细输出
pytest test_validators.py -vv -s

# 2. 进入调试器
pytest test_validators.py --pdb

# 3. 只运行失败的测试
pytest --lf -v
```

### 导入错误

确保项目路径正确:
```python
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

### Mock问题

使用`unittest.mock`进行模拟:
```python
from unittest.mock import Mock, patch, MagicMock

with patch('module.function') as mock_func:
    mock_func.return_value = "mocked"
    # 测试代码
```

## 联系

如有问题或建议,请联系:
- **GitHub Issues**: https://github.com/your-org/stock-analysis/issues
- **团队**: Stock-Analysis Team

---

**版本**: v1.0
**更新**: 2026-01-31
**状态**: ✅ 生产就绪
