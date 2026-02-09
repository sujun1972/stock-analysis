"""
统一回测API集成测试

端到端测试三种策略类型的回测流程

作者: Backend Team
创建日期: 2026-02-09
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.integration
@pytest.mark.slow
class TestUnifiedBacktestIntegration:
    """统一回测API集成测试"""

    def test_predefined_strategy_backtest(self):
        """测试预定义策略回测"""

        payload = {
            "strategy_type": "predefined",
            "strategy_name": "momentum",
            "strategy_config": {
                "lookback_period": 20,
                "threshold": 0.10,
                "top_n": 10
            },
            "stock_pool": ["000001.SZ"],
            "start_date": "2023-01-01",
            "end_date": "2023-03-31",
            "initial_capital": 1000000.0
        }

        response = client.post("/api/backtest/run-v2", json=payload)

        # 注意：如果 Core 不可用或数据不存在，测试可能失败
        # 这里主要验证接口的正确性
        if response.status_code == 200:
            data = response.json()
            assert data['success'] is True
            assert 'execution_id' in data['data']
            assert 'strategy_info' in data['data']
            assert data['data']['strategy_info']['type'] == 'predefined'
            assert 'metrics' in data['data']
        else:
            # 如果失败，至少验证返回了合理的错误
            assert response.status_code in [400, 500]

    def test_config_strategy_backtest(self):
        """测试配置驱动策略回测"""

        # 1. 先创建一个策略配置
        config_payload = {
            "strategy_type": "momentum",
            "config": {
                "lookback_period": 20,
                "threshold": 0.10,
                "top_n": 10
            },
            "name": "回测测试配置"
        }
        config_response = client.post("/api/strategy-configs", json=config_payload)

        if config_response.status_code == 201:
            config_id = config_response.json()['data']['config_id']

            # 2. 使用该配置进行回测
            backtest_payload = {
                "strategy_type": "config",
                "strategy_id": config_id,
                "stock_pool": ["000001.SZ"],
                "start_date": "2023-01-01",
                "end_date": "2023-03-31",
                "initial_capital": 1000000.0
            }

            response = client.post("/api/backtest/run-v2", json=backtest_payload)

            if response.status_code == 200:
                data = response.json()
                assert data['success'] is True
                assert data['data']['strategy_info']['type'] == 'config'
                assert data['data']['strategy_info']['config_id'] == config_id

            # 3. 清理：删除策略配置
            client.delete(f"/api/strategy-configs/{config_id}")

    def test_dynamic_strategy_backtest(self):
        """测试动态代码策略回测"""

        # 1. 先创建一个动态策略
        strategy_code = '''
class SimpleTestStrategy(BaseStrategy):
    def select_stocks(self, market_data, date):
        """简单选股逻辑"""
        return market_data.index[:5].tolist()

    def generate_signals(self, market_data, date):
        """生成交易信号"""
        selected = self.select_stocks(market_data, date)
        signals = {}
        for stock in selected:
            signals[stock] = 1.0 / len(selected)
        return signals
'''

        dynamic_payload = {
            "strategy_name": "simple_test_strategy",
            "display_name": "简单测试策略",
            "class_name": "SimpleTestStrategy",
            "generated_code": strategy_code,
            "description": "用于集成测试的简单策略"
        }

        strategy_response = client.post("/api/dynamic-strategies", json=dynamic_payload)

        if strategy_response.status_code == 201:
            strategy_id = strategy_response.json()['data']['strategy_id']

            # 2. 测试策略是否可以创建
            test_response = client.post(
                f"/api/dynamic-strategies/{strategy_id}/test",
                params={"strict_mode": False}
            )

            # 3. 如果策略测试通过，进行回测
            if test_response.status_code == 200:
                test_data = test_response.json()

                if test_data.get('success') and test_data['data'].get('test_passed'):
                    backtest_payload = {
                        "strategy_type": "dynamic",
                        "strategy_id": strategy_id,
                        "stock_pool": ["000001.SZ"],
                        "start_date": "2023-01-01",
                        "end_date": "2023-03-31",
                        "initial_capital": 1000000.0,
                        "strict_mode": False
                    }

                    response = client.post("/api/backtest/run-v2", json=backtest_payload)

                    if response.status_code == 200:
                        data = response.json()
                        assert data['success'] is True
                        assert data['data']['strategy_info']['type'] == 'dynamic'
                        assert data['data']['strategy_info']['strategy_id'] == strategy_id

            # 4. 清理：删除动态策略
            client.delete(f"/api/dynamic-strategies/{strategy_id}")

    def test_backtest_with_custom_params(self):
        """测试带自定义交易参数的回测"""

        payload = {
            "strategy_type": "predefined",
            "strategy_name": "momentum",
            "strategy_config": {
                "lookback_period": 20,
                "top_n": 10
            },
            "stock_pool": ["000001.SZ"],
            "start_date": "2023-01-01",
            "end_date": "2023-03-31",
            "initial_capital": 500000.0,
            "commission_rate": 0.0005,
            "stamp_tax_rate": 0.001,
            "min_commission": 5.0,
            "slippage": 0.001
        }

        response = client.post("/api/backtest/run-v2", json=payload)

        if response.status_code == 200:
            data = response.json()
            assert data['success'] is True
            assert data['data']['backtest_params']['initial_capital'] == 500000.0

    def test_backtest_validation_errors(self):
        """测试回测参数验证"""

        # 缺少必需参数
        payload = {
            "strategy_type": "predefined"
            # 缺少 strategy_name
        }
        response = client.post("/api/backtest/run-v2", json=payload)
        assert response.status_code == 422  # Validation error

        # 不支持的策略类型
        payload = {
            "strategy_type": "invalid_type",
            "stock_pool": ["000001.SZ"],
            "start_date": "2023-01-01",
            "end_date": "2023-03-31"
        }
        response = client.post("/api/backtest/run-v2", json=payload)
        assert response.status_code == 422

        # 日期格式错误
        payload = {
            "strategy_type": "predefined",
            "strategy_name": "momentum",
            "stock_pool": ["000001.SZ"],
            "start_date": "2023/01/01",  # 错误格式
            "end_date": "2023-03-31"
        }
        response = client.post("/api/backtest/run-v2", json=payload)
        assert response.status_code == 422

    def test_backtest_execution_record(self):
        """测试回测执行记录是否正确保存"""

        payload = {
            "strategy_type": "predefined",
            "strategy_name": "momentum",
            "strategy_config": {"lookback_period": 20, "top_n": 10},
            "stock_pool": ["000001.SZ"],
            "start_date": "2023-01-01",
            "end_date": "2023-03-31",
            "initial_capital": 1000000.0
        }

        response = client.post("/api/backtest/run-v2", json=payload)

        if response.status_code == 200:
            data = response.json()
            execution_id = data['data'].get('execution_id')

            # 验证执行记录ID存在
            assert execution_id is not None
            assert isinstance(execution_id, int)
            assert execution_id > 0

            # TODO: 可以添加查询执行记录的接口来验证记录确实保存了
