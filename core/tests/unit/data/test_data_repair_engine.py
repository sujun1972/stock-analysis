"""
测试数据修复引擎 (DataRepairEngine)

作者: AI Assistant
日期: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np

from src.data.data_repair_engine import DataRepairEngine, diagnose_and_repair
from src.database.db_manager import get_database


class TestDataRepairEngine:
    """测试数据修复引擎"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.db = get_database()
        self.engine = DataRepairEngine(self.db)
        self.test_symbol = 'TEST_REPAIR.SZ'

        yield

        # 测试后清理
        try:
            query = "DELETE FROM data_repair_logs WHERE symbol = %s"
            self.db._execute_update(query, (self.test_symbol,))
        except Exception:
            pass

    def test_diagnose_no_issues(self):
        """测试诊断无问题的数据"""
        df = self._create_clean_dataframe(100)

        df_repaired, report = self.engine.diagnose_and_repair(
            symbol=self.test_symbol,
            df=df,
            auto_repair=True
        )

        assert report['issues_count'] == 0
        assert report['repairs_count'] == 0
        assert len(df_repaired) == 100

        print(f"✓ 无问题数据诊断通过")

    def test_repair_missing_values(self):
        """测试修复缺失值"""
        df = self._create_clean_dataframe(100)

        # 注入缺失值
        df.iloc[10, 0] = np.nan
        df.iloc[20:25, 1] = np.nan

        df_repaired, report = self.engine.diagnose_and_repair(
            symbol=self.test_symbol,
            df=df,
            auto_repair=True
        )

        assert df_repaired.isnull().sum().sum() < df.isnull().sum().sum()
        assert report['issues_count'] > 0
        assert report['repairs_count'] > 0

        print(f"✓ 缺失值修复完成: {report['repairs_count']}个修复")

    def test_repair_price_logic(self):
        """测试修复价格逻辑错误"""
        df = self._create_clean_dataframe(100)

        # 注入价格逻辑错误: high < low
        df.iloc[10, df.columns.get_loc('high')] = 5.0
        df.iloc[10, df.columns.get_loc('low')] = 10.0

        df_repaired, report = self.engine.diagnose_and_repair(
            symbol=self.test_symbol,
            df=df,
            auto_repair=True
        )

        # 验证修复后 high >= low
        assert (df_repaired['high'] >= df_repaired['low']).all()
        assert report['repairs_count'] > 0

        print(f"✓ 价格逻辑错误修复完成")

    def test_repair_duplicates(self):
        """测试修复重复记录"""
        df = self._create_clean_dataframe(100)

        # 添加重复记录
        df = pd.concat([df, df.iloc[[10, 20, 30]]])

        df_repaired, report = self.engine.diagnose_and_repair(
            symbol=self.test_symbol,
            df=df,
            auto_repair=True
        )

        assert len(df_repaired) < len(df)
        assert df_repaired.duplicated().sum() == 0

        print(f"✓ 重复记录修复完成: 原{len(df)}行 -> {len(df_repaired)}行")

    def test_repair_methods_smart(self):
        """测试智能修复方法"""
        df = self._create_clean_dataframe(100)

        # 注入多种问题
        df.loc[df.index[10], 'open'] = np.nan  # 使用列名而不是数字索引
        df.loc[df.index[20], 'high'] = 999.0  # 异常值

        df_repaired, report = self.engine.repair_missing_values(df, method='smart')

        # repair_missing_values返回(df, report),所以report是元组的第二个元素
        assert report['repaired_count'] > 0

        print(f"✓ 智能修复方法测试通过: 修复{report['repaired_count']}个缺失值")

    def test_get_repair_history(self):
        """测试获取修复历史"""
        # 执行一次修复
        df = self._create_clean_dataframe(100)
        df.iloc[10, 0] = np.nan

        self.engine.diagnose_and_repair(
            symbol=self.test_symbol,
            df=df,
            auto_repair=True
        )

        # 获取历史
        history = self.engine.get_repair_history(symbol=self.test_symbol, limit=5)

        assert len(history) > 0
        assert history[0]['symbol'] == self.test_symbol

        print(f"✓ 修复历史查询成功: {len(history)}条记录")

    def _create_clean_dataframe(self, rows: int) -> pd.DataFrame:
        """创建干净的测试DataFrame"""
        dates = pd.date_range('2026-01-01', periods=rows, freq='D')
        df = pd.DataFrame({
            'open': np.random.uniform(10, 15, rows),
            'high': np.random.uniform(15, 20, rows),
            'low': np.random.uniform(8, 12, rows),
            'close': np.random.uniform(10, 15, rows),
            'volume': np.random.uniform(1000000, 10000000, rows)
        }, index=dates)

        # 确保价格逻辑正确
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)

        return df


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
