"""
持仓管理器测试
测试 Position 和 PositionManager 类的所有功能
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import Mock, patch

# 导入被测试模块
try:
    from src.backtest.position_manager import Position, PositionManager
except ImportError:
    # 处理tests/unit/backtest/目录下的导入路径问题
    import sys
    from pathlib import Path
    core_path = Path(__file__).parent.parent.parent.parent
    if str(core_path) not in sys.path:
        sys.path.insert(0, str(core_path))
    from src.backtest.position_manager import Position, PositionManager


# ==================== Position 类测试 ====================

class TestPosition:
    """测试 Position 类"""

    def test_position_initialization(self):
        """测试持仓初始化"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        assert pos.stock_code == '600000'
        assert pos.shares == 1000
        assert pos.entry_price == 10.0
        assert pos.entry_date == datetime(2023, 1, 1)
        assert pos.entry_cost == 50.0

    def test_position_initialization_without_cost(self):
        """测试持仓初始化（无成本）"""
        pos = Position(
            stock_code='000001',
            shares=500,
            entry_price=15.0,
            entry_date=datetime(2023, 1, 1)
        )

        assert pos.entry_cost == 0.0

    def test_market_value(self):
        """测试市值计算"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1)
        )

        # 当前价格 11.0
        market_value = pos.market_value(11.0)
        assert market_value == 11000.0

        # 当前价格 9.0
        market_value = pos.market_value(9.0)
        assert market_value == 9000.0

    def test_profit_loss_profit(self):
        """测试盈亏计算 - 盈利"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 盈利: (11 - 10) * 1000 - 50 = 950
        pnl = pos.profit_loss(11.0)
        assert pnl == 950.0

    def test_profit_loss_loss(self):
        """测试盈亏计算 - 亏损"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 亏损: (9 - 10) * 1000 - 50 = -1050
        pnl = pos.profit_loss(9.0)
        assert pnl == -1050.0

    def test_profit_loss_pct_profit(self):
        """测试盈亏比例 - 盈利"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 盈利比例: 950 / (10 * 1000 + 50) = 950 / 10050 ≈ 0.0945
        pnl_pct = pos.profit_loss_pct(11.0)
        assert abs(pnl_pct - 0.0945) < 0.0001

    def test_profit_loss_pct_loss(self):
        """测试盈亏比例 - 亏损"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 亏损比例: -1050 / 10050 ≈ -0.1045
        pnl_pct = pos.profit_loss_pct(9.0)
        assert abs(pnl_pct + 0.1045) < 0.0001

    def test_profit_loss_pct_zero_cost_basis(self):
        """测试盈亏比例 - 零成本基础"""
        pos = Position(
            stock_code='600000',
            shares=0,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=0.0
        )

        # 零成本基础应返回0
        pnl_pct = pos.profit_loss_pct(11.0)
        assert pnl_pct == 0.0

    def test_to_dict(self):
        """测试转换为字典"""
        pos = Position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        data = pos.to_dict()
        assert data['stock_code'] == '600000'
        assert data['shares'] == 1000
        assert data['entry_price'] == 10.0
        assert data['entry_date'] == datetime(2023, 1, 1)
        assert data['entry_cost'] == 50.0


# ==================== PositionManager 初始化测试 ====================

class TestPositionManagerInit:
    """测试 PositionManager 初始化"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = PositionManager(
            initial_capital=1000000,
            max_position_pct=0.2,
            max_single_loss_pct=0.05,
            min_position_value=10000.0
        )

        assert manager.initial_capital == 1000000
        assert manager.max_position_pct == 0.2
        assert manager.max_single_loss_pct == 0.05
        assert manager.min_position_value == 10000.0
        assert manager.cash == 1000000
        assert len(manager.positions) == 0

    def test_manager_initialization_defaults(self):
        """测试管理器初始化（默认参数）"""
        manager = PositionManager(initial_capital=500000)

        assert manager.initial_capital == 500000
        assert manager.max_position_pct == 0.2
        assert manager.max_single_loss_pct == 0.05
        assert manager.min_position_value == 10000.0
        assert manager.cash == 500000


# ==================== PositionManager 持仓操作测试 ====================

class TestPositionManagerOperations:
    """测试 PositionManager 持仓操作"""

    @pytest.fixture
    def manager(self):
        """创建测试用管理器"""
        return PositionManager(initial_capital=1000000)

    def test_add_position_new(self, manager):
        """测试添加新持仓"""
        manager.add_position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        assert len(manager.positions) == 1
        assert '600000' in manager.positions
        assert manager.positions['600000'].shares == 1000
        assert manager.cash == 1000000 - 10000 - 50  # 989950

    def test_add_position_accumulate(self, manager):
        """测试加仓（累积持仓）"""
        # 第一次买入
        manager.add_position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 第二次加仓
        manager.add_position(
            stock_code='600000',
            shares=500,
            entry_price=12.0,
            entry_date=datetime(2023, 1, 2),
            entry_cost=30.0
        )

        pos = manager.positions['600000']
        assert pos.shares == 1500
        # 平均成本: (1000*10 + 500*12) / 1500 = 16000/1500 ≈ 10.67
        assert abs(pos.entry_price - 10.67) < 0.01
        assert pos.entry_date == datetime(2023, 1, 1)  # 保留原始日期
        assert pos.entry_cost == 80.0  # 累积成本

        # 现金: 1000000 - (1000*10+50) - (500*12+30) = 983920
        assert manager.cash == 983920

    def test_remove_position_full(self, manager):
        """测试全部卖出"""
        # 先买入
        manager.add_position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 全部卖出
        pnl = manager.remove_position(
            stock_code='600000',
            shares=1000,
            exit_price=11.0,
            exit_cost=25.0
        )

        # 盈亏: profit_loss(11) - exit_cost = ((11-10)*1000 - 50) - 25 = 950 - 25 = 925
        assert pnl == 925.0
        assert '600000' not in manager.positions
        # 现金: 989950 + (1000*11 - 25) = 1000925
        assert manager.cash == 1000925

    def test_remove_position_partial(self, manager):
        """测试部分卖出"""
        # 先买入
        manager.add_position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=100.0
        )

        # 部分卖出
        pnl = manager.remove_position(
            stock_code='600000',
            shares=400,
            exit_price=11.0,
            exit_cost=20.0
        )

        # 盈亏: (11-10)*400 - 20 = 380
        assert pnl == 380.0
        assert '600000' in manager.positions
        pos = manager.positions['600000']
        assert pos.shares == 600
        # 成本按比例减少: 100 * (600/1000) = 60
        assert pos.entry_cost == 60.0

        # 现金: 989900 + (400*11 - 20) = 994280
        assert manager.cash == 994280

    def test_remove_position_nonexistent(self, manager):
        """测试卖出不存在的持仓"""
        pnl = manager.remove_position(
            stock_code='600000',
            shares=100,
            exit_price=11.0
        )

        assert pnl is None

    def test_remove_position_over_shares(self, manager):
        """测试卖出股数超过持仓（应卖出全部）"""
        # 先买入
        manager.add_position(
            stock_code='600000',
            shares=1000,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1),
            entry_cost=50.0
        )

        # 卖出超过持有的股数
        pnl = manager.remove_position(
            stock_code='600000',
            shares=1500,
            exit_price=11.0,
            exit_cost=25.0
        )

        # 应该全部卖出
        assert '600000' not in manager.positions
        assert pnl == 925.0  # profit_loss(11) - exit_cost = 950 - 25


# ==================== PositionManager 查询测试 ====================

class TestPositionManagerQuery:
    """测试 PositionManager 查询功能"""

    @pytest.fixture
    def manager_with_positions(self):
        """创建有持仓的管理器"""
        manager = PositionManager(initial_capital=1000000)
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)
        manager.add_position('000001', 2000, 15.0, datetime(2023, 1, 2), 75)
        return manager

    def test_get_position_exists(self, manager_with_positions):
        """测试获取存在的持仓"""
        pos = manager_with_positions.get_position('600000')
        assert pos is not None
        assert pos.stock_code == '600000'
        assert pos.shares == 1000

    def test_get_position_not_exists(self, manager_with_positions):
        """测试获取不存在的持仓"""
        pos = manager_with_positions.get_position('999999')
        assert pos is None

    def test_has_position_true(self, manager_with_positions):
        """测试检查持仓存在"""
        assert manager_with_positions.has_position('600000') is True
        assert manager_with_positions.has_position('000001') is True

    def test_has_position_false(self, manager_with_positions):
        """测试检查持仓不存在"""
        assert manager_with_positions.has_position('999999') is False

    def test_get_all_positions(self, manager_with_positions):
        """测试获取所有持仓"""
        all_pos = manager_with_positions.get_all_positions()
        assert len(all_pos) == 2
        assert '600000' in all_pos
        assert '000001' in all_pos

        # 注意: positions.copy()是浅拷贝，字典被复制但Position对象是同一个
        # 修改字典本身不影响原字典
        all_pos['999999'] = Position('999999', 100, 10.0, datetime(2023, 1, 1))
        assert '999999' not in manager_with_positions.positions

        # 但修改Position对象会影响原对象（浅拷贝行为）
        original_shares = manager_with_positions.positions['600000'].shares
        all_pos['600000'].shares = 9999
        assert manager_with_positions.positions['600000'].shares == 9999  # 浅拷贝

        # 恢复原值
        all_pos['600000'].shares = original_shares


# ==================== PositionManager 计算测试 ====================

class TestPositionManagerCalculations:
    """测试 PositionManager 计算功能"""

    @pytest.fixture
    def manager_with_positions(self):
        """创建有持仓的管理器"""
        manager = PositionManager(initial_capital=1000000)
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)
        manager.add_position('000001', 2000, 15.0, datetime(2023, 1, 2), 75)
        return manager

    def test_calculate_total_value(self, manager_with_positions):
        """测试计算总资产"""
        prices = {'600000': 11.0, '000001': 14.5}

        # 总资产 = 现金 + 持仓市值
        # 现金: 1000000 - (1000*10+50) - (2000*15+75) = 959875
        # 持仓: 1000*11 + 2000*14.5 = 11000 + 29000 = 40000
        # 总计: 999875
        total_value = manager_with_positions.calculate_total_value(prices)
        assert total_value == 999875

    def test_calculate_total_value_missing_price(self, manager_with_positions):
        """测试计算总资产（缺失价格时使用买入价）"""
        prices = {'600000': 11.0}  # 000001 价格缺失

        # 000001 使用买入价 15.0
        total_value = manager_with_positions.calculate_total_value(prices)
        # 现金 + 1000*11 + 2000*15 = 959875 + 11000 + 30000 = 1000875
        assert total_value == 1000875

    def test_calculate_position_weights(self, manager_with_positions):
        """测试计算持仓权重"""
        prices = {'600000': 11.0, '000001': 14.5}

        weights = manager_with_positions.calculate_position_weights(prices)

        # 总资产: 999875
        # 600000 权重: 11000 / 999875 ≈ 0.011
        # 000001 权重: 29000 / 999875 ≈ 0.029
        assert abs(weights['600000'] - 0.011) < 0.001
        assert abs(weights['000001'] - 0.029) < 0.001

    def test_calculate_position_weights_zero_value(self):
        """测试计算持仓权重（零总资产）"""
        manager = PositionManager(initial_capital=0)
        weights = manager.calculate_position_weights({})
        assert weights == {}

    def test_calculate_available_capital(self, manager_with_positions):
        """测试计算可用资金"""
        prices = {'600000': 11.0, '000001': 14.5}

        # 总资产: 999875
        # 保留: 999875 * 0.05 = 49993.75
        # 现金: 959875
        # 可用: 959875 - 49993.75 = 909881.25
        available = manager_with_positions.calculate_available_capital(prices, reserve_ratio=0.05)
        assert abs(available - 909881.25) < 0.01

    def test_calculate_available_capital_custom_reserve(self, manager_with_positions):
        """测试计算可用资金（自定义保留比例）"""
        prices = {'600000': 11.0, '000001': 14.5}

        # 保留: 999875 * 0.1 = 99987.5
        # 可用: 959875 - 99987.5 = 859887.5
        available = manager_with_positions.calculate_available_capital(prices, reserve_ratio=0.1)
        assert abs(available - 859887.5) < 0.01

    def test_calculate_available_capital_insufficient(self):
        """测试计算可用资金（现金不足）"""
        manager = PositionManager(initial_capital=10000)
        manager.add_position('600000', 900, 10.0, datetime(2023, 1, 1), 0)

        prices = {'600000': 10.0}
        # 现金: 1000, 总资产: 10000, 保留: 500, 可用: 500
        available = manager.calculate_available_capital(prices, reserve_ratio=0.05)
        assert available == 500


# ==================== PositionManager 风险控制测试 ====================

class TestPositionManagerRiskControl:
    """测试 PositionManager 风险控制功能"""

    def test_check_stop_loss_triggered(self):
        """测试止损检查 - 触发止损"""
        manager = PositionManager(
            initial_capital=1000000,
            max_single_loss_pct=0.05  # 5%止损
        )
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)

        # 当前价格9.4，亏损: (9.4-10)*1000-50 = -650
        # 亏损比例: -650 / (10*1000+50) = -0.0647 > -0.05
        prices = {'600000': 9.4}
        stop_loss_stocks = manager.check_stop_loss(prices)

        assert '600000' in stop_loss_stocks

    def test_check_stop_loss_not_triggered(self):
        """测试止损检查 - 未触发止损"""
        manager = PositionManager(
            initial_capital=1000000,
            max_single_loss_pct=0.05
        )
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)

        # 当前价格9.6，亏损比例较小
        prices = {'600000': 9.6}
        stop_loss_stocks = manager.check_stop_loss(prices)

        assert len(stop_loss_stocks) == 0

    def test_check_stop_loss_missing_price(self):
        """测试止损检查 - 价格缺失"""
        manager = PositionManager(
            initial_capital=1000000,
            max_single_loss_pct=0.05
        )
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)

        # 价格缺失
        prices = {}
        stop_loss_stocks = manager.check_stop_loss(prices)

        assert len(stop_loss_stocks) == 0

    def test_check_position_limit_exceeded(self):
        """测试仓位限制检查 - 超限"""
        manager = PositionManager(
            initial_capital=100000,
            max_position_pct=0.2  # 最大20%
        )
        manager.add_position('600000', 3000, 10.0, datetime(2023, 1, 1), 0)

        # 当前价格11，市值33000
        # 总资产: 70000 + 33000 = 103000
        # 权重: 33000/103000 ≈ 0.32 > 0.2
        prices = {'600000': 11.0}
        overlimit_stocks = manager.check_position_limit(prices)

        assert '600000' in overlimit_stocks

    def test_check_position_limit_within(self):
        """测试仓位限制检查 - 未超限"""
        manager = PositionManager(
            initial_capital=100000,
            max_position_pct=0.3
        )
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 0)

        # 权重: 10000/100000 = 0.1 < 0.3
        prices = {'600000': 10.0}
        overlimit_stocks = manager.check_position_limit(prices)

        assert len(overlimit_stocks) == 0


# ==================== PositionManager 摘要测试 ====================

class TestPositionManagerSummary:
    """测试 PositionManager 摘要功能"""

    def test_get_summary(self):
        """测试获取持仓摘要"""
        manager = PositionManager(initial_capital=1000000)
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)
        manager.add_position('000001', 2000, 15.0, datetime(2023, 1, 2), 75)

        prices = {'600000': 11.0, '000001': 14.5}
        summary = manager.get_summary(prices)

        # 验证摘要字段
        assert summary['cash'] == 959875
        assert summary['holdings_value'] == 40000
        assert summary['total_value'] == 999875
        assert summary['position_count'] == 2

        # 总盈亏: (11-10)*1000-50 + (14.5-15)*2000-75 = 950 - 1075 = -125
        assert summary['total_pnl'] == -125

        # 总收益: (999875 - 1000000) / 1000000 = -0.000125
        assert abs(summary['total_return'] + 0.000125) < 0.000001

        # 验证各持仓信息
        assert '600000' in summary['positions']
        pos_600000 = summary['positions']['600000']
        assert pos_600000['shares'] == 1000
        assert pos_600000['entry_price'] == 10.0
        assert pos_600000['current_price'] == 11.0
        assert pos_600000['market_value'] == 11000
        assert pos_600000['pnl'] == 950

    def test_get_summary_empty(self):
        """测试获取空持仓摘要"""
        manager = PositionManager(initial_capital=1000000)
        summary = manager.get_summary({})

        assert summary['cash'] == 1000000
        assert summary['holdings_value'] == 0
        assert summary['total_value'] == 1000000
        assert summary['position_count'] == 0
        assert summary['total_pnl'] == 0
        assert summary['total_return'] == 0
        assert summary['positions'] == {}


# ==================== 边界情况和异常测试 ====================

class TestEdgeCases:
    """测试边界情况"""

    def test_zero_shares_position(self):
        """测试零股数持仓"""
        pos = Position(
            stock_code='600000',
            shares=0,
            entry_price=10.0,
            entry_date=datetime(2023, 1, 1)
        )

        assert pos.market_value(11.0) == 0
        assert pos.profit_loss(11.0) == 0
        assert pos.profit_loss_pct(11.0) == 0

    def test_negative_price(self):
        """测试负价格（理论上不应该存在）"""
        manager = PositionManager(initial_capital=100000)
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 0)

        # 负价格应该正常计算（虽然不符合实际）
        prices = {'600000': -1.0}
        total_value = manager.calculate_total_value(prices)
        assert total_value == 90000 - 1000  # 90000现金 + (-1)*1000

    def test_very_large_position(self):
        """测试超大持仓"""
        manager = PositionManager(initial_capital=1000000000)  # 10亿
        manager.add_position('600000', 10000000, 10.0, datetime(2023, 1, 1), 0)

        prices = {'600000': 10.0}
        total_value = manager.calculate_total_value(prices)
        assert total_value == 1000000000

    def test_multiple_add_remove_same_stock(self):
        """测试同一股票多次买卖"""
        manager = PositionManager(initial_capital=1000000)

        # 买入
        manager.add_position('600000', 1000, 10.0, datetime(2023, 1, 1), 50)
        # 卖出部分
        manager.remove_position('600000', 500, 11.0, 25)
        # 再买入
        manager.add_position('600000', 300, 10.5, datetime(2023, 1, 5), 20)
        # 再卖出
        manager.remove_position('600000', 200, 11.5, 15)

        # 应剩余 500 + 300 - 200 = 600 股
        assert manager.positions['600000'].shares == 600
