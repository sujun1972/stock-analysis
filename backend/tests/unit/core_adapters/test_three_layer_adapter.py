"""
ThreeLayerAdapter 单元测试

测试三层架构适配器的所有功能。

作者: Backend Team
创建日期: 2026-02-06
"""

import sys
from datetime import date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

# 添加项目路径
backend_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core_adapters.three_layer_adapter import ThreeLayerAdapter


@pytest.fixture
def mock_data_adapter():
    """模拟数据适配器"""
    mock = Mock()

    # 模拟 get_stock_list
    mock.get_stock_list = AsyncMock(
        return_value=[
            {"code": "000001", "name": "平安银行"},
            {"code": "000002", "name": "万科A"},
            {"code": "600000", "name": "浦发银行"},
        ]
    )

    # 模拟 get_daily_data
    async def mock_get_daily_data(code, start_date, end_date):
        """返回模拟的日线数据"""
        dates = pd.date_range(start_date, end_date, freq="D")
        df = pd.DataFrame({
            "trade_date": dates,
            "open": [10.0 + i * 0.1 for i in range(len(dates))],
            "high": [10.5 + i * 0.1 for i in range(len(dates))],
            "low": [9.5 + i * 0.1 for i in range(len(dates))],
            "close": [10.2 + i * 0.1 for i in range(len(dates))],
            "volume": [1000000 + i * 1000 for i in range(len(dates))],
        })
        return df

    mock.get_daily_data = mock_get_daily_data

    return mock


@pytest.fixture
def mock_cache():
    """模拟缓存服务"""
    cache_storage = {}

    async def mock_get(key):
        return cache_storage.get(key)

    async def mock_set(key, value, ttl=None):
        cache_storage[key] = value

    async def mock_delete_pattern(pattern):
        pass

    mock = Mock()
    mock.get = mock_get
    mock.set = mock_set
    mock.delete_pattern = mock_delete_pattern

    return mock


@pytest.fixture
def three_layer_adapter(mock_data_adapter, mock_cache):
    """创建三层架构适配器实例"""
    with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
        adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)
        return adapter


@pytest.fixture
def mock_selector():
    """模拟选股器"""
    mock = Mock()
    mock.name = "动量选股器"
    mock.get_metadata = Mock(
        return_value={
            "name": "动量选股器",
            "description": "基于动量因子选股",
            "version": "1.0.0",
            "parameters": [
                {
                    "name": "lookback_period",
                    "label": "回看周期",
                    "type": "integer",
                    "default": 20,
                    "min_value": 5,
                    "max_value": 200,
                }
            ],
        }
    )
    return mock


@pytest.fixture
def mock_entry():
    """模拟入场策略"""
    mock = Mock()
    mock.name = "立即入场"
    mock.get_metadata = Mock(
        return_value={
            "name": "立即入场",
            "description": "选中后立即入场",
            "version": "1.0.0",
            "parameters": [],
        }
    )
    return mock


@pytest.fixture
def mock_exit():
    """模拟退出策略"""
    mock = Mock()
    mock.name = "固定止损"
    mock.get_metadata = Mock(
        return_value={
            "name": "固定止损",
            "description": "固定百分比止损",
            "version": "1.0.0",
            "parameters": [
                {
                    "name": "stop_loss_pct",
                    "label": "止损百分比",
                    "type": "float",
                    "default": -5.0,
                    "min_value": -50.0,
                    "max_value": 0.0,
                }
            ],
        }
    )
    return mock


@pytest.fixture
def mock_backtest_response():
    """模拟回测响应"""
    mock = Mock()
    mock.success = True
    mock.message = "回测完成"
    mock.data = {
        "equity_curve": pd.DataFrame({
            "date": pd.date_range("2023-01-01", periods=10),
            "equity": [1000000 + i * 1000 for i in range(10)],
        }),
        "metrics": {
            "total_return": 0.15,
            "sharpe_ratio": 1.5,
            "max_drawdown": -0.08,
        },
        "trades": pd.DataFrame({
            "date": ["2023-01-05", "2023-01-10"],
            "code": ["000001", "000002"],
            "action": ["buy", "sell"],
            "price": [10.5, 11.2],
        }),
    }
    mock.metadata = {"backtest_type": "three_layer"}
    return mock


class TestThreeLayerAdapter:
    """ThreeLayerAdapter 单元测试类"""

    # ==================== 元数据查询测试 ====================

    @pytest.mark.asyncio
    async def test_get_selectors(self, three_layer_adapter):
        """测试获取选股器列表"""
        # Act
        result = await three_layer_adapter.get_selectors()

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 3  # 至少有momentum, value, external

    @pytest.mark.asyncio
    async def test_get_selectors_cached(self, three_layer_adapter):
        """测试选股器列表缓存"""
        # Act - 第一次调用
        result1 = await three_layer_adapter.get_selectors()

        # Act - 第二次调用（应该命中缓存）
        result2 = await three_layer_adapter.get_selectors()

        # Assert
        assert result1 == result2  # 两次结果应该相同

    @pytest.mark.asyncio
    async def test_get_entries(self, three_layer_adapter):
        """测试获取入场策略列表"""
        # Act
        result = await three_layer_adapter.get_entries()

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 3  # 至少有immediate, ma_breakout, rsi_oversold

    @pytest.mark.asyncio
    async def test_get_exits(self, three_layer_adapter):
        """测试获取退出策略列表"""
        # Act
        result = await three_layer_adapter.get_exits()

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 3  # 至少有fixed_stop_loss, atr_stop_loss, time_based

    # ==================== 策略验证测试 ====================

    @pytest.mark.asyncio
    async def test_validate_strategy_combo_invalid_selector(self, three_layer_adapter):
        """测试验证无效的选股器ID"""
        # Act
        result = await three_layer_adapter.validate_strategy_combo(
            selector_id="invalid_selector",
            selector_params={},
            entry_id="immediate",
            entry_params={},
            exit_id="fixed_stop_loss",
            exit_params={},
            rebalance_freq="W",
        )

        # Assert
        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "未知的选股器" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_validate_strategy_combo_invalid_entry(self, three_layer_adapter):
        """测试验证无效的入场策略ID"""
        # Act
        result = await three_layer_adapter.validate_strategy_combo(
            selector_id="momentum",
            selector_params={},
            entry_id="invalid_entry",
            entry_params={},
            exit_id="fixed_stop_loss",
            exit_params={},
            rebalance_freq="W",
        )

        # Assert
        assert result["valid"] is False
        assert any("未知的入场策略" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_strategy_combo_invalid_exit(self, three_layer_adapter):
        """测试验证无效的退出策略ID"""
        # Act
        result = await three_layer_adapter.validate_strategy_combo(
            selector_id="momentum",
            selector_params={},
            entry_id="immediate",
            entry_params={},
            exit_id="invalid_exit",
            exit_params={},
            rebalance_freq="W",
        )

        # Assert
        assert result["valid"] is False
        assert any("未知的退出策略" in error for error in result["errors"])

    @pytest.mark.asyncio
    async def test_validate_strategy_combo_invalid_rebalance_freq(self, three_layer_adapter):
        """测试验证无效的调仓频率"""
        # Act
        result = await three_layer_adapter.validate_strategy_combo(
            selector_id="momentum",
            selector_params={},
            entry_id="immediate",
            entry_params={},
            exit_id="fixed_stop_loss",
            exit_params={},
            rebalance_freq="X",  # 无效的频率
        )

        # Assert
        assert result["valid"] is False
        # 检查错误列表中是否有关于调仓频率的错误
        error_messages = result.get("errors", [])
        assert len(error_messages) > 0
        # 错误消息可能包含"调仓频率"或"rebalance"
        assert any("调仓" in str(error) or "频率" in str(error) or "rebalance" in str(error).lower() for error in error_messages)

    @pytest.mark.asyncio
    async def test_validate_strategy_combo_valid(
        self, three_layer_adapter, mock_selector, mock_entry, mock_exit
    ):
        """测试验证有效的策略组合"""
        # Arrange
        mock_composer = Mock()
        mock_composer.validate = Mock(return_value={"valid": True, "errors": []})

        with (
            patch.dict(
                three_layer_adapter.SELECTOR_REGISTRY, {"momentum": lambda params: mock_selector}
            ),
            patch.dict(
                three_layer_adapter.ENTRY_REGISTRY, {"immediate": lambda params: mock_entry}
            ),
            patch.dict(
                three_layer_adapter.EXIT_REGISTRY,
                {"fixed_stop_loss": lambda params: mock_exit},
            ),
            patch(
                "app.core_adapters.three_layer_adapter.StrategyComposer",
                return_value=mock_composer,
            ),
        ):
            # Act
            result = await three_layer_adapter.validate_strategy_combo(
                selector_id="momentum",
                selector_params={"lookback_period": 20},
                entry_id="immediate",
                entry_params={},
                exit_id="fixed_stop_loss",
                exit_params={"stop_loss_pct": -5.0},
                rebalance_freq="W",
            )

            # Assert
            assert result["valid"] is True
            assert len(result["errors"]) == 0

    # ==================== 回测执行测试 ====================

    @pytest.mark.asyncio
    async def test_run_backtest_unknown_selector(self, three_layer_adapter):
        """测试回测时使用未知选股器"""
        # Act
        result = await three_layer_adapter.run_backtest(
            selector_id="unknown",
            selector_params={},
            entry_id="immediate",
            entry_params={},
            exit_id="fixed_stop_loss",
            exit_params={},
            rebalance_freq="W",
            start_date="2023-01-01",
            end_date="2023-12-31",
        )

        # Assert
        assert result["success"] is False
        assert "未知的策略ID" in result["error"]

    @pytest.mark.asyncio
    async def test_run_backtest_empty_data(self, mock_data_adapter):
        """测试回测时数据为空"""
        # Arrange - 创建返回空数据的mock
        async def mock_get_daily_data_empty(code, start_date, end_date):
            return pd.DataFrame()

        mock_data_adapter.get_daily_data = mock_get_daily_data_empty

        # 使用简化的适配器（不使用真实的Redis cache）
        cache_storage = {}

        async def mock_cache_get(key):
            return cache_storage.get(key)

        async def mock_cache_set(key, value, ttl=None):
            cache_storage[key] = value

        mock_cache = Mock()
        mock_cache.get = mock_cache_get
        mock_cache.set = mock_cache_set

        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # Act
            result = await adapter.run_backtest(
                selector_id="momentum",
                selector_params={},
                entry_id="immediate",
                entry_params={},
                exit_id="fixed_stop_loss",
                exit_params={},
                rebalance_freq="W",
                start_date="2023-01-01",
                end_date="2023-12-31",
            )

            # Assert
            assert result["success"] is False
            # 错误消息可能是直接的错误或嵌套的错误（包含堆栈信息）
            error_msg = result["error"]
            assert "未找到符合条件的价格数据" in error_msg or "未获取到任何有效的价格数据" in error_msg or "价格数据获取失败" in error_msg

    @pytest.mark.asyncio
    async def test_run_backtest_success(
        self,
        three_layer_adapter,
        mock_data_adapter,
        mock_selector,
        mock_entry,
        mock_exit,
        mock_backtest_response,
    ):
        """测试成功执行回测"""
        # Arrange
        mock_engine = Mock()
        mock_engine.backtest_three_layer = Mock(return_value=mock_backtest_response)

        with (
            patch.dict(
                three_layer_adapter.SELECTOR_REGISTRY, {"momentum": lambda params: mock_selector}
            ),
            patch.dict(
                three_layer_adapter.ENTRY_REGISTRY, {"immediate": lambda params: mock_entry}
            ),
            patch.dict(
                three_layer_adapter.EXIT_REGISTRY,
                {"fixed_stop_loss": lambda params: mock_exit},
            ),
            patch(
                "app.core_adapters.three_layer_adapter.BacktestEngine",
                return_value=mock_engine,
            ),
        ):
            # Act
            result = await three_layer_adapter.run_backtest(
                selector_id="momentum",
                selector_params={"lookback_period": 20},
                entry_id="immediate",
                entry_params={},
                exit_id="fixed_stop_loss",
                exit_params={"stop_loss_pct": -5.0},
                rebalance_freq="W",
                start_date="2023-01-01",
                end_date="2023-01-31",
                initial_capital=1000000.0,
                stock_codes=["000001", "000002"],
            )

            # Assert
            assert result["success"] is True
            assert "data" in result
            mock_engine.backtest_three_layer.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_backtest_cached(self, mock_data_adapter):
        """测试回测结果缓存"""
        # Arrange - 创建简单的内存缓存
        cache_storage = {}

        async def mock_cache_get(key):
            return cache_storage.get(key)

        async def mock_cache_set(key, value, ttl=None):
            cache_storage[key] = value

        mock_cache = Mock()
        mock_cache.get = mock_cache_get
        mock_cache.set = mock_cache_set

        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # 预先设置缓存
            cached_result = {
                "success": True,
                "data": {"metrics": {"total_return": 0.15}},
            }

            cache_key = adapter._generate_cache_key(
                "momentum",
                {"lookback_period": 20},
                "immediate",
                {},
                "fixed_stop_loss",
                {"stop_loss_pct": -5.0},
                "W",
                "2023-01-01",
                "2023-01-31",
                1000000.0,
                None,
            )
            await mock_cache.set(cache_key, cached_result)

            # Act
            result = await adapter.run_backtest(
                selector_id="momentum",
                selector_params={"lookback_period": 20},
                entry_id="immediate",
                entry_params={},
                exit_id="fixed_stop_loss",
                exit_params={"stop_loss_pct": -5.0},
                rebalance_freq="W",
                start_date="2023-01-01",
                end_date="2023-01-31",
                initial_capital=1000000.0,
            )

            # Assert
            assert result == cached_result

    # ==================== 辅助方法测试 ====================

    def test_generate_cache_key(self, three_layer_adapter):
        """测试缓存键生成"""
        # Act
        key1 = three_layer_adapter._generate_cache_key(
            "momentum", {"top_n": 50}, "immediate", {}, "fixed_stop_loss", {}, "W", "2023-01-01"
        )
        key2 = three_layer_adapter._generate_cache_key(
            "momentum", {"top_n": 50}, "immediate", {}, "fixed_stop_loss", {}, "W", "2023-01-01"
        )
        key3 = three_layer_adapter._generate_cache_key(
            "momentum", {"top_n": 100}, "immediate", {}, "fixed_stop_loss", {}, "W", "2023-01-01"
        )

        # Assert
        assert key1 == key2  # 相同参数应生成相同key
        assert key1 != key3  # 不同参数应生成不同key
        assert key1.startswith("three_layer:backtest:")

    def test_convert_response_to_dict_success(self, three_layer_adapter, mock_backtest_response):
        """测试Response对象转换为字典（成功情况）"""
        # Act
        result = three_layer_adapter._convert_response_to_dict(mock_backtest_response)

        # Assert
        assert result["success"] is True
        assert "data" in result
        assert "message" in result
        assert result["message"] == "回测完成"

    def test_convert_response_to_dict_failure(self, three_layer_adapter):
        """测试Response对象转换为字典（失败情况）"""
        # Arrange
        mock_response = Mock()
        mock_response.success = False
        mock_response.error = "回测失败"

        # Act
        result = three_layer_adapter._convert_response_to_dict(mock_response)

        # Assert
        assert result["success"] is False
        assert result["error"] == "回测失败"

    @pytest.mark.asyncio
    async def test_fetch_price_data_with_stock_codes(self, three_layer_adapter, mock_data_adapter):
        """测试获取指定股票池的价格数据"""
        # Act
        result = await three_layer_adapter._fetch_price_data(
            stock_codes=["000001", "000002"],
            start_date="2023-01-01",
            end_date="2023-01-10",
        )

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert not result.empty
        assert "000001" in result.columns or "000002" in result.columns

    @pytest.mark.asyncio
    async def test_fetch_price_data_all_stocks(self, three_layer_adapter, mock_data_adapter):
        """测试获取全市场股票的价格数据"""
        # Act
        result = await three_layer_adapter._fetch_price_data(
            stock_codes=None, start_date="2023-01-01", end_date="2023-01-10"
        )

        # Assert
        assert isinstance(result, pd.DataFrame)
        # 应该调用了 get_stock_list
        mock_data_adapter.get_stock_list.assert_called_once()


# ==================== 集成测试提示 ====================
# 以下测试需要真实的 Core 组件和数据库连接，应放在集成测试中：
# - test_real_selector_metadata
# - test_real_entry_metadata
# - test_real_exit_metadata
# - test_real_strategy_validation
# - test_real_backtest_execution
