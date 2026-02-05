"""
Pytest 配置文件

全局测试配置、夹具和钩子函数

作者: Backend Team
创建日期: 2026-02-01
版本: 1.0.0
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# 添加 core 目录到 Python 路径（用于导入 src.* 模块）
core_path = backend_path.parent / "core"
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))


# ==================== Pytest 配置 ====================

def pytest_configure(config):
    """Pytest 启动配置"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "unit: 标记为单元测试"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "performance: 标记为性能测试"
    )
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试"
    )


# ==================== 事件循环配置 ====================

@pytest.fixture(scope="session")
def event_loop():
    """
    创建全局事件循环

    用于异步测试
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== 测试数据夹具 ====================

@pytest.fixture
def sample_stock_codes():
    """样例股票代码列表"""
    return ["000001", "000002", "300001", "600000", "688001"]


@pytest.fixture
def sample_date_range():
    """样例日期范围"""
    return {
        "start": "2024-01-01",
        "end": "2024-01-31"
    }


# ==================== Mock 夹具 ====================

@pytest.fixture
def mock_stock_list():
    """Mock 股票列表数据"""
    return [
        {
            "code": "000001",
            "name": "平安银行",
            "market": "主板",
            "industry": "银行",
            "area": "深圳",
            "list_date": "1991-04-03"
        },
        {
            "code": "000002",
            "name": "万科A",
            "market": "主板",
            "industry": "房地产",
            "area": "深圳",
            "list_date": "1991-01-29"
        },
        {
            "code": "300001",
            "name": "特锐德",
            "market": "创业板",
            "industry": "电气设备",
            "area": "青岛",
            "list_date": "2009-10-30"
        }
    ]


@pytest.fixture
def mock_stock_info():
    """Mock 股票详情数据"""
    return {
        "code": "000001",
        "name": "平安银行",
        "market": "主板",
        "industry": "银行",
        "area": "深圳",
        "list_date": "1991-04-03",
        "status": "正常"
    }


# ==================== 测试环境清理 ====================

@pytest.fixture(autouse=True)
def reset_adapters():
    """
    每个测试后重置 Adapter（如果需要）

    自动使用，无需显式调用
    """
    yield
    # 测试后清理逻辑（如果需要）
    pass


# ==================== 测试报告钩子 ====================

def pytest_report_header(config):
    """测试报告头部信息"""
    return [
        "Backend Stocks API Tests",
        f"Python: {sys.version}",
        f"Backend Path: {backend_path}"
    ]


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    测试报告生成钩子

    可用于添加额外的测试信息
    """
    outcome = yield
    report = outcome.get_result()

    # 在失败时添加额外信息
    if report.when == "call" and report.failed:
        # 可以在这里添加失败时的额外日志
        pass
