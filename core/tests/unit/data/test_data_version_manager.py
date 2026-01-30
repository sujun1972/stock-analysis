"""
测试数据版本管理器 (DataVersionManager)

测试内容:
- 版本创建
- 活跃版本获取
- 版本历史查询
- 版本对比
- 版本回滚
- 版本清理

作者: AI Assistant
日期: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.data.data_version_manager import DataVersionManager
from src.data.data_checksum_validator import DataChecksumValidator
from src.database.db_manager import get_database


class TestDataVersionManager:
    """测试数据版本管理器"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.db = get_database()
        self.manager = DataVersionManager(self.db)
        self.test_symbol = 'TEST_VER.SZ'

        # 清理测试数据
        try:
            query = "DELETE FROM data_versions WHERE symbol = %s"
            self.db._execute_update(query, (self.test_symbol,))
        except Exception:
            pass

        yield

        # 测试后清理
        try:
            query = "DELETE FROM data_versions WHERE symbol = %s"
            self.db._execute_update(query, (self.test_symbol,))
        except Exception:
            pass

    def test_create_version(self):
        """测试创建版本"""
        # 准备测试数据
        df = self._create_test_dataframe(100)
        checksum = DataChecksumValidator.calculate_checksum(df)

        # 创建版本
        version = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-01-30',
            data_source='akshare',
            checksum=checksum,
            record_count=len(df),
            metadata={'test': True}
        )

        # 验证
        assert version is not None
        assert version['symbol'] == self.test_symbol
        assert version['record_count'] == 100
        assert version['checksum'] == checksum
        assert version['is_active'] is True
        assert 'version_id' in version
        assert 'version_number' in version

        print(f"✓ 创建版本: {version['version_number']}")

    def test_get_active_version(self):
        """测试获取活跃版本"""
        # 创建两个版本
        df1 = self._create_test_dataframe(100)
        checksum1 = DataChecksumValidator.calculate_checksum(df1)

        v1 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-01-30',
            data_source='akshare',
            checksum=checksum1,
            record_count=100
        )

        df2 = self._create_test_dataframe(110)
        checksum2 = DataChecksumValidator.calculate_checksum(df2)

        v2 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-02-10',
            data_source='akshare',
            checksum=checksum2,
            record_count=110,
            parent_version_id=v1['version_id']
        )

        # 获取活跃版本 (应该是v2)
        active = self.manager.get_active_version(self.test_symbol)

        assert active is not None
        assert active['version_id'] == v2['version_id']
        assert active['record_count'] == 110
        assert active['parent_version_id'] == v1['version_id']

        print(f"✓ 活跃版本: {active['version_number']}")

    def test_get_version_history(self):
        """测试获取版本历史"""
        # 创建3个版本
        for i in range(3):
            df = self._create_test_dataframe(100 + i*10)
            checksum = DataChecksumValidator.calculate_checksum(df)

            self.manager.create_version(
                symbol=self.test_symbol,
                start_date='2026-01-01',
                end_date='2026-01-30',
                data_source='akshare',
                checksum=checksum,
                record_count=100 + i*10
            )

        # 获取历史
        history = self.manager.get_version_history(self.test_symbol, limit=10)

        assert len(history) == 3
        # 应该按创建时间倒序
        assert history[0]['record_count'] == 120  # 最新的
        assert history[2]['record_count'] == 100  # 最旧的

        print(f"✓ 版本历史: {len(history)}个版本")

    def test_compare_versions(self):
        """测试版本对比"""
        # 创建两个版本
        df1 = self._create_test_dataframe(100)
        checksum1 = DataChecksumValidator.calculate_checksum(df1)

        v1 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-01-30',
            data_source='akshare',
            checksum=checksum1,
            record_count=100
        )

        df2 = self._create_test_dataframe(120)
        checksum2 = DataChecksumValidator.calculate_checksum(df2)

        v2 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-02-10',
            data_source='tushare',  # 不同的数据源
            checksum=checksum2,
            record_count=120
        )

        # 对比版本
        comparison = self.manager.compare_versions(
            self.test_symbol,
            v1['version_number'],
            v2['version_number']
        )

        assert comparison is not None
        assert comparison['differences']['record_count'] == 20  # 120 - 100
        assert comparison['differences']['checksum_changed'] is True
        assert comparison['differences']['data_source']['changed'] is True

        print(f"✓ 版本对比完成")

    def test_set_active_version(self):
        """测试设置活跃版本 (回滚)"""
        # 创建两个版本
        df1 = self._create_test_dataframe(100)
        checksum1 = DataChecksumValidator.calculate_checksum(df1)

        v1 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-01-30',
            data_source='akshare',
            checksum=checksum1,
            record_count=100
        )

        df2 = self._create_test_dataframe(110)
        checksum2 = DataChecksumValidator.calculate_checksum(df2)

        v2 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-02-10',
            data_source='akshare',
            checksum=checksum2,
            record_count=110
        )

        # v2现在是活跃版本
        active = self.manager.get_active_version(self.test_symbol)
        assert active['version_id'] == v2['version_id']

        # 回滚到v1
        result = self.manager.set_active_version(self.test_symbol, v1['version_number'])
        assert result is True

        # 验证v1现在是活跃版本
        active = self.manager.get_active_version(self.test_symbol)
        assert active['version_id'] == v1['version_id']

        print(f"✓ 回滚到版本: {v1['version_number']}")

    def test_cleanup_old_versions(self):
        """测试清理旧版本"""
        # 创建10个版本
        for i in range(10):
            df = self._create_test_dataframe(100 + i)
            checksum = DataChecksumValidator.calculate_checksum(df)

            self.manager.create_version(
                symbol=self.test_symbol,
                start_date='2026-01-01',
                end_date='2026-01-30',
                data_source='akshare',
                checksum=checksum,
                record_count=100 + i
            )

        # 验证有10个版本
        history_before = self.manager.get_version_history(self.test_symbol, limit=100)
        assert len(history_before) == 10

        # 清理,只保留最近3个
        result = self.manager.cleanup_old_versions(
            symbol=self.test_symbol,
            keep_recent=3,
            dry_run=False
        )

        assert result['total_deleted'] == 7
        assert result['total_kept'] == 3

        # 验证只剩3个版本
        history_after = self.manager.get_version_history(self.test_symbol, limit=100)
        assert len(history_after) == 3

        print(f"✓ 清理版本: 删除{result['total_deleted']}个, 保留{result['total_kept']}个")

    def test_get_version_chain(self):
        """测试获取版本链"""
        # 创建版本链: v1 -> v2 -> v3
        df1 = self._create_test_dataframe(100)
        checksum1 = DataChecksumValidator.calculate_checksum(df1)

        v1 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-01-30',
            data_source='akshare',
            checksum=checksum1,
            record_count=100
        )

        df2 = self._create_test_dataframe(110)
        checksum2 = DataChecksumValidator.calculate_checksum(df2)

        v2 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-02-10',
            data_source='akshare',
            checksum=checksum2,
            record_count=110,
            parent_version_id=v1['version_id']
        )

        df3 = self._create_test_dataframe(120)
        checksum3 = DataChecksumValidator.calculate_checksum(df3)

        v3 = self.manager.create_version(
            symbol=self.test_symbol,
            start_date='2026-01-01',
            end_date='2026-03-01',
            data_source='akshare',
            checksum=checksum3,
            record_count=120,
            parent_version_id=v2['version_id']
        )

        # 获取v3的版本链
        chain = self.manager.get_version_chain(self.test_symbol, v3['version_number'])

        assert len(chain) == 3
        assert chain[0]['version_id'] == v1['version_id']  # 根版本
        assert chain[1]['version_id'] == v2['version_id']
        assert chain[2]['version_id'] == v3['version_id']  # 当前版本

        print(f"✓ 版本链: {len(chain)}层")

    def _create_test_dataframe(self, rows: int) -> pd.DataFrame:
        """创建测试用DataFrame"""
        dates = pd.date_range('2026-01-01', periods=rows, freq='D')
        df = pd.DataFrame({
            'open': np.random.uniform(10, 20, rows),
            'high': np.random.uniform(15, 25, rows),
            'low': np.random.uniform(5, 15, rows),
            'close': np.random.uniform(10, 20, rows),
            'volume': np.random.uniform(1000000, 10000000, rows)
        }, index=dates)
        return df


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
