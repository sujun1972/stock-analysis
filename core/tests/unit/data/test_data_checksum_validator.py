"""
测试数据校验和验证器 (DataChecksumValidator)

作者: AI Assistant
日期: 2026-01-30
"""

import pytest
import pandas as pd
import numpy as np

from src.data.data_checksum_validator import DataChecksumValidator, calculate_checksum, validate_checksum


class TestDataChecksumValidator:
    """测试数据校验和验证器"""

    def test_calculate_checksum(self):
        """测试计算校验和"""
        df = self._create_test_dataframe(100)

        checksum = calculate_checksum(df)

        assert checksum is not None
        assert len(checksum) == 64  # SHA256长度
        assert isinstance(checksum, str)

        print(f"✓ 计算校验和: {checksum[:16]}...")

    def test_checksum_consistency(self):
        """测试校验和一致性 (相同数据应产生相同校验和)"""
        df = self._create_test_dataframe(100)

        checksum1 = calculate_checksum(df)
        checksum2 = calculate_checksum(df)

        assert checksum1 == checksum2

        print(f"✓ 校验和一致性验证通过")

    def test_checksum_sensitivity(self):
        """测试校验和敏感性 (数据变化应产生不同校验和)"""
        df = self._create_test_dataframe(100)

        checksum1 = calculate_checksum(df)

        # 修改数据
        df.iloc[0, 0] = 999.0

        checksum2 = calculate_checksum(df)

        assert checksum1 != checksum2

        print(f"✓ 校验和敏感性验证通过")

    def test_validate_checksum_success(self):
        """测试校验和验证成功"""
        df = self._create_test_dataframe(100)

        expected_checksum = calculate_checksum(df)

        is_valid, actual_checksum = validate_checksum(df, expected_checksum)

        assert is_valid is True
        assert actual_checksum == expected_checksum

        print(f"✓ 校验和验证通过")

    def test_validate_checksum_failure(self):
        """测试校验和验证失败"""
        df = self._create_test_dataframe(100)

        original_checksum = calculate_checksum(df)

        # 修改数据
        df.iloc[0, 0] = 999.0

        is_valid, actual_checksum = validate_checksum(df, original_checksum)

        assert is_valid is False
        assert actual_checksum != original_checksum

        print(f"✓ 校验和不匹配检测成功")

    def test_incremental_checksum(self):
        """测试增量校验和"""
        df_old = self._create_test_dataframe(100)
        df_new = df_old.copy()

        # 添加新记录
        new_date = df_new.index.max() + pd.Timedelta(days=1)
        df_new.loc[new_date] = [15, 20, 10, 18, 5000000]

        # 修改记录
        df_new.iloc[10, 0] = 999.0

        result = DataChecksumValidator.calculate_incremental_checksum(df_new, df_old)

        assert 'added' in result
        assert 'modified' in result
        assert result['added_count'] == 1
        assert result['modified_count'] == 1
        assert result['unchanged_count'] == 99

        print(f"✓ 增量校验和计算完成: 新增{result['added_count']}, 修改{result['modified_count']}")

    def _create_test_dataframe(self, rows: int) -> pd.DataFrame:
        """创建测试DataFrame"""
        np.random.seed(42)  # 固定种子确保可重复性
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
