"""
ML策略回测集成测试

测试MLEntry与BacktestEngine的集成
验证完整的ML策略回测工作流

版本: v1.0.0
创建时间: 2026-02-08
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

from src.ml.feature_engine import FeatureEngine
from src.ml.label_generator import LabelGenerator
from src.ml.trained_model import TrainedModel, TrainingConfig
from src.ml.ml_entry import MLEntry
from src.backtest.backtest_engine import BacktestEngine


class TestMLBacktestIntegration:
    """ML策略回测集成测试"""

    @pytest.fixture
    def market_data(self):
        """生成模拟市场数据"""
        np.random.seed(42)

        stocks = ['600000.SH', '600001.SH', '600002.SH', '600003.SH', '600004.SH']
        dates = pd.date_range('2023-01-01', '2023-12-31', freq='D')

        data_list = []

        for stock in stocks:
            # 生成模拟价格走势
            base_price = 10.0 + np.random.rand() * 10
            prices = [base_price]

            for _ in range(len(dates) - 1):
                # 随机游走
                change = np.random.randn() * 0.02
                new_price = prices[-1] * (1 + change)
                prices.append(max(new_price, 1.0))  # 价格不低于1元

            for i, date in enumerate(dates):
                price = prices[i]
                data_list.append({
                    'date': date,
                    'stock_code': stock,
                    'open': price * (1 + np.random.randn() * 0.01),
                    'high': price * (1 + abs(np.random.randn()) * 0.02),
                    'low': price * (1 - abs(np.random.randn()) * 0.02),
                    'close': price,
                    'volume': int(1000000 + np.random.rand() * 500000)
                })

        df = pd.DataFrame(data_list)
        df['date'] = pd.to_datetime(df['date'])
        return df

    @pytest.fixture
    def trained_model(self, market_data):
        """创建并训练一个简单的模型"""
        # 1. 特征引擎
        feature_engine = FeatureEngine(
            feature_groups=['technical'],
            lookback_window=60
        )

        # 2. 训练一个简单的sklearn模型
        from sklearn.linear_model import Ridge

        # 生成训练数据
        stocks = ['600000.SH', '600001.SH']
        train_date = '2023-06-01'

        features = feature_engine.calculate_features(
            stock_codes=stocks,
            market_data=market_data,
            date=train_date
        )

        # 生成标签 (模拟)
        labels = pd.Series([0.05, -0.02], index=stocks, name='label')

        # 训练模型
        X = features.fillna(0).replace([np.inf, -np.inf], 0)
        y = labels

        model = Ridge(alpha=1.0)
        model.fit(X.values, y.values)

        # 创建TrainingConfig
        config = TrainingConfig(
            model_type='ridge',
            train_start_date='2023-01-01',
            train_end_date='2023-06-30',
            forward_window=5,
            feature_groups=['technical']
        )

        # 创建TrainedModel
        trained = TrainedModel(
            model=model,
            feature_engine=feature_engine,
            config=config,
            metrics={'ic': 0.08}
        )

        # 设置特征列
        trained.set_feature_columns(X.columns.tolist())

        return trained

    @pytest.fixture
    def temp_model_path(self, trained_model):
        """保存模型到临时文件"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            model_path = f.name

        trained_model.save(model_path)

        yield model_path

        # 清理
        if os.path.exists(model_path):
            os.remove(model_path)

    def test_01_backtest_ml_strategy_basic(self, market_data, temp_model_path):
        """测试1: 基本ML策略回测"""
        print("\n=== 测试1: 基本ML策略回测 ===")

        # 1. 创建ML策略
        ml_entry = MLEntry(
            model_path=temp_model_path,
            confidence_threshold=0.5,
            top_long=3,
            top_short=0,
            enable_short=False
        )

        # 2. 创建回测引擎
        engine = BacktestEngine(
            initial_capital=1000000.0,
            commission_rate=0.0003,
            slippage=0.001
        )

        # 3. 执行回测
        stock_pool = ['600000.SH', '600001.SH', '600002.SH', '600003.SH', '600004.SH']

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-07-01',
            end_date='2023-12-31',
            rebalance_freq='W'  # 周度调仓
        )

        # 4. 验证结果
        assert result.success, f"回测失败: {result.message}"
        assert 'portfolio_value' in result.data
        assert 'daily_returns' in result.data
        assert 'positions' in result.data
        assert 'metrics' in result.data

        # 验证净值曲线
        portfolio_value = result.data['portfolio_value']
        assert len(portfolio_value) > 0
        assert 'total' in portfolio_value.columns
        assert portfolio_value['total'].iloc[0] > 0

        # 验证绩效指标
        metrics = result.data['metrics']
        assert 'total_return' in metrics
        assert 'annual_return' in metrics
        assert 'sharpe_ratio' in metrics
        assert 'max_drawdown' in metrics

        print(f"✓ 回测完成: {len(portfolio_value)}天")
        print(f"✓ 总收益率: {metrics['total_return']:.2%}")
        print(f"✓ 年化收益: {metrics['annual_return']:.2%}")
        print(f"✓ 夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"✓ 最大回撤: {metrics['max_drawdown']:.2%}")

    def test_02_backtest_ml_strategy_with_short(self, market_data, temp_model_path):
        """测试2: 带做空的ML策略回测"""
        print("\n=== 测试2: 带做空的ML策略回测 ===")

        # 创建支持做空的ML策略
        ml_entry = MLEntry(
            model_path=temp_model_path,
            confidence_threshold=0.5,
            top_long=2,
            top_short=2,
            enable_short=True
        )

        engine = BacktestEngine(initial_capital=1000000.0)
        stock_pool = ['600000.SH', '600001.SH', '600002.SH', '600003.SH']

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-07-01',
            end_date='2023-09-30',
            rebalance_freq='W'
        )

        assert result.success

        portfolio_value = result.data['portfolio_value']

        # 验证包含多空持仓
        assert 'long_value' in portfolio_value.columns
        assert 'short_value' in portfolio_value.columns

        print(f"✓ 多空策略回测完成")
        print(f"✓ 最终多头价值: {portfolio_value['long_value'].iloc[-1]:,.0f}")
        print(f"✓ 最终空头价值: {portfolio_value['short_value'].iloc[-1]:,.0f}")

    def test_03_backtest_different_rebalance_freq(self, market_data, temp_model_path):
        """测试3: 不同调仓频率"""
        print("\n=== 测试3: 不同调仓频率 ===")

        ml_entry = MLEntry(
            model_path=temp_model_path,
            confidence_threshold=0.5,
            top_long=3
        )

        stock_pool = ['600000.SH', '600001.SH', '600002.SH']

        # 测试日度调仓
        engine_daily = BacktestEngine(initial_capital=1000000.0)
        result_daily = engine_daily.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-10-01',
            end_date='2023-10-31',
            rebalance_freq='D'
        )

        # 测试周度调仓
        engine_weekly = BacktestEngine(initial_capital=1000000.0)
        result_weekly = engine_weekly.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-10-01',
            end_date='2023-10-31',
            rebalance_freq='W'
        )

        assert result_daily.success
        assert result_weekly.success

        print(f"✓ 日度调仓完成")
        print(f"✓ 周度调仓完成")

    def test_04_backtest_with_cost_analysis(self, market_data, temp_model_path):
        """测试4: 成本分析"""
        print("\n=== 测试4: 成本分析 ===")

        ml_entry = MLEntry(
            model_path=temp_model_path,
            confidence_threshold=0.5,
            top_long=3
        )

        engine = BacktestEngine(
            initial_capital=1000000.0,
            commission_rate=0.0003,
            stamp_tax_rate=0.001,
            slippage=0.001
        )

        stock_pool = ['600000.SH', '600001.SH', '600002.SH']

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-07-01',
            end_date='2023-12-31',
            rebalance_freq='W'
        )

        assert result.success
        assert 'cost_analysis' in result.data

        cost_analysis = result.data['cost_analysis']

        # 验证成本指标
        assert 'total_commission' in cost_analysis
        assert 'total_slippage' in cost_analysis

        print(f"✓ 成本分析完成")
        print(f"✓ 总佣金: {cost_analysis.get('total_commission', 0):,.2f}")
        print(f"✓ 总滑点: {cost_analysis.get('total_slippage', 0):,.2f}")

    def test_05_backtest_empty_signals(self, market_data, temp_model_path):
        """测试5: 空信号处理"""
        print("\n=== 测试5: 空信号处理 ===")

        # 创建极高置信度阈值的策略（可能产生空信号）
        ml_entry = MLEntry(
            model_path=temp_model_path,
            confidence_threshold=0.99,  # 极高阈值
            top_long=10
        )

        engine = BacktestEngine(initial_capital=1000000.0)
        stock_pool = ['600000.SH', '600001.SH']

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-07-01',
            end_date='2023-07-31',
            rebalance_freq='W'
        )

        # 应该成功完成，即使有些调仓日没有信号
        assert result.success

        print(f"✓ 空信号处理测试通过")

    def test_06_backtest_performance_metrics(self, market_data, temp_model_path):
        """测试6: 绩效指标计算"""
        print("\n=== 测试6: 绩效指标计算 ===")

        ml_entry = MLEntry(
            model_path=temp_model_path,
            confidence_threshold=0.5,
            top_long=3
        )

        engine = BacktestEngine(initial_capital=1000000.0)
        stock_pool = ['600000.SH', '600001.SH', '600002.SH', '600003.SH']

        result = engine.backtest_ml_strategy(
            ml_entry=ml_entry,
            stock_pool=stock_pool,
            market_data=market_data,
            start_date='2023-07-01',
            end_date='2023-12-31',
            rebalance_freq='W'
        )

        metrics = result.data['metrics']

        # 验证所有必要指标存在
        required_metrics = [
            'total_return', 'annual_return', 'volatility',
            'sharpe_ratio', 'max_drawdown', 'win_rate', 'n_days'
        ]

        for metric in required_metrics:
            assert metric in metrics, f"缺少指标: {metric}"
            assert isinstance(metrics[metric], (int, float)), f"指标类型错误: {metric}"

        # 验证指标范围
        assert -1 <= metrics['max_drawdown'] <= 0
        assert 0 <= metrics['win_rate'] <= 1
        assert metrics['n_days'] > 0

        print(f"✓ 绩效指标验证通过")
        print(f"  - 总收益率: {metrics['total_return']:.2%}")
        print(f"  - 年化收益: {metrics['annual_return']:.2%}")
        print(f"  - 波动率: {metrics['volatility']:.2%}")
        print(f"  - 夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"  - 最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"  - 胜率: {metrics['win_rate']:.2%}")

    def test_07_complete_ml_backtest_workflow(self, market_data):
        """测试7: 完整ML回测工作流 (端到端)"""
        print("\n=== 测试7: 完整ML回测工作流 ===")

        # 1. 特征工程
        print("步骤1: 计算特征...")
        feature_engine = FeatureEngine(
            feature_groups=['technical'],
            lookback_window=60
        )

        stocks = ['600000.SH', '600001.SH', '600002.SH']
        features = feature_engine.calculate_features(
            stock_codes=stocks,
            market_data=market_data,
            date='2023-06-01'
        )
        assert len(features) > 0
        print(f"✓ 特征计算完成: {features.shape}")

        # 2. 标签生成
        print("步骤2: 生成标签...")
        label_generator = LabelGenerator(
            forward_window=5,
            label_type='return'
        )
        labels = label_generator.generate_labels(
            stock_codes=stocks,
            market_data=market_data,
            date='2023-06-01'
        )
        assert len(labels) > 0
        print(f"✓ 标签生成完成: {len(labels)}个")

        # 3. 模型训练
        print("步骤3: 训练模型...")
        from sklearn.linear_model import Ridge

        X = features.fillna(0).replace([np.inf, -np.inf], 0)
        y = labels

        model = Ridge(alpha=1.0)
        model.fit(X.values, y.values)
        print(f"✓ 模型训练完成")

        # 4. 封装模型
        print("步骤4: 封装模型...")
        config = TrainingConfig(
            model_type='ridge',
            train_start_date='2023-01-01',
            train_end_date='2023-06-30',
            forward_window=5
        )

        trained_model = TrainedModel(
            model=model,
            feature_engine=feature_engine,
            config=config,
            metrics={'ic': 0.08}
        )
        trained_model.set_feature_columns(X.columns.tolist())
        print(f"✓ 模型封装完成")

        # 5. 保存模型
        print("步骤5: 保存模型...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as f:
            model_path = f.name
        trained_model.save(model_path)
        print(f"✓ 模型已保存")

        try:
            # 6. 创建ML策略
            print("步骤6: 创建ML策略...")
            ml_entry = MLEntry(
                model_path=model_path,
                confidence_threshold=0.5,
                top_long=2,
                enable_short=False
            )
            print(f"✓ ML策略创建完成")

            # 7. 回测
            print("步骤7: 执行回测...")
            engine = BacktestEngine(initial_capital=1000000.0)

            result = engine.backtest_ml_strategy(
                ml_entry=ml_entry,
                stock_pool=stocks,
                market_data=market_data,
                start_date='2023-07-01',
                end_date='2023-12-31',
                rebalance_freq='W'
            )

            assert result.success
            print(f"✓ 回测完成")

            # 8. 验证结果
            print("步骤8: 验证结果...")
            assert 'portfolio_value' in result.data
            assert 'metrics' in result.data

            metrics = result.data['metrics']
            print(f"\n=== 最终绩效 ===")
            print(f"总收益率: {metrics['total_return']:.2%}")
            print(f"年化收益: {metrics['annual_return']:.2%}")
            print(f"夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"✓ 端到端工作流验证通过")

        finally:
            # 清理
            if os.path.exists(model_path):
                os.remove(model_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
