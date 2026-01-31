"""
测试增量更新管理器 (IncrementalUpdateManager)

作者: AI Assistant
日期: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np

from src.data.incremental_update_manager import IncrementalUpdateManager
from src.database.db_manager import get_database


class TestIncrementalUpdateManager:
    """测试增量更新管理器"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.db = get_database()
        self.manager = IncrementalUpdateManager(self.db)
        self.test_symbol = 'TEST_INC.SZ'

        yield

        # 测试后清理
        try:
            query = "DELETE FROM incremental_update_logs WHERE symbol = %s"
            self.db._execute_update(query, (self.test_symbol,))
            query = "DELETE FROM data_versions WHERE symbol = %s"
            self.db._execute_update(query, (self.test_symbol,))
        except Exception:
            pass

    def test_detect_full_update(self):
        """测试检测全量更新 (无本地数据)"""
        df = self._create_test_dataframe(100)

        result = self.manager.detect_incremental_updates(self.test_symbol, df)

        assert result['is_full_update'] is True
        assert result['new_count'] == 100
        assert result['updated_count'] == 0
        assert result['unchanged_count'] == 0

        print(f"✓ 全量更新检测: 新增{result['new_count']}条")

    def test_detect_no_changes(self):
        """测试检测无变化"""
        # 先插入数据
        df = self._create_test_dataframe(100)

        self.manager.update_symbol_incremental(
            symbol=self.test_symbol,
            remote_df=df,
            data_source='akshare'
        )

        # 再次用相同数据检测
        result = self.manager.detect_incremental_updates(self.test_symbol, df)

        assert result['new_count'] == 0
        assert result['updated_count'] == 0
        assert result['unchanged_count'] == 100

        print(f"✓ 无变化检测通过")

    def test_detect_incremental_new_records(self):
        """测试检测新增记录"""
        # 先插入初始数据
        df_initial = self._create_test_dataframe(100)

        self.manager.update_symbol_incremental(
            symbol=self.test_symbol,
            remote_df=df_initial,
            data_source='akshare'
        )

        # 添加新记录 - 保留前100行，添加新的10行
        # 注意：为了确保前100行数据一致，我们需要复制df_initial并追加新数据
        df_new_only = self._create_test_dataframe(110).iloc[100:]  # 只取后10行
        df_new = pd.concat([df_initial.copy(), df_new_only])

        result = self.manager.detect_incremental_updates(self.test_symbol, df_new)

        assert result['new_count'] == 10
        assert result['unchanged_count'] == 100

        print(f"✓ 新增记录检测: {result['new_count']}条新增")

    def test_update_symbol_incremental_success(self):
        """测试增量更新成功"""
        df = self._create_test_dataframe(100)

        result = self.manager.update_symbol_incremental(
            symbol=self.test_symbol,
            remote_df=df,
            data_source='akshare',
            update_type='daily'
        )

        assert result['status'] == 'success'
        assert result['new_count'] == 100
        assert 'duration_seconds' in result

        print(f"✓ 增量更新成功: 耗时{result['duration_seconds']:.3f}秒")

    def test_get_update_history(self):
        """测试获取更新历史"""
        # 执行一次更新
        df = self._create_test_dataframe(100)

        self.manager.update_symbol_incremental(
            symbol=self.test_symbol,
            remote_df=df,
            data_source='akshare'
        )

        # 获取历史
        history = self.manager.get_update_history(symbol=self.test_symbol, limit=5)

        assert len(history) > 0
        assert history[0]['symbol'] == self.test_symbol
        assert history[0]['status'] == 'success'

        print(f"✓ 更新历史查询成功: {len(history)}条记录")

    def _create_test_dataframe(self, rows: int) -> pd.DataFrame:
        """创建测试DataFrame"""
        np.random.seed(42)  # 固定种子
        dates = pd.date_range('2026-01-01', periods=rows, freq='D')

        # 生成基础价格数据
        open_prices = np.random.uniform(10, 20, rows)
        close_prices = np.random.uniform(10, 20, rows)
        high_prices = np.maximum(open_prices, close_prices) + np.random.uniform(0, 2, rows)
        low_prices = np.minimum(open_prices, close_prices) - np.random.uniform(0, 2, rows)
        volumes = np.random.uniform(1000000, 10000000, rows).astype(int)

        df = pd.DataFrame({
            'open': open_prices.astype(float),
            'high': high_prices.astype(float),
            'low': low_prices.astype(float),
            'close': close_prices.astype(float),
            'volume': volumes.astype('int64'),
            'amount': (volumes * close_prices).astype(float),  # 成交额 = 成交量 * 收盘价
            'amplitude': ((high_prices - low_prices) / close_prices * 100).astype(float),  # 振幅
            'pct_change': np.random.uniform(-5, 5, rows).astype(float),  # 涨跌幅
            'change': (close_prices - open_prices).astype(float),  # 涨跌额
            'turnover': np.random.uniform(0.5, 5, rows).astype(float)  # 换手率
        }, index=dates)

        # 转换volume为int类型 (避免numpy.int64导致psycopg2错误)
        df['volume'] = df['volume'].astype(int)

        return df


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
