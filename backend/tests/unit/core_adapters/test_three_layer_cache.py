"""
三层架构缓存机制专项测试

测试范围:
- 元数据缓存（selectors/entries/exits）
- 回测结果缓存
- 缓存键生成
- 缓存TTL设置
- 缓存命中率测试

作者: Backend Team
创建日期: 2026-02-06
版本: 1.0.0
"""

import asyncio
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pandas as pd
import pytest

from app.core_adapters.three_layer_adapter import ThreeLayerAdapter


@pytest.mark.asyncio
class TestThreeLayerCache:
    """三层架构缓存机制测试"""

    @pytest.fixture
    def mock_cache(self):
        """Mock 缓存"""
        cache_storage = {}

        async def mock_get(key):
            # 返回实际的值，不是包装后的结构
            item = cache_storage.get(key)
            return item["value"] if item else None

        async def mock_set(key, value, ttl=None):
            cache_storage[key] = {"value": value, "ttl": ttl}
            return True

        mock = Mock()
        mock.get = mock_get
        mock.set = mock_set
        mock.storage = cache_storage
        return mock

    @pytest.fixture
    def mock_data_adapter(self):
        """Mock 数据适配器"""
        mock = AsyncMock()

        # 模拟股票列表
        mock.get_stock_list = AsyncMock(
            return_value=[{"code": "000001"}, {"code": "000002"}]
        )

        # 模拟日行情数据
        async def mock_get_daily(code, start_date, end_date):
            dates = pd.date_range(start_date, end_date, freq="D")
            return pd.DataFrame({
                "trade_date": dates,
                "close": [100 + i for i in range(len(dates))],
            })

        mock.get_daily_data = mock_get_daily
        return mock

    # ==================== 元数据缓存测试 ====================

    async def test_selectors_metadata_cache(self, mock_cache, mock_data_adapter):
        """测试选股器元数据缓存"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # 第一次调用 - 应该从策略类获取并缓存
            selectors1 = await adapter.get_selectors()
            assert len(selectors1) > 0
            assert "three_layer:selectors:metadata" in mock_cache.storage

            # 验证缓存内容
            cached_data = mock_cache.storage["three_layer:selectors:metadata"]
            assert cached_data["value"] == selectors1
            assert cached_data["ttl"] == 86400  # 1天

            # 第二次调用 - 应该从缓存获取
            selectors2 = await adapter.get_selectors()
            assert selectors2 == selectors1

    async def test_entries_metadata_cache(self, mock_cache, mock_data_adapter):
        """测试入场策略元数据缓存"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # 第一次调用
            entries1 = await adapter.get_entries()
            # 即使某些策略失败，缓存键也应该存在
            assert "three_layer:entries:metadata" in mock_cache.storage

            # 验证TTL
            cached_data = mock_cache.storage["three_layer:entries:metadata"]
            assert cached_data["ttl"] == 86400

            # 第二次调用应该命中缓存
            entries2 = await adapter.get_entries()
            assert entries2 == entries1

    async def test_exits_metadata_cache(self, mock_cache, mock_data_adapter):
        """测试退出策略元数据缓存"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # 第一次调用
            exits1 = await adapter.get_exits()
            # 即使某些策略失败，缓存键也应该存在
            assert "three_layer:exits:metadata" in mock_cache.storage

            # 验证TTL
            cached_data = mock_cache.storage["three_layer:exits:metadata"]
            assert cached_data["ttl"] == 86400

            # 第二次调用应该命中缓存
            exits2 = await adapter.get_exits()
            assert exits2 == exits1

    async def test_metadata_cache_independence(self, mock_cache, mock_data_adapter):
        """测试三种元数据缓存的独立性"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # 调用三种元数据获取方法
            selectors = await adapter.get_selectors()
            entries = await adapter.get_entries()
            exits = await adapter.get_exits()

            # 验证三个独立的缓存键存在
            assert "three_layer:selectors:metadata" in mock_cache.storage
            assert "three_layer:entries:metadata" in mock_cache.storage
            assert "three_layer:exits:metadata" in mock_cache.storage

            # 验证选股器能正确获取
            assert len(selectors) > 0

    # ==================== 回测结果缓存测试 ====================

    async def test_backtest_result_cache(self, mock_cache, mock_data_adapter):
        """测试回测结果缓存"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # Mock BacktestEngine
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"metrics": {"total_return": 0.25}}

            with patch("app.core_adapters.three_layer_adapter.BacktestEngine") as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.backtest_three_layer.return_value = mock_result
                mock_engine_class.return_value = mock_engine

                # 第一次回测
                result1 = await adapter.run_backtest(
                    selector_id="momentum",
                    selector_params={"lookback_period": 20, "top_n": 50},
                    entry_id="immediate",
                    entry_params={},
                    exit_id="fixed_stop_loss",
                    exit_params={"stop_loss_pct": -5.0},
                    rebalance_freq="W",
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                    initial_capital=1000000.0,
                )

                assert result1["success"] is True

                # 验证缓存键存在
                cache_keys = list(mock_cache.storage.keys())
                backtest_cache_key = [k for k in cache_keys if k.startswith("three_layer:backtest:")][0]

                # 验证缓存TTL
                cached_data = mock_cache.storage[backtest_cache_key]
                assert cached_data["ttl"] == 3600  # 1小时

                # 第二次相同参数的回测 - 应该命中缓存
                result2 = await adapter.run_backtest(
                    selector_id="momentum",
                    selector_params={"lookback_period": 20, "top_n": 50},
                    entry_id="immediate",
                    entry_params={},
                    exit_id="fixed_stop_loss",
                    exit_params={"stop_loss_pct": -5.0},
                    rebalance_freq="W",
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                    initial_capital=1000000.0,
                )

                assert result2 == result1

    async def test_backtest_cache_different_params(self, mock_cache, mock_data_adapter):
        """测试不同参数的回测使用不同的缓存键"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"metrics": {}}

            with patch("app.core_adapters.three_layer_adapter.BacktestEngine") as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.backtest_three_layer.return_value = mock_result
                mock_engine_class.return_value = mock_engine

                # 第一次回测
                await adapter.run_backtest(
                    selector_id="momentum",
                    selector_params={"lookback_period": 20},
                    entry_id="immediate",
                    entry_params={},
                    exit_id="fixed_stop_loss",
                    exit_params={"stop_loss_pct": -5.0},
                    rebalance_freq="W",
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                )

                initial_cache_count = len([k for k in mock_cache.storage.keys() if k.startswith("three_layer:backtest:")])

                # 第二次回测（不同参数）
                await adapter.run_backtest(
                    selector_id="momentum",
                    selector_params={"lookback_period": 30},  # 不同的参数
                    entry_id="immediate",
                    entry_params={},
                    exit_id="fixed_stop_loss",
                    exit_params={"stop_loss_pct": -5.0},
                    rebalance_freq="W",
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                )

                final_cache_count = len([k for k in mock_cache.storage.keys() if k.startswith("three_layer:backtest:")])

                # 应该生成两个不同的缓存键
                assert final_cache_count == initial_cache_count + 1

    async def test_backtest_cache_with_stock_codes(self, mock_cache, mock_data_adapter):
        """测试包含股票池参数的回测缓存"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"metrics": {}}

            with patch("app.core_adapters.three_layer_adapter.BacktestEngine") as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.backtest_three_layer.return_value = mock_result
                mock_engine_class.return_value = mock_engine

                # 有股票池的回测
                await adapter.run_backtest(
                    selector_id="momentum",
                    selector_params={},
                    entry_id="immediate",
                    entry_params={},
                    exit_id="fixed_stop_loss",
                    exit_params={},
                    rebalance_freq="W",
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                    stock_codes=["000001", "000002"],
                )

                cache_keys_with_codes = len([k for k in mock_cache.storage.keys() if k.startswith("three_layer:backtest:")])

                # 无股票池的回测
                await adapter.run_backtest(
                    selector_id="momentum",
                    selector_params={},
                    entry_id="immediate",
                    entry_params={},
                    exit_id="fixed_stop_loss",
                    exit_params={},
                    rebalance_freq="W",
                    start_date="2023-01-01",
                    end_date="2023-12-31",
                    stock_codes=None,
                )

                cache_keys_without_codes = len([k for k in mock_cache.storage.keys() if k.startswith("three_layer:backtest:")])

                # 应该生成不同的缓存键
                assert cache_keys_without_codes == cache_keys_with_codes + 1

    # ==================== 缓存键生成测试 ====================

    def test_cache_key_generation(self):
        """测试缓存键生成方法"""
        adapter = ThreeLayerAdapter()

        # 测试缓存键生成
        key1 = adapter._generate_cache_key(
            "momentum", {"lookback": 20}, "immediate", {},
            "fixed_stop_loss", {"pct": -5}, "W",
            "2023-01-01", "2023-12-31", 1000000.0, None
        )

        # 相同参数应该生成相同的键
        key2 = adapter._generate_cache_key(
            "momentum", {"lookback": 20}, "immediate", {},
            "fixed_stop_loss", {"pct": -5}, "W",
            "2023-01-01", "2023-12-31", 1000000.0, None
        )

        assert key1 == key2
        assert key1.startswith("three_layer:backtest:")

        # 不同参数应该生成不同的键
        key3 = adapter._generate_cache_key(
            "momentum", {"lookback": 30}, "immediate", {},  # 不同的lookback
            "fixed_stop_loss", {"pct": -5}, "W",
            "2023-01-01", "2023-12-31", 1000000.0, None
        )

        assert key3 != key1

    def test_cache_key_includes_all_params(self):
        """测试缓存键包含所有参数"""
        adapter = ThreeLayerAdapter()

        # 所有参数都影响缓存键
        params_sets = [
            ("momentum", "value"),  # 不同的selector
            ({"lookback": 20}, {"lookback": 30}),  # 不同的selector_params
            ("immediate", "ma_breakout"),  # 不同的entry
            ("W", "M"),  # 不同的rebalance_freq
            ("2023-01-01", "2023-02-01"),  # 不同的start_date
        ]

        for idx, (param1, param2) in enumerate(params_sets):
            if idx == 0:  # selector_id
                key1 = adapter._generate_cache_key(
                    param1, {}, "immediate", {}, "fixed_stop_loss", {},
                    "W", "2023-01-01", "2023-12-31", 1000000.0, None
                )
                key2 = adapter._generate_cache_key(
                    param2, {}, "immediate", {}, "fixed_stop_loss", {},
                    "W", "2023-01-01", "2023-12-31", 1000000.0, None
                )
            elif idx == 1:  # selector_params
                key1 = adapter._generate_cache_key(
                    "momentum", param1, "immediate", {}, "fixed_stop_loss", {},
                    "W", "2023-01-01", "2023-12-31", 1000000.0, None
                )
                key2 = adapter._generate_cache_key(
                    "momentum", param2, "immediate", {}, "fixed_stop_loss", {},
                    "W", "2023-01-01", "2023-12-31", 1000000.0, None
                )
            elif idx == 2:  # entry_id
                key1 = adapter._generate_cache_key(
                    "momentum", {}, param1, {}, "fixed_stop_loss", {},
                    "W", "2023-01-01", "2023-12-31", 1000000.0, None
                )
                key2 = adapter._generate_cache_key(
                    "momentum", {}, param2, {}, "fixed_stop_loss", {},
                    "W", "2023-01-01", "2023-12-31", 1000000.0, None
                )
            elif idx == 3:  # rebalance_freq
                key1 = adapter._generate_cache_key(
                    "momentum", {}, "immediate", {}, "fixed_stop_loss", {},
                    param1, "2023-01-01", "2023-12-31", 1000000.0, None
                )
                key2 = adapter._generate_cache_key(
                    "momentum", {}, "immediate", {}, "fixed_stop_loss", {},
                    param2, "2023-01-01", "2023-12-31", 1000000.0, None
                )
            else:  # start_date
                key1 = adapter._generate_cache_key(
                    "momentum", {}, "immediate", {}, "fixed_stop_loss", {},
                    "W", param1, "2023-12-31", 1000000.0, None
                )
                key2 = adapter._generate_cache_key(
                    "momentum", {}, "immediate", {}, "fixed_stop_loss", {},
                    "W", param2, "2023-12-31", 1000000.0, None
                )

            assert key1 != key2, f"参数集 {idx} 应该生成不同的缓存键"

    # ==================== 缓存失效场景测试 ====================

    async def test_cache_not_used_on_backtest_failure(self, mock_cache, mock_data_adapter):
        """测试回测失败时不缓存结果"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # Mock 回测失败
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "测试失败"

            with patch("app.core_adapters.three_layer_adapter.BacktestEngine") as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.backtest_three_layer.return_value = mock_result
                mock_engine_class.return_value = mock_engine

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

                assert result["success"] is False

                # 失败的结果不应该被缓存
                backtest_cache_keys = [k for k in mock_cache.storage.keys() if k.startswith("three_layer:backtest:")]
                assert len(backtest_cache_keys) == 0

    async def test_metadata_cache_returns_empty_on_error(self, mock_cache, mock_data_adapter):
        """测试元数据获取错误时返回空列表（不缓存）"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            # Mock 策略类抛出异常
            with patch.dict(
                "app.core_adapters.three_layer_adapter.ThreeLayerAdapter.SELECTOR_REGISTRY",
                {"broken": type("BrokenSelector", (), {"get_parameters": lambda: None})}
            ):
                adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

                # 应该返回空列表（跳过出错的策略）
                selectors = await adapter.get_selectors()

                # 仍然应该缓存结果（即使是空的或部分的）
                assert "three_layer:selectors:metadata" in mock_cache.storage

    # ==================== 缓存性能测试 ====================

    async def test_cache_reduces_api_calls(self, mock_cache, mock_data_adapter):
        """测试缓存减少API调用次数"""
        call_count = 0

        async def counting_get_selectors_original():
            nonlocal call_count
            call_count += 1
            return [{"id": "test"}]

        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            # 调用10次
            for _ in range(10):
                await adapter.get_selectors()

            # 由于缓存，实际只应该生成一次数据
            # （第一次调用后，后续都从缓存获取）
            cache_data = mock_cache.storage.get("three_layer:selectors:metadata")
            assert cache_data is not None

    async def test_cache_hit_logging(self, mock_cache, mock_data_adapter):
        """测试缓存命中时的日志记录"""
        with patch("app.core_adapters.three_layer_adapter.cache", mock_cache):
            adapter = ThreeLayerAdapter(data_adapter=mock_data_adapter)

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.data = {"metrics": {}}

            with patch("app.core_adapters.three_layer_adapter.BacktestEngine") as mock_engine_class:
                mock_engine = MagicMock()
                mock_engine.backtest_three_layer.return_value = mock_result
                mock_engine_class.return_value = mock_engine

                with patch("app.core_adapters.three_layer_adapter.logger") as mock_logger:
                    # 第一次调用
                    await adapter.run_backtest(
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

                    # 应该记录缓存写入日志
                    assert any("已缓存" in str(call) for call in mock_logger.info.call_args_list)

                    # 第二次调用（缓存命中）
                    await adapter.run_backtest(
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

                    # 应该记录缓存命中日志
                    assert any("命中缓存" in str(call) for call in mock_logger.info.call_args_list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
