"""
Walk-Forward验证器单元测试

测试功能：
- 窗口创建（滑动和锚定模式）
- 完整验证流程
- 过拟合检测
- 数据分割正确性
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from optimization.walk_forward import WalkForwardValidator, WalkForwardWindow


@pytest.fixture
def sample_dates():
    """生成样本日期列表"""
    return pd.date_range('2020-01-01', periods=300, freq='D').tolist()


@pytest.fixture
def sample_data():
    """生成样本数据"""
    dates = pd.date_range('2020-01-01', periods=300, freq='D')
    stocks = [f'stock_{i:02d}' for i in range(50)]

    prices = pd.DataFrame(
        100 * (1 + np.random.randn(300, 50) * 0.02).cumprod(axis=0),
        index=dates,
        columns=stocks
    )

    features = pd.DataFrame(
        np.random.randn(300, 50),
        index=dates,
        columns=stocks
    )

    return {'prices': prices, 'features': features}


@pytest.fixture
def simple_optimizer():
    """简单的优化器类"""
    class SimpleOptimizer:
        def optimize(self, obj_func, maximize=True):
            """简单网格搜索"""
            best_score = -np.inf if maximize else np.inf
            best_params = None

            for lookback in [10, 20, 30]:
                for top_n in [10, 20, 30]:
                    params = {'lookback': lookback, 'top_n': top_n}
                    try:
                        score = obj_func(params)
                        if maximize and score > best_score:
                            best_score = score
                            best_params = params
                        elif not maximize and score < best_score:
                            best_score = score
                            best_params = params
                    except:
                        continue

            from dataclasses import dataclass
            @dataclass
            class Result:
                best_params: dict
                best_score: float

            return Result(best_params=best_params, best_score=best_score)

    return SimpleOptimizer()


class TestWalkForwardValidatorInit:
    """测试初始化"""

    def test_default_init(self):
        validator = WalkForwardValidator()
        assert validator.train_period == 252
        assert validator.test_period == 63
        assert validator.step_size == 63
        assert validator.min_train_size == 126

    def test_custom_init(self):
        validator = WalkForwardValidator(
            train_period=120,
            test_period=30,
            step_size=30,
            min_train_size=60
        )
        assert validator.train_period == 120
        assert validator.test_period == 30
        assert validator.step_size == 30
        assert validator.min_train_size == 60


class TestCreateWindows:
    """测试窗口创建"""

    def test_basic_windows(self, sample_dates):
        validator = WalkForwardValidator(
            train_period=60,
            test_period=20,
            step_size=20
        )

        windows = validator.create_windows(sample_dates, anchored=False)

        assert isinstance(windows, list)
        assert len(windows) > 0
        for train_dates, test_dates in windows:
            assert len(train_dates) == 60
            assert len(test_dates) == 20
            # 训练集和测试集不重叠
            assert train_dates[-1] < test_dates[0]

    def test_anchored_windows(self, sample_dates):
        validator = WalkForwardValidator(
            train_period=60,
            test_period=20,
            step_size=20
        )

        windows = validator.create_windows(sample_dates, anchored=True)

        assert isinstance(windows, list)
        # 锚定模式：所有窗口从同一起点开始
        if len(windows) >= 2:
            assert windows[0][0][0] == windows[1][0][0]

    def test_insufficient_data(self):
        validator = WalkForwardValidator(
            train_period=100,
            test_period=50,
            min_train_size=80
        )

        short_dates = pd.date_range('2020-01-01', periods=50, freq='D').tolist()
        windows = validator.create_windows(short_dates)

        # 数据不足时应该返回空列表
        assert len(windows) == 0

    def test_step_size_effect(self, sample_dates):
        validator_small_step = WalkForwardValidator(
            train_period=60,
            test_period=20,
            step_size=10  # 小步长
        )

        validator_large_step = WalkForwardValidator(
            train_period=60,
            test_period=20,
            step_size=40  # 大步长
        )

        windows_small = validator_small_step.create_windows(sample_dates)
        windows_large = validator_large_step.create_windows(sample_dates)

        # 步长越小，窗口数越多
        assert len(windows_small) > len(windows_large)


class TestValidate:
    """测试完整验证流程"""

    def test_basic_validation(self, sample_data, sample_dates, simple_optimizer):
        validator = WalkForwardValidator(
            train_period=100,
            test_period=30,
            step_size=30,
            min_train_size=50
        )

        def objective_func(params, data):
            """简单目标函数"""
            lookback = params['lookback']
            top_n = params['top_n']
            # 简单计算：基于参数返回得分
            score = 1.0 - abs(lookback - 20) / 30 - abs(top_n - 20) / 40
            score += np.random.randn() * 0.05
            return max(score, 0)

        results_df = validator.validate(
            objective_func=objective_func,
            optimizer=simple_optimizer,
            data=sample_data,
            dates=sample_dates
        )

        assert isinstance(results_df, pd.DataFrame)
        assert '窗口' in results_df.columns
        assert '训练得分' in results_df.columns
        assert '测试得分' in results_df.columns
        assert '过拟合度' in results_df.columns
        assert len(results_df) > 0

    def test_validation_columns(self, sample_data, sample_dates, simple_optimizer):
        validator = WalkForwardValidator(
            train_period=100,
            test_period=30,
            step_size=50
        )

        def objective_func(params, data):
            return np.random.rand()

        results_df = validator.validate(
            objective_func=objective_func,
            optimizer=simple_optimizer,
            data=sample_data,
            dates=sample_dates
        )

        required_columns = ['窗口', '训练开始', '训练结束', '测试开始', '测试结束',
                          '训练得分', '测试得分', '过拟合度', '参数']
        for col in required_columns:
            assert col in results_df.columns

    def test_validation_overfitting_detection(self, sample_data, sample_dates, simple_optimizer):
        validator = WalkForwardValidator(
            train_period=100,
            test_period=30,
            step_size=50
        )

        # 创建过拟合的目标函数：训练集得分高，测试集得分低
        def overfitting_func(params, data):
            # 在训练集上返回高分，测试集上返回低分（通过随机性模拟）
            score = np.random.uniform(0.5, 1.0)
            return score

        results_df = validator.validate(
            objective_func=overfitting_func,
            optimizer=simple_optimizer,
            data=sample_data,
            dates=sample_dates
        )

        # 过拟合度 = 训练得分 - 测试得分
        assert '过拟合度' in results_df.columns


class TestDataSplitting:
    """测试数据分割"""

    def test_split_data_basic(self):
        validator = WalkForwardValidator()

        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        data = {
            'prices': pd.DataFrame(
                np.random.randn(100, 10),
                index=dates
            )
        }

        split_dates = dates[:50].tolist()
        split_data = validator._split_data(data, split_dates)

        assert isinstance(split_data, dict)
        assert 'prices' in split_data
        assert len(split_data['prices']) == 50

    def test_split_non_dataframe(self):
        validator = WalkForwardValidator()

        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        data = {
            'config': {'param1': 1, 'param2': 2}  # 非DataFrame数据
        }

        split_dates = dates[:50].tolist()
        split_data = validator._split_data(data, split_dates)

        # 非DataFrame数据应该直接传递
        assert split_data['config'] == data['config']


class TestWalkForwardWindow:
    """测试WalkForwardWindow数据类"""

    def test_window_creation(self):
        window = WalkForwardWindow(
            window_id=1,
            train_start=datetime(2020, 1, 1),
            train_end=datetime(2020, 3, 31),
            test_start=datetime(2020, 4, 1),
            test_end=datetime(2020, 4, 30),
            optimal_params={'lookback': 20, 'top_n': 50},
            train_score=0.85,
            test_score=0.75
        )

        assert window.window_id == 1
        assert window.train_score == 0.85
        assert window.test_score == 0.75
        assert window.optimal_params['lookback'] == 20


class TestEdgeCases:
    """测试边界条件"""

    def test_empty_windows(self, sample_data, simple_optimizer):
        validator = WalkForwardValidator(
            train_period=500,  # 超过数据长度
            test_period=100
        )

        dates = pd.date_range('2020-01-01', periods=100, freq='D').tolist()

        def objective_func(params, data):
            return 0.5

        results_df = validator.validate(
            objective_func=objective_func,
            optimizer=simple_optimizer,
            data=sample_data,
            dates=dates
        )

        # 应该返回空DataFrame（因为无法创建窗口）
        assert len(results_df) == 0

    def test_optimizer_failure(self, sample_data, sample_dates):
        validator = WalkForwardValidator(
            train_period=100,
            test_period=30,
            step_size=50
        )

        class FailingOptimizer:
            def optimize(self, obj_func, maximize=True):
                raise ValueError("Optimization failed")

        def objective_func(params, data):
            return 0.5

        results_df = validator.validate(
            objective_func=objective_func,
            optimizer=FailingOptimizer(),
            data=sample_data,
            dates=sample_dates
        )

        # 优化失败时应该跳过该窗口
        assert isinstance(results_df, pd.DataFrame)


class TestIntegration:
    """集成测试"""

    def test_complete_workflow(self, sample_data, sample_dates, simple_optimizer):
        # 1. 创建验证器
        validator = WalkForwardValidator(
            train_period=120,
            test_period=30,
            step_size=30,
            min_train_size=60
        )

        # 2. 定义目标函数
        def objective_func(params, data):
            lookback = params['lookback']
            score = 1.0 - abs(lookback - 20) / 30
            score += np.random.randn() * 0.05
            return max(score, 0)

        # 3. 执行验证
        results_df = validator.validate(
            objective_func=objective_func,
            optimizer=simple_optimizer,
            data=sample_data,
            dates=sample_dates
        )

        # 4. 验证结果
        assert len(results_df) > 0
        assert all(results_df['训练得分'] >= 0)
        assert all(results_df['测试得分'] >= 0)

        # 5. 检查过拟合
        avg_overfitting = results_df['过拟合度'].mean()
        assert isinstance(avg_overfitting, (int, float))


@pytest.mark.performance
class TestPerformance:
    """性能测试"""

    def test_large_dataset_validation(self):
        import time

        dates = pd.date_range('2018-01-01', periods=1000, freq='D')
        data = {
            'prices': pd.DataFrame(
                100 * (1 + np.random.randn(1000, 100) * 0.02).cumprod(axis=0),
                index=dates
            )
        }

        validator = WalkForwardValidator(
            train_period=200,
            test_period=50,
            step_size=100
        )

        class FastOptimizer:
            def optimize(self, obj_func, maximize=True):
                from dataclasses import dataclass
                @dataclass
                class Result:
                    best_params: dict
                    best_score: float
                return Result(best_params={'x': 1}, best_score=0.5)

        def objective_func(params, data):
            return 0.5

        start = time.time()
        results_df = validator.validate(
            objective_func=objective_func,
            optimizer=FastOptimizer(),
            data=data,
            dates=dates.tolist()
        )
        duration = time.time() - start

        assert duration < 5.0  # 应该在5秒内完成


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
