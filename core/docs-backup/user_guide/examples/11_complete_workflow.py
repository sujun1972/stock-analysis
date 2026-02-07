"""
完整交易工作流示例

演示从数据下载到策略回测的端到端完整流程。

工作流程:
1. 数据下载与验证
2. 特征工程（Alpha因子 + 技术指标）
3. 模型训练与评估
4. 策略回测
5. 性能分析与可视化

作者: Quant Team
版本: v3.0.0
日期: 2026-02-01
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from loguru import logger

from src.providers import DataProviderFactory
from src.data.database_manager import DatabaseManager
from src.data.data_validator import DataValidator
from src.api.feature_api import calculate_alpha_factors
from src.features import TechnicalIndicators
from src.models.model_trainer import ModelTrainer, TrainingConfig
from src.strategies import MLStrategy, MomentumStrategy
from src.backtest import BacktestEngine
from src.visualization import BacktestVisualizer
from src.utils.response import Response


class TradingWorkflow:
    """完整交易工作流"""

    def __init__(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        output_dir: str = 'output'
    ):
        """
        初始化工作流

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            output_dir: 输出目录
        """
        self.stock_code = stock_code
        self.start_date = start_date
        self.end_date = end_date
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info("=" * 60)
        logger.info("📊 股票量化交易完整工作流")
        logger.info("=" * 60)
        logger.info(f"股票代码: {stock_code}")
        logger.info(f"时间范围: {start_date} ~ {end_date}")
        logger.info(f"输出目录: {output_dir}")
        logger.info("=" * 60)

    def step1_download_data(self) -> pd.DataFrame:
        """步骤1: 下载和验证数据"""
        logger.info("\n【步骤1/6】数据下载与验证")
        logger.info("-" * 60)

        try:
            # 1.1 创建数据提供者
            provider = DataProviderFactory.create_provider('akshare')

            # 1.2 下载数据
            logger.info(f"正在下载 {self.stock_code} 数据...")
            data = provider.get_daily_data(
                stock_code=self.stock_code,
                start_date=self.start_date,
                end_date=self.end_date
            )
            logger.info(f"✅ 获取了 {len(data)} 条数据")

            # 1.3 数据验证
            validator = DataValidator()
            is_valid, errors = validator.validate(data)

            if not is_valid:
                logger.warning(f"⚠️ 数据质量问题: {errors}")
                data = validator.clean(data)
                logger.info("✅ 数据已清洗")

            # 1.4 保存原始数据
            raw_data_path = self.output_dir / f"{self.stock_code}_raw.csv"
            data.to_csv(raw_data_path, index=False)
            logger.info(f"✅ 原始数据已保存: {raw_data_path}")

            return data

        except Exception as e:
            logger.exception(f"❌ 数据下载失败: {e}")
            raise

    def step2_calculate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """步骤2: 计算特征"""
        logger.info("\n【步骤2/6】特征工程")
        logger.info("-" * 60)

        try:
            # 2.1 计算Alpha因子
            logger.info("计算Alpha因子...")
            alpha_response = calculate_alpha_factors(
                data=data,
                factor_groups=['momentum', 'reversal', 'volatility', 'volume']
            )

            if not alpha_response.is_success():
                raise ValueError(f"Alpha因子计算失败: {alpha_response.message}")

            alpha_factors = alpha_response.data
            logger.info(f"✅ 计算了 {len(alpha_factors.columns)} 个Alpha因子")

            # 2.2 计算技术指标
            logger.info("计算技术指标...")
            tech = TechnicalIndicators(data)
            tech.add_ma(periods=[5, 10, 20, 60])
            tech.add_ema(periods=[12, 26])
            tech.add_macd()
            tech.add_rsi(period=14)
            tech.add_bollinger_bands()

            data_with_tech = tech.get_data()
            tech_indicators = data_with_tech.drop(columns=data.columns)
            logger.info(f"✅ 计算了 {len(tech_indicators.columns)} 个技术指标")

            # 2.3 合并特征
            features = pd.concat([alpha_factors, tech_indicators], axis=1)
            logger.info(f"✅ 总特征数: {len(features.columns)}")

            # 2.4 保存特征
            features_path = self.output_dir / f"{self.stock_code}_features.parquet"
            features.to_parquet(features_path)
            logger.info(f"✅ 特征已保存: {features_path}")

            return features

        except Exception as e:
            logger.exception(f"❌ 特征计算失败: {e}")
            raise

    def step3_train_model(
        self,
        data: pd.DataFrame,
        features: pd.DataFrame
    ) -> ModelTrainer:
        """步骤3: 训练模型"""
        logger.info("\n【步骤3/6】模型训练")
        logger.info("-" * 60)

        try:
            # 3.1 准备训练数据
            logger.info("准备训练数据...")

            # 计算未来5日收益率作为目标
            y = data['close'].pct_change(5).shift(-5)

            # 合并特征和目标
            df = pd.concat([features, y.rename('target')], axis=1)

            # 删除NaN
            df = df.dropna()

            logger.info(f"训练样本数: {len(df)}")

            # 3.2 创建训练配置
            config = TrainingConfig(
                model_type='lightgbm',
                hyperparameters={
                    'n_estimators': 100,
                    'learning_rate': 0.05,
                    'max_depth': 5,
                    'num_leaves': 31,
                    'min_child_samples': 20
                }
            )

            # 3.3 创建训练器
            trainer = ModelTrainer(config)

            # 3.4 准备数据
            prep_response = trainer.prepare_data(
                df=df,
                feature_cols=features.columns.tolist(),
                target_col='target',
                test_size=0.2,
                valid_size=0.1
            )

            # 3.5 训练
            logger.info("开始训练...")
            train_response = trainer.train(
                X_train=prep_response.data['X_train'],
                y_train=prep_response.data['y_train'],
                X_valid=prep_response.data['X_valid'],
                y_valid=prep_response.data['y_valid']
            )

            if train_response.is_success():
                logger.info("✅ 训练完成")
                logger.info(f"  训练集 R²: {train_response.metadata['train_r2']:.4f}")
                logger.info(f"  验证集 R²: {train_response.metadata['valid_r2']:.4f}")

            # 3.6 评估
            eval_response = trainer.evaluate(
                X=prep_response.data['X_test'],
                y=prep_response.data['y_test']
            )

            if eval_response.is_success():
                metrics = eval_response.data
                logger.info(f"\n测试集评估:")
                logger.info(f"  R²: {metrics['r2']:.4f}")
                logger.info(f"  IC: {metrics['ic']:.4f}")

            # 3.7 保存模型
            model_path = self.output_dir / f"{self.stock_code}_model.pkl"
            trainer.save_model(str(model_path))
            logger.info(f"✅ 模型已保存: {model_path}")

            return trainer

        except Exception as e:
            logger.exception(f"❌ 模型训练失败: {e}")
            raise

    def step4_backtest_strategy(
        self,
        data: pd.DataFrame,
        features: pd.DataFrame,
        trainer: ModelTrainer
    ) -> dict:
        """步骤4: 策略回测"""
        logger.info("\n【步骤4/6】策略回测")
        logger.info("-" * 60)

        try:
            # 4.1 创建回测引擎
            engine = BacktestEngine(
                initial_capital=1_000_000,
                commission_rate=0.0003,
                slippage_rate=0.001
            )

            results = {}

            # 4.2 回测动量策略
            logger.info("\n回测动量策略...")
            momentum_strategy = MomentumStrategy(
                name='动量策略',
                params={'lookback_period': 20}
            )

            momentum_signals = momentum_strategy.generate_signals(data, features)
            momentum_results = engine.backtest_long_only(momentum_signals, data)

            results['momentum'] = momentum_results

            logger.info(f"  年化收益率: {momentum_results.annualized_return:.2%}")
            logger.info(f"  夏普比率: {momentum_results.sharpe_ratio:.2f}")
            logger.info(f"  最大回撤: {momentum_results.max_drawdown:.2%}")

            # 4.3 回测ML策略
            logger.info("\n回测机器学习策略...")
            ml_strategy = MLStrategy(
                name='ML策略',
                params={
                    'model': trainer.model,
                    'threshold': 0.01
                }
            )

            ml_signals = ml_strategy.generate_signals(data, features)
            ml_results = engine.backtest_long_only(ml_signals, data)

            results['ml'] = ml_results

            logger.info(f"  年化收益率: {ml_results.annualized_return:.2%}")
            logger.info(f"  夏普比率: {ml_results.sharpe_ratio:.2f}")
            logger.info(f"  最大回撤: {ml_results.max_drawdown:.2%}")

            # 4.4 保存回测结果
            results_path = self.output_dir / f"{self.stock_code}_backtest.csv"
            ml_results.to_dataframe().to_csv(results_path, index=False)
            logger.info(f"\n✅ 回测结果已保存: {results_path}")

            return results

        except Exception as e:
            logger.exception(f"❌ 回测失败: {e}")
            raise

    def step5_visualize_results(self, results: dict):
        """步骤5: 可视化分析"""
        logger.info("\n【步骤5/6】可视化分析")
        logger.info("-" * 60)

        try:
            for strategy_name, backtest_result in results.items():
                logger.info(f"\n生成 {strategy_name} 策略报告...")

                viz = BacktestVisualizer(backtest_result)

                # 生成完整报告
                report_path = self.output_dir / f"{self.stock_code}_{strategy_name}_report.html"
                viz.generate_full_report(str(report_path))

                logger.info(f"✅ 报告已生成: {report_path}")

        except Exception as e:
            logger.exception(f"❌ 可视化失败: {e}")
            raise

    def step6_generate_summary(self, results: dict):
        """步骤6: 生成总结报告"""
        logger.info("\n【步骤6/6】生成总结报告")
        logger.info("-" * 60)

        summary = []
        summary.append(f"\n{'='*60}")
        summary.append(f"📊 {self.stock_code} 量化分析总结")
        summary.append(f"{'='*60}")
        summary.append(f"时间范围: {self.start_date} ~ {self.end_date}")
        summary.append(f"\n策略对比:")

        for strategy_name, result in results.items():
            summary.append(f"\n{strategy_name.upper()}策略:")
            summary.append(f"  年化收益率: {result.annualized_return:>8.2%}")
            summary.append(f"  夏普比率:   {result.sharpe_ratio:>8.2f}")
            summary.append(f"  最大回撤:   {result.max_drawdown:>8.2%}")
            summary.append(f"  胜率:       {result.win_rate:>8.2%}")
            summary.append(f"  交易次数:   {result.n_trades:>8}")

        summary.append(f"\n{'='*60}")
        summary.append(f"📁 输出文件:")
        summary.append(f"  - 原始数据: {self.stock_code}_raw.csv")
        summary.append(f"  - 特征数据: {self.stock_code}_features.parquet")
        summary.append(f"  - 模型文件: {self.stock_code}_model.pkl")
        summary.append(f"  - 回测结果: {self.stock_code}_backtest.csv")
        summary.append(f"  - 可视化报告: {self.stock_code}_*_report.html")
        summary.append(f"{'='*60}\n")

        summary_text = "\n".join(summary)
        logger.info(summary_text)

        # 保存总结
        summary_path = self.output_dir / f"{self.stock_code}_summary.txt"
        summary_path.write_text(summary_text)
        logger.info(f"✅ 总结已保存: {summary_path}")

    def run(self):
        """运行完整工作流"""
        try:
            start_time = datetime.now()

            # 执行各步骤
            data = self.step1_download_data()
            features = self.step2_calculate_features(data)
            trainer = self.step3_train_model(data, features)
            results = self.step4_backtest_strategy(data, features, trainer)
            self.step5_visualize_results(results)
            self.step6_generate_summary(results)

            # 计算耗时
            elapsed = (datetime.now() - start_time).total_seconds()

            logger.info("\n" + "=" * 60)
            logger.info(f"🎉 工作流完成！总耗时: {elapsed:.1f}秒")
            logger.info(f"📁 所有输出文件保存在: {self.output_dir}")
            logger.info("=" * 60)

        except Exception as e:
            logger.exception(f"❌ 工作流执行失败: {e}")
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='完整交易工作流')

    parser.add_argument(
        '--stock',
        type=str,
        default='000001.SZ',
        help='股票代码（默认：000001.SZ）'
    )

    parser.add_argument(
        '--start',
        type=str,
        default='2023-01-01',
        help='开始日期'
    )

    parser.add_argument(
        '--end',
        type=str,
        default='2023-12-31',
        help='结束日期'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='output',
        help='输出目录'
    )

    args = parser.parse_args()

    # 创建并运行工作流
    workflow = TradingWorkflow(
        stock_code=args.stock,
        start_date=args.start,
        end_date=args.end,
        output_dir=args.output
    )

    workflow.run()


if __name__ == '__main__':
    main()
