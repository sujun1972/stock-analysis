"""
LabelGenerator 单元测试
测试覆盖目标: >= 90%
"""
import unittest
import pandas as pd
import numpy as np

from src.ml.label_generator import LabelGenerator


class TestLabelGenerator(unittest.TestCase):
    """LabelGenerator 测试用例"""

    def setUp(self):
        """准备测试数据"""
        # 创建模拟市场数据
        dates = pd.date_range(start='2024-01-01', end='2024-02-28', freq='D')
        stock_codes = ['600000.SH', '000001.SZ', '000002.SZ']

        data = []
        for stock in stock_codes:
            base_price = 10.0 if stock == '600000.SH' else 20.0 if stock == '000001.SZ' else 30.0

            for i, date in enumerate(dates):
                # 创建有规律的价格变化
                if stock == '600000.SH':
                    # 上涨股票: 每天 +1%
                    price = base_price * (1.01 ** i)
                elif stock == '000001.SZ':
                    # 下跌股票: 每天 -0.5%
                    price = base_price * (0.995 ** i)
                else:
                    # 横盘股票: 微小波动
                    price = base_price + np.sin(i / 5) * 0.1

                data.append({
                    'date': date,
                    'stock_code': stock,
                    'open': price,
                    'high': price * 1.02,
                    'low': price * 0.98,
                    'close': price,
                    'volume': 1000000
                })

        self.market_data = pd.DataFrame(data)
        self.stock_codes = stock_codes
        self.test_date = '2024-01-15'

    def test_init_default_params(self):
        """测试默认参数初始化"""
        generator = LabelGenerator()

        self.assertEqual(generator.forward_window, 5)
        self.assertEqual(generator.label_type, 'return')
        self.assertEqual(generator.classification_thresholds, (-0.02, 0.02))

    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        generator = LabelGenerator(
            forward_window=10,
            label_type='direction',
            classification_thresholds=(-0.05, 0.05)
        )

        self.assertEqual(generator.forward_window, 10)
        self.assertEqual(generator.label_type, 'direction')
        self.assertEqual(generator.classification_thresholds, (-0.05, 0.05))

    def test_generate_labels_return_type(self):
        """测试生成 return 类型标签"""
        generator = LabelGenerator(
            forward_window=5,
            label_type='return'
        )

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        # 验证返回类型
        self.assertIsInstance(labels, pd.Series)
        self.assertEqual(labels.name, 'label')

        # 验证股票数量
        self.assertEqual(len(labels), 3)

        # 验证上涨股票有正收益
        self.assertGreater(labels['600000.SH'], 0)

        # 验证下跌股票有负收益
        self.assertLess(labels['000001.SZ'], 0)

    def test_generate_labels_direction_type(self):
        """测试生成 direction 类型标签"""
        generator = LabelGenerator(
            forward_window=5,
            label_type='direction'
        )

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        # 验证标签值为 0 或 1
        self.assertTrue(all(label in [0.0, 1.0] for label in labels.values))

        # 验证上涨股票标签为 1
        self.assertEqual(labels['600000.SH'], 1.0)

        # 验证下跌股票标签为 0
        self.assertEqual(labels['000001.SZ'], 0.0)

    def test_generate_labels_classification_type(self):
        """测试生成 classification 类型标签"""
        generator = LabelGenerator(
            forward_window=5,
            label_type='classification',
            classification_thresholds=(-0.02, 0.02)
        )

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        # 验证标签值为 0, 1, 2
        self.assertTrue(all(label in [0.0, 1.0, 2.0] for label in labels.values))

        # 上涨股票应该是 2.0 (上涨)
        self.assertEqual(labels['600000.SH'], 2.0)

        # 下跌股票应该是 0.0 (下跌)
        self.assertEqual(labels['000001.SZ'], 0.0)

        # 横盘股票应该是 1.0 (横盘)
        self.assertEqual(labels['000002.SZ'], 1.0)

    def test_generate_labels_regression_type(self):
        """测试生成 regression 类型标签"""
        generator = LabelGenerator(
            forward_window=5,
            label_type='regression'
        )

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        # regression 类型应该和 return 类型一样
        self.assertIsInstance(labels, pd.Series)
        self.assertGreater(labels['600000.SH'], 0)
        self.assertLess(labels['000001.SZ'], 0)

    def test_generate_labels_different_forward_windows(self):
        """测试不同的前向窗口"""
        for window in [1, 3, 5, 10, 20]:
            generator = LabelGenerator(
                forward_window=window,
                label_type='return'
            )

            labels = generator.generate_labels(
                stock_codes=['600000.SH'],
                market_data=self.market_data,
                date=self.test_date
            )

            # 验证能成功生成标签
            self.assertEqual(len(labels), 1)

            # 对于上涨股票，窗口越大，收益应该越大
            if window > 1:
                prev_generator = LabelGenerator(
                    forward_window=window - 1,
                    label_type='return'
                )
                prev_labels = prev_generator.generate_labels(
                    stock_codes=['600000.SH'],
                    market_data=self.market_data,
                    date=self.test_date
                )
                # 上涨股票，更长窗口应该有更高收益
                self.assertGreater(labels['600000.SH'], prev_labels['600000.SH'] * 0.95)

    def test_generate_labels_stock_not_found(self):
        """测试股票不存在的情况"""
        generator = LabelGenerator()

        labels = generator.generate_labels(
            stock_codes=['999999.SH'],  # 不存在的股票
            market_data=self.market_data,
            date=self.test_date
        )

        # 应该返回空的 Series
        self.assertEqual(len(labels), 0)

    def test_generate_labels_date_not_found(self):
        """测试日期不存在的情况"""
        generator = LabelGenerator()

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date='2030-01-01'  # 未来日期
        )

        # 应该返回空的 Series
        self.assertEqual(len(labels), 0)

    def test_generate_labels_insufficient_future_data(self):
        """测试未来数据不足的情况"""
        generator = LabelGenerator(
            forward_window=100  # 超过数据范围
        )

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date='2024-02-25'  # 接近数据末尾
        )

        # 应该返回空的 Series (没有足够的未来数据)
        self.assertEqual(len(labels), 0)

    def test_generate_labels_zero_price(self):
        """测试价格为0的情况"""
        # 创建包含0价格的数据
        bad_data = self.market_data.copy()
        bad_data.loc[
            (bad_data['stock_code'] == '600000.SH') &
            (bad_data['date'] == pd.to_datetime(self.test_date)),
            'close'
        ] = 0

        generator = LabelGenerator()

        labels = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=bad_data,
            date=self.test_date
        )

        # 应该跳过价格为0的股票
        self.assertNotIn('600000.SH', labels.index)
        # 其他股票应该正常
        self.assertIn('000001.SZ', labels.index)

    def test_convert_label_return(self):
        """测试 return 标签转换"""
        generator = LabelGenerator(label_type='return')

        self.assertAlmostEqual(generator._convert_label(0.05), 0.05)
        self.assertAlmostEqual(generator._convert_label(-0.03), -0.03)
        self.assertAlmostEqual(generator._convert_label(0.0), 0.0)

    def test_convert_label_direction(self):
        """测试 direction 标签转换"""
        generator = LabelGenerator(label_type='direction')

        self.assertEqual(generator._convert_label(0.05), 1.0)
        self.assertEqual(generator._convert_label(-0.03), 0.0)
        self.assertEqual(generator._convert_label(0.0), 0.0)  # 0 被视为不涨
        self.assertEqual(generator._convert_label(0.001), 1.0)

    def test_convert_label_classification(self):
        """测试 classification 标签转换"""
        generator = LabelGenerator(
            label_type='classification',
            classification_thresholds=(-0.02, 0.02)
        )

        # 下跌 (< -0.02)
        self.assertEqual(generator._convert_label(-0.05), 0.0)
        self.assertEqual(generator._convert_label(-0.03), 0.0)

        # 横盘 (-0.02 ~ 0.02)
        self.assertEqual(generator._convert_label(-0.01), 1.0)
        self.assertEqual(generator._convert_label(0.0), 1.0)
        self.assertEqual(generator._convert_label(0.01), 1.0)

        # 上涨 (> 0.02)
        self.assertEqual(generator._convert_label(0.03), 2.0)
        self.assertEqual(generator._convert_label(0.05), 2.0)

    def test_convert_label_unknown_type(self):
        """测试未知标签类型"""
        generator = LabelGenerator()
        generator.label_type = 'unknown'  # 手动设置为无效类型

        with self.assertRaises(ValueError) as context:
            generator._convert_label(0.05)

        self.assertIn('Unknown label_type', str(context.exception))

    def test_generate_multi_horizon_labels(self):
        """测试多时间窗口标签生成"""
        generator = LabelGenerator(label_type='return')

        horizons = [1, 3, 5, 10]
        multi_labels = generator.generate_multi_horizon_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date,
            horizons=horizons
        )

        # 验证返回类型
        self.assertIsInstance(multi_labels, pd.DataFrame)

        # 验证列数
        self.assertEqual(len(multi_labels.columns), len(horizons))

        # 验证列名
        expected_columns = ['label_1d', 'label_3d', 'label_5d', 'label_10d']
        self.assertListEqual(list(multi_labels.columns), expected_columns)

        # 验证股票数量
        self.assertEqual(len(multi_labels), len(self.stock_codes))

        # 验证上涨股票的标签随窗口增大而增大
        for i in range(len(horizons) - 1):
            col1 = f'label_{horizons[i]}d'
            col2 = f'label_{horizons[i+1]}d'

            # 600000.SH 是上涨股票
            if pd.notna(multi_labels.loc['600000.SH', col1]) and \
               pd.notna(multi_labels.loc['600000.SH', col2]):
                self.assertGreater(
                    multi_labels.loc['600000.SH', col2],
                    multi_labels.loc['600000.SH', col1] * 0.9
                )

    def test_generate_multi_horizon_labels_with_classification(self):
        """测试多时间窗口分类标签生成"""
        generator = LabelGenerator(
            label_type='classification',
            classification_thresholds=(-0.02, 0.02)
        )

        multi_labels = generator.generate_multi_horizon_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date,
            horizons=[1, 5, 10]
        )

        # 验证所有值都在 [0, 1, 2] 中
        for col in multi_labels.columns:
            valid_values = multi_labels[col].dropna().isin([0.0, 1.0, 2.0])
            self.assertTrue(valid_values.all())

    def test_generate_multi_horizon_labels_default_horizons(self):
        """测试默认时间窗口"""
        generator = LabelGenerator(label_type='return')

        multi_labels = generator.generate_multi_horizon_labels(
            stock_codes=['600000.SH'],
            market_data=self.market_data,
            date=self.test_date
        )

        # 默认窗口应该是 [1, 3, 5, 10, 20]
        expected_columns = ['label_1d', 'label_3d', 'label_5d', 'label_10d', 'label_20d']
        self.assertListEqual(list(multi_labels.columns), expected_columns)

    def test_label_consistency_across_calls(self):
        """测试多次调用结果一致性"""
        generator = LabelGenerator(
            forward_window=5,
            label_type='return'
        )

        labels1 = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        labels2 = generator.generate_labels(
            stock_codes=self.stock_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        # 验证两次调用结果完全一致
        pd.testing.assert_series_equal(labels1, labels2)

    def test_empty_stock_codes(self):
        """测试空股票列表"""
        generator = LabelGenerator()

        labels = generator.generate_labels(
            stock_codes=[],
            market_data=self.market_data,
            date=self.test_date
        )

        self.assertEqual(len(labels), 0)

    def test_partial_stock_codes_available(self):
        """测试部分股票可用的情况"""
        generator = LabelGenerator()

        # 包含一些存在和不存在的股票
        mixed_codes = ['600000.SH', '999999.SH', '000001.SZ', '888888.SZ']

        labels = generator.generate_labels(
            stock_codes=mixed_codes,
            market_data=self.market_data,
            date=self.test_date
        )

        # 应该只返回存在的股票
        self.assertEqual(len(labels), 2)
        self.assertIn('600000.SH', labels.index)
        self.assertIn('000001.SZ', labels.index)
        self.assertNotIn('999999.SH', labels.index)
        self.assertNotIn('888888.SZ', labels.index)


class TestLabelGeneratorEdgeCases(unittest.TestCase):
    """LabelGenerator 边缘情况测试"""

    def test_single_day_data(self):
        """测试只有一天数据的情况"""
        data = pd.DataFrame([
            {
                'date': pd.to_datetime('2024-01-01'),
                'stock_code': '600000.SH',
                'close': 10.0
            }
        ])

        generator = LabelGenerator(forward_window=1)

        labels = generator.generate_labels(
            stock_codes=['600000.SH'],
            market_data=data,
            date='2024-01-01'
        )

        # 没有未来数据，应该返回空
        self.assertEqual(len(labels), 0)

    def test_large_forward_window(self):
        """测试超大前向窗口"""
        dates = pd.date_range(start='2024-01-01', end='2024-01-10', freq='D')
        data = []
        for date in dates:
            data.append({
                'date': date,
                'stock_code': '600000.SH',
                'close': 10.0
            })

        df = pd.DataFrame(data)

        generator = LabelGenerator(forward_window=1000)

        labels = generator.generate_labels(
            stock_codes=['600000.SH'],
            market_data=df,
            date='2024-01-01'
        )

        # 未来数据不足，应该返回空
        self.assertEqual(len(labels), 0)

    def test_extreme_classification_thresholds(self):
        """测试极端分类阈值"""
        # 非常窄的阈值
        generator = LabelGenerator(
            label_type='classification',
            classification_thresholds=(-0.001, 0.001)
        )

        self.assertEqual(generator._convert_label(0.002), 2.0)
        self.assertEqual(generator._convert_label(-0.002), 0.0)
        self.assertEqual(generator._convert_label(0.0005), 1.0)

        # 非常宽的阈值
        generator = LabelGenerator(
            label_type='classification',
            classification_thresholds=(-0.5, 0.5)
        )

        self.assertEqual(generator._convert_label(0.3), 1.0)
        self.assertEqual(generator._convert_label(-0.3), 1.0)


if __name__ == '__main__':
    unittest.main()
