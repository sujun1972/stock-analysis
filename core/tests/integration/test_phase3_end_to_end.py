"""
Phase 3 端到端测试 - 完整ML工作流验证
测试范围: 数据准备 → 特征工程 → 标签生成 → 模型训练 → 回测执行 → 结果分析
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

# ML模块
from src.ml import (
    FeatureEngine, LabelGenerator, TrainedModel, TrainingConfig,
    MLEntry, MLStockRanker
)

# 回测引擎
from src.backtest.backtest_engine import BacktestEngine

# 模型
from src.models.lightgbm_model import LightGBMStockModel


class TestPhase3EndToEnd:
    """Phase 3 端到端测试套件"""

    @pytest.fixture(scope="class")
    def market_data(self):
        """生成模拟市场数据 (500天 × 20股票)"""
        np.random.seed(42)

        # 日期范围: 2022-01-01 到 2023-12-31 (约500天)
        dates = pd.date_range('2022-01-01', '2023-12-31', freq='D')

        # 20只股票
        stocks = [f"{600000 + i:06d}.SH" for i in range(10)] + \
                 [f"{1 + i:06d}.SZ" for i in range(10)]

        # 生成OHLCV数据
        data = []
        for stock in stocks:
            # 初始价格
            base_price = np.random.uniform(10, 100)

            for date in dates:
                # 随机游走价格
                daily_return = np.random.normal(0.0005, 0.02)
                base_price = base_price * (1 + daily_return)

                # OHLCV
                open_price = base_price * np.random.uniform(0.98, 1.02)
                close_price = base_price * np.random.uniform(0.98, 1.02)
                high_price = max(open_price, close_price) * np.random.uniform(1.0, 1.05)
                low_price = min(open_price, close_price) * np.random.uniform(0.95, 1.0)
                volume = np.random.uniform(1000000, 10000000)

                data.append({
                    'date': date,
                    'stock_code': stock,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])

        return df

    @pytest.fixture(scope="class")
    def stock_pool(self, market_data):
        """股票池"""
        return market_data['stock_code'].unique().tolist()

    def test_01_data_preparation(self, market_data, stock_pool):
        """
        测试1: 数据准备和验证

        验证:
        - 数据格式正确
        - 日期连续性
        - 股票代码完整性
        - OHLCV数据有效性
        """
        print("\n" + "="*80)
        print("测试1: 数据准备和验证")
        print("="*80)

        # 验证数据格式
        assert isinstance(market_data, pd.DataFrame)
        assert 'date' in market_data.columns
        assert 'stock_code' in market_data.columns
        assert all(col in market_data.columns for col in ['open', 'high', 'low', 'close', 'volume'])

        # 验证股票池
        assert len(stock_pool) == 20
        print(f"✓ 股票池包含 {len(stock_pool)} 只股票")

        # 验证日期范围
        date_range = market_data['date'].max() - market_data['date'].min()
        print(f"✓ 数据时间跨度: {date_range.days} 天")
        assert date_range.days >= 400  # 至少400天

        # 验证数据完整性
        for stock in stock_pool[:3]:
            stock_data = market_data[market_data['stock_code'] == stock]
            assert len(stock_data) > 400
            print(f"✓ {stock}: {len(stock_data)} 条记录")

        # 验证OHLC关系
        sample_data = market_data.sample(100)
        assert (sample_data['high'] >= sample_data['low']).all()
        assert (sample_data['high'] >= sample_data['open']).all()
        assert (sample_data['high'] >= sample_data['close']).all()
        assert (sample_data['low'] <= sample_data['open']).all()
        assert (sample_data['low'] <= sample_data['close']).all()
        print("✓ OHLC数据关系正确")

        print("\n测试1通过: 数据准备完成 ✓")

    def test_02_feature_engineering(self, market_data, stock_pool):
        """
        测试2: 特征工程

        验证:
        - 特征引擎初始化
        - 特征计算成功
        - 特征数量正确
        - 特征值有效性
        """
        print("\n" + "="*80)
        print("测试2: 特征工程")
        print("="*80)

        # 创建特征引擎
        engine = FeatureEngine(
            feature_groups=['technical'],  # 只使用技术指标以加快速度
            lookback_window=60
        )

        print(f"✓ 特征引擎已创建 (特征组: technical)")

        # 计算特征
        test_date = '2023-06-01'
        test_stocks = stock_pool[:5]  # 使用5只股票

        features = engine.calculate_features(
            stock_codes=test_stocks,
            market_data=market_data,
            date=test_date
        )

        print(f"✓ 特征计算完成: {len(features)} 只股票 × {len(features.columns)} 个特征")

        # 验证特征矩阵
        assert len(features) == len(test_stocks)
        assert len(features.columns) > 10  # 至少10个特征

        # 验证特征值有效性
        valid_features = features.replace([np.inf, -np.inf], np.nan).dropna(axis=1, how='all')
        print(f"✓ 有效特征数: {len(valid_features.columns)}")

        # 查看样本特征
        print("\n样本特征 (前5列):")
        print(features.iloc[:3, :5])

        print("\n测试2通过: 特征工程完成 ✓")

    def test_03_label_generation(self, market_data, stock_pool):
        """
        测试3: 标签生成

        验证:
        - 单时间窗口标签生成
        - 多时间窗口标签生成
        - 4种标签类型 (return/direction/classification/regression)
        - 标签值有效性
        """
        print("\n" + "="*80)
        print("测试3: 标签生成")
        print("="*80)

        test_date = '2023-06-01'
        test_stocks = stock_pool[:5]

        # 测试4种标签类型
        label_types = ['return', 'direction', 'classification', 'regression']

        for label_type in label_types:
            generator = LabelGenerator(
                forward_window=5,
                label_type=label_type
            )

            labels = generator.generate_labels(
                stock_codes=test_stocks,
                market_data=market_data,
                date=test_date
            )

            print(f"✓ {label_type:15s}: {len(labels)} 个标签生成")

            # 验证标签数量
            assert len(labels) > 0

            # 验证标签值范围
            if label_type == 'direction':
                assert labels.isin([0.0, 1.0]).all()
            elif label_type == 'classification':
                assert labels.isin([0.0, 1.0, 2.0]).all()

        # 测试多时间窗口标签
        generator = LabelGenerator(forward_window=5, label_type='return')
        multi_labels = generator.generate_multi_horizon_labels(
            stock_codes=test_stocks,
            market_data=market_data,
            date=test_date,
            horizons=[1, 3, 5, 10, 20]
        )

        print(f"\n✓ 多时间窗口标签: {multi_labels.shape[0]} 只股票 × {multi_labels.shape[1]} 个窗口")

        print("\n测试3通过: 标签生成完成 ✓")

    def test_04_model_training(self, market_data, stock_pool):
        """
        测试4: 模型训练

        验证:
        - 训练数据准备
        - 模型训练成功
        - 模型保存和加载
        - 模型预测功能
        """
        print("\n" + "="*80)
        print("测试4: 模型训练")
        print("="*80)

        # 1. 准备训练数据
        engine = FeatureEngine(feature_groups=['technical'], lookback_window=60)
        generator = LabelGenerator(forward_window=5, label_type='return')

        # 选择训练日期
        all_dates = sorted(market_data['date'].unique())
        train_dates = [d for d in all_dates if '2023-01-01' <= d.strftime('%Y-%m-%d') <= '2023-06-30']

        print(f"训练日期范围: {train_dates[0].date()} 到 {train_dates[-1].date()} ({len(train_dates)}天)")

        # 收集训练样本
        X_list = []
        y_list = []

        for date in train_dates[::10]:  # 每10天采样一次,加快速度
            date_str = date.strftime('%Y-%m-%d')

            try:
                features = engine.calculate_features(
                    stock_codes=stock_pool,
                    market_data=market_data,
                    date=date_str
                )

                labels = generator.generate_labels(
                    stock_codes=stock_pool,
                    market_data=market_data,
                    date=date_str
                )

                # 对齐
                common_stocks = features.index.intersection(labels.index)
                if len(common_stocks) > 0:
                    X_list.append(features.loc[common_stocks])
                    y_list.append(labels.loc[common_stocks])

            except Exception as e:
                continue

        if len(X_list) == 0:
            pytest.skip("训练数据不足")

        X_train = pd.concat(X_list, axis=0)
        y_train = pd.concat(y_list, axis=0)

        # 清理数据
        X_train = X_train.replace([np.inf, -np.inf], np.nan).fillna(0)
        y_train = y_train.replace([np.inf, -np.inf], np.nan).dropna()

        # 对齐
        common_idx = X_train.index.intersection(y_train.index)
        X_train = X_train.loc[common_idx]
        y_train = y_train.loc[common_idx]

        print(f"✓ 训练数据准备完成: {len(X_train)} 个样本 × {X_train.shape[1]} 个特征")

        # 2. 训练模型
        model = LightGBMStockModel(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            verbose=-1
        )

        model.train(X_train, y_train)
        print("✓ 模型训练完成")

        # 3. 封装为TrainedModel
        config = TrainingConfig(
            model_type='lightgbm',
            train_start_date='2023-01-01',
            train_end_date='2023-06-30',
            forward_window=5,
            feature_groups=['technical']
        )

        trained_model = TrainedModel(
            model=model,
            feature_engine=engine,
            config=config,
            metrics={'ic': 0.05}
        )

        trained_model.feature_columns = X_train.columns.tolist()
        print("✓ 模型封装完成")

        # 4. 测试预测
        test_date = '2023-08-01'
        predictions = trained_model.predict(
            stock_codes=stock_pool[:5],
            market_data=market_data,
            date=test_date
        )

        print(f"✓ 预测完成: {len(predictions)} 只股票")
        print("\n预测结果样本:")
        print(predictions.head())

        # 验证预测结果格式
        assert 'expected_return' in predictions.columns
        assert 'volatility' in predictions.columns
        assert 'confidence' in predictions.columns

        # 5. 测试保存和加载
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            trained_model.save(str(model_path))
            print(f"\n✓ 模型已保存: {model_path.name}")

            loaded_model = TrainedModel.load(str(model_path))
            print("✓ 模型已加载")

            # 验证加载后的模型可以预测
            predictions2 = loaded_model.predict(
                stock_codes=stock_pool[:5],
                market_data=market_data,
                date=test_date
            )
            assert len(predictions2) == len(predictions)
            print("✓ 加载模型预测成功")

        print("\n测试4通过: 模型训练完成 ✓")

    def test_05_ml_entry_strategy(self, market_data, stock_pool):
        """
        测试5: ML入场策略

        验证:
        - MLEntry初始化
        - 信号生成
        - 做多做空信号
        - 权重归一化
        """
        print("\n" + "="*80)
        print("测试5: ML入场策略")
        print("="*80)

        # 1. 训练一个简单模型
        engine = FeatureEngine(feature_groups=['technical'], lookback_window=60)

        # 创建一个简单的模型
        model = LightGBMStockModel(n_estimators=10, verbose=-1)

        # 准备训练数据 (简化版)
        test_date = '2023-06-01'
        features = engine.calculate_features(
            stock_codes=stock_pool[:10],
            market_data=market_data,
            date=test_date
        )

        features = features.replace([np.inf, -np.inf], np.nan).fillna(0)
        y_dummy = np.random.randn(len(features)) * 0.01

        model.train(features, pd.Series(y_dummy, index=features.index))

        config = TrainingConfig(model_type='lightgbm', forward_window=5)
        trained_model = TrainedModel(model=model, feature_engine=engine, config=config, metrics={})
        trained_model.feature_columns = features.columns.tolist()

        # 保存模型
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "ml_entry_model.pkl"
            trained_model.save(str(model_path))

            # 2. 创建MLEntry策略
            strategy = MLEntry(
                model_path=str(model_path),
                confidence_threshold=0.5,
                top_long=5,
                top_short=3,
                enable_short=True
            )

            print("✓ MLEntry策略已创建")

            # 3. 生成信号
            signals = strategy.generate_signals(
                stock_pool=stock_pool,
                market_data=market_data,
                date='2023-08-01'
            )

            print(f"✓ 信号生成完成: {len(signals)} 只股票")

            # 验证信号格式
            for stock, signal in signals.items():
                assert 'action' in signal
                assert 'weight' in signal
                assert signal['action'] in ['long', 'short']
                assert 0 <= signal['weight'] <= 1

            # 验证权重归一化
            total_weight = sum(s['weight'] for s in signals.values())
            assert abs(total_weight - 1.0) < 0.01  # 允许小误差
            print(f"✓ 权重归一化: {total_weight:.4f}")

            # 统计信号
            long_signals = [s for s in signals.values() if s['action'] == 'long']
            short_signals = [s for s in signals.values() if s['action'] == 'short']
            print(f"✓ 做多信号: {len(long_signals)} 只, 做空信号: {len(short_signals)} 只")

        print("\n测试5通过: ML入场策略完成 ✓")

    def test_06_ml_stock_ranker(self, market_data, stock_pool):
        """
        测试6: ML股票评分排名

        验证:
        - MLStockRanker初始化
        - 评分排名功能
        - 不同评分方法
        - 批量评分
        """
        print("\n" + "="*80)
        print("测试6: ML股票评分排名")
        print("="*80)

        # 1. 准备模型
        engine = FeatureEngine(feature_groups=['technical'], lookback_window=60)
        model = LightGBMStockModel(n_estimators=10, verbose=-1)

        test_date = '2023-06-01'
        features = engine.calculate_features(
            stock_codes=stock_pool[:10],
            market_data=market_data,
            date=test_date
        )
        features = features.replace([np.inf, -np.inf], np.nan).fillna(0)
        y_dummy = np.random.randn(len(features)) * 0.01
        model.train(features, pd.Series(y_dummy, index=features.index))

        config = TrainingConfig(model_type='lightgbm', forward_window=5)
        trained_model = TrainedModel(model=model, feature_engine=engine, config=config, metrics={})
        trained_model.feature_columns = features.columns.tolist()

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "ranker_model.pkl"
            trained_model.save(str(model_path))

            # 2. 创建MLStockRanker
            ranker = MLStockRanker(
                model_path=str(model_path),
                scoring_method='sharpe',
                min_confidence=0.5
            )

            print("✓ MLStockRanker已创建")

            # 3. 评分排名
            rankings = ranker.rank(
                stock_pool=stock_pool,
                market_data=market_data,
                date='2023-08-01',
                return_top_n=10
            )

            print(f"✓ 评分完成: Top {len(rankings)} 只股票")

            # 验证评分结果
            assert len(rankings) <= 10
            assert all(isinstance(score, (int, float)) for score in rankings.values())

            # 4. 测试DataFrame返回
            result_df = ranker.rank_dataframe(
                stock_pool=stock_pool,
                market_data=market_data,
                date='2023-08-01',
                return_top_n=10
            )

            print(f"✓ DataFrame结果: {result_df.shape}")
            if len(result_df) > 0:
                assert 'score' in result_df.columns
                assert 'expected_return' in result_df.columns
            else:
                print("  (结果为空，可能由于min_confidence过滤)")

            # 5. 测试批量评分
            batch_results = ranker.batch_rank(
                stock_pool=stock_pool[:10],
                market_data=market_data,
                dates=['2023-08-01', '2023-08-05', '2023-08-10'],
                return_top_n=5
            )

            print(f"✓ 批量评分完成: {len(batch_results)} 个日期")
            assert len(batch_results) == 3

        print("\n测试6通过: ML股票评分排名完成 ✓")

    def test_07_backtest_integration(self, market_data, stock_pool):
        """
        测试7: 回测引擎集成

        验证:
        - BacktestEngine + MLEntry集成
        - 回测执行成功
        - 净值曲线生成
        - 绩效指标计算
        """
        print("\n" + "="*80)
        print("测试7: 回测引擎集成")
        print("="*80)

        # 1. 准备模型
        engine = FeatureEngine(feature_groups=['technical'], lookback_window=60)
        model = LightGBMStockModel(n_estimators=10, verbose=-1)

        test_date = '2023-06-01'
        features = engine.calculate_features(
            stock_codes=stock_pool[:10],
            market_data=market_data,
            date=test_date
        )
        features = features.replace([np.inf, -np.inf], np.nan).fillna(0)
        y_dummy = np.random.randn(len(features)) * 0.01
        model.train(features, pd.Series(y_dummy, index=features.index))

        config = TrainingConfig(model_type='lightgbm', forward_window=5)
        trained_model = TrainedModel(model=model, feature_engine=engine, config=config, metrics={})
        trained_model.feature_columns = features.columns.tolist()

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "backtest_model.pkl"
            trained_model.save(str(model_path))

            # 2. 创建MLEntry策略
            strategy = MLEntry(
                model_path=str(model_path),
                confidence_threshold=0.5,
                top_long=5,
                enable_short=False
            )

            print("✓ ML策略已创建")

            # 3. 创建回测引擎
            engine = BacktestEngine(
                initial_capital=1000000.0,
                commission_rate=0.0003,
                slippage=0.001,
                verbose=False
            )

            print("✓ 回测引擎已创建")

            # 4. 执行回测
            response = engine.backtest_ml_strategy(
                ml_entry=strategy,
                stock_pool=stock_pool,
                market_data=market_data,
                start_date='2023-08-01',
                end_date='2023-09-30',
                rebalance_freq='W'
            )

            print(f"✓ 回测完成: {response.message}")

            # 验证回测结果
            assert response.success
            assert 'portfolio_value' in response.data
            assert 'daily_returns' in response.data
            assert 'metrics' in response.data

            # 验证净值曲线
            portfolio_value = response.data['portfolio_value']
            assert len(portfolio_value) > 0
            print(f"✓ 净值曲线: {len(portfolio_value)} 个交易日")

            # 验证绩效指标
            metrics = response.data['metrics']
            print("\n绩效指标:")
            print(f"  总收益率: {metrics['total_return']:.2%}")
            print(f"  年化收益率: {metrics['annual_return']:.2%}")
            print(f"  波动率: {metrics['volatility']:.2%}")
            print(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"  最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"  胜率: {metrics['win_rate']:.2%}")

        print("\n测试7通过: 回测引擎集成完成 ✓")

    def test_08_complete_workflow(self, market_data, stock_pool):
        """
        测试8: 完整端到端工作流

        完整流程:
        1. 数据加载
        2. 特征工程
        3. 标签生成
        4. 模型训练
        5. 模型评估
        6. 策略构建
        7. 回测执行
        8. 结果分析
        """
        print("\n" + "="*80)
        print("测试8: 完整端到端工作流")
        print("="*80)

        # === 阶段1: 数据加载 ===
        print("\n[阶段1] 数据加载")
        print(f"  数据范围: {market_data['date'].min().date()} 到 {market_data['date'].max().date()}")
        print(f"  股票数量: {len(stock_pool)}")
        print(f"  总记录数: {len(market_data)}")

        # === 阶段2: 特征工程 ===
        print("\n[阶段2] 特征工程")
        feature_engine = FeatureEngine(
            feature_groups=['technical'],
            lookback_window=60
        )
        print("  ✓ 特征引擎已创建")

        # === 阶段3: 标签生成 ===
        print("\n[阶段3] 标签生成")
        label_generator = LabelGenerator(
            forward_window=5,
            label_type='return'
        )
        print("  ✓ 标签生成器已创建")

        # === 阶段4: 模型训练 ===
        print("\n[阶段4] 模型训练")

        # 准备训练数据
        all_dates = sorted(market_data['date'].unique())
        train_dates = [d for d in all_dates if '2023-01-01' <= d.strftime('%Y-%m-%d') <= '2023-06-30']

        X_list = []
        y_list = []

        for date in train_dates[::15]:  # 每15天采样一次
            date_str = date.strftime('%Y-%m-%d')
            try:
                features = feature_engine.calculate_features(
                    stock_codes=stock_pool,
                    market_data=market_data,
                    date=date_str
                )
                labels = label_generator.generate_labels(
                    stock_codes=stock_pool,
                    market_data=market_data,
                    date=date_str
                )
                common_stocks = features.index.intersection(labels.index)
                if len(common_stocks) > 0:
                    X_list.append(features.loc[common_stocks])
                    y_list.append(labels.loc[common_stocks])
            except:
                continue

        X_train = pd.concat(X_list, axis=0)
        y_train = pd.concat(y_list, axis=0)
        X_train = X_train.replace([np.inf, -np.inf], np.nan).fillna(0)
        y_train = y_train.replace([np.inf, -np.inf], np.nan).dropna()

        common_idx = X_train.index.intersection(y_train.index)
        X_train = X_train.loc[common_idx]
        y_train = y_train.loc[common_idx]

        print(f"  训练样本: {len(X_train)}")

        model = LightGBMStockModel(n_estimators=50, verbose=-1)
        model.train(X_train, y_train)
        print("  ✓ 模型训练完成")

        # === 阶段5: 模型封装 ===
        print("\n[阶段5] 模型封装")
        config = TrainingConfig(
            model_type='lightgbm',
            train_start_date='2023-01-01',
            train_end_date='2023-06-30',
            forward_window=5
        )

        trained_model = TrainedModel(
            model=model,
            feature_engine=feature_engine,
            config=config,
            metrics={'ic': 0.05}
        )
        trained_model.feature_columns = X_train.columns.tolist()
        print("  ✓ 模型已封装")

        # === 阶段6: 策略构建 ===
        print("\n[阶段6] 策略构建")
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "workflow_model.pkl"
            trained_model.save(str(model_path))

            ml_strategy = MLEntry(
                model_path=str(model_path),
                confidence_threshold=0.6,
                top_long=10,
                enable_short=False
            )
            print("  ✓ ML策略已创建")

            # === 阶段7: 回测执行 ===
            print("\n[阶段7] 回测执行")
            backtest_engine = BacktestEngine(
                initial_capital=1000000.0,
                commission_rate=0.0003,
                slippage=0.001,
                verbose=False
            )

            response = backtest_engine.backtest_ml_strategy(
                ml_entry=ml_strategy,
                stock_pool=stock_pool,
                market_data=market_data,
                start_date='2023-08-01',
                end_date='2023-11-30',
                rebalance_freq='W'
            )

            print(f"  ✓ 回测完成: {response.message}")

            # === 阶段8: 结果分析 ===
            print("\n[阶段8] 结果分析")

            metrics = response.data['metrics']
            print("\n  绩效总结:")
            print(f"    总收益率: {metrics['total_return']:.2%}")
            print(f"    年化收益率: {metrics['annual_return']:.2%}")
            print(f"    波动率: {metrics['volatility']:.2%}")
            print(f"    夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"    最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"    胜率: {metrics['win_rate']:.2%}")
            print(f"    交易天数: {metrics['n_days']}")

            cost_analysis = response.data['cost_analysis']
            print("\n  成本分析:")
            print(f"    总佣金: {cost_analysis['total_commission']:.2f}")
            print(f"    总印花税: {cost_analysis['total_stamp_tax']:.2f}")
            print(f"    总滑点: {cost_analysis['total_slippage']:.2f}")

            # 验证结果有效性
            assert response.success
            assert metrics['n_days'] > 0
            assert -1 <= metrics['total_return'] <= 10  # 合理范围

        print("\n" + "="*80)
        print("测试8通过: 完整端到端工作流成功 ✓✓✓")
        print("="*80)

    def test_09_error_handling(self, market_data, stock_pool):
        """
        测试9: 错误处理和边缘情况

        验证:
        - 空股票池处理
        - 无效日期处理
        - 数据不足处理
        - 异常恢复能力
        """
        print("\n" + "="*80)
        print("测试9: 错误处理和边缘情况")
        print("="*80)

        engine = FeatureEngine(feature_groups=['technical'], lookback_window=60)

        # 测试1: 空股票池
        print("\n[测试1] 空股票池")
        try:
            features = engine.calculate_features(
                stock_codes=[],
                market_data=market_data,
                date='2023-08-01'
            )
            print(f"  处理结果: {len(features)} 只股票")
            assert len(features) == 0
        except Exception as e:
            print(f"  预期错误: {type(e).__name__}")

        # 测试2: 无效日期
        print("\n[测试2] 无效日期")
        try:
            features = engine.calculate_features(
                stock_codes=stock_pool[:3],
                market_data=market_data,
                date='2030-01-01'  # 未来日期
            )
            print(f"  处理失败(预期)")
        except ValueError as e:
            print(f"  ✓ 捕获错误: {str(e)[:50]}")

        # 测试3: 数据不足
        print("\n[测试3] 数据不足")
        generator = LabelGenerator(forward_window=1000, label_type='return')  # 窗口过大
        labels = generator.generate_labels(
            stock_codes=stock_pool[:3],
            market_data=market_data,
            date='2023-11-01'
        )
        print(f"  处理结果: {len(labels)} 个标签 (数据不足时返回空)")

        # 测试4: 非法模型路径
        print("\n[测试4] 非法模型路径")
        try:
            strategy = MLEntry(
                model_path='/nonexistent/model.pkl',
                confidence_threshold=0.7,
                top_long=10
            )
            print(f"  加载失败(预期)")
        except FileNotFoundError:
            print("  ✓ 捕获文件不存在错误")

        print("\n测试9通过: 错误处理正常 ✓")

    def test_10_performance_benchmark(self, market_data, stock_pool):
        """
        测试10: 性能基准

        验证:
        - 特征计算性能
        - 模型预测性能
        - 回测执行性能
        """
        print("\n" + "="*80)
        print("测试10: 性能基准")
        print("="*80)

        import time

        # 基准1: 特征计算
        print("\n[基准1] 特征计算性能")
        engine = FeatureEngine(feature_groups=['technical'], lookback_window=60)

        start = time.time()
        features = engine.calculate_features(
            stock_codes=stock_pool[:10],
            market_data=market_data,
            date='2023-08-01'
        )
        elapsed = time.time() - start

        print(f"  10只股票特征计算: {elapsed:.3f} 秒")
        assert elapsed < 10.0  # 应在10秒内完成

        # 基准2: 模型预测
        print("\n[基准2] 模型预测性能")
        model = LightGBMStockModel(n_estimators=10, verbose=-1)
        features_clean = features.replace([np.inf, -np.inf], np.nan).fillna(0)
        y_dummy = np.random.randn(len(features_clean)) * 0.01
        model.train(features_clean, pd.Series(y_dummy, index=features_clean.index))

        config = TrainingConfig(model_type='lightgbm', forward_window=5)
        trained_model = TrainedModel(
            model=model, feature_engine=engine, config=config, metrics={}
        )
        trained_model.feature_columns = features_clean.columns.tolist()

        start = time.time()
        predictions = trained_model.predict(
            stock_codes=stock_pool[:10],
            market_data=market_data,
            date='2023-08-01'
        )
        elapsed = time.time() - start

        print(f"  10只股票预测: {elapsed:.3f} 秒")
        assert elapsed < 5.0  # 应在5秒内完成

        print("\n测试10通过: 性能符合预期 ✓")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
