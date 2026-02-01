"""
A股列表获取模块单元测试

测试范围：
1. fetch_akshare_stock_list - AkShare数据源
2. fetch_tushare_stock_list - Tushare数据源
3. fetch_and_save_a_stock_list - 智能数据源选择
4. save_stock_list_to_database - 数据库保存
5. get_a_stock_list_detailed - 详细信息获取
6. update_stock_list_from_database - 数据库读取
7. 市场类型判断和边界情况

目标覆盖率: 90%+

作者: Stock Analysis Team
创建: 2026-01-29
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
import tempfile
import os

# Mock Settings before importing module
with patch('src.config.settings.get_settings') as mock_get_settings:
    mock_settings = Mock()
    mock_settings.TUSHARE_TOKEN = 'test_token'
    mock_settings.DATABASE_HOST = 'localhost'
    mock_settings.DATABASE_PORT = 5432
    mock_settings.DATABASE_NAME = 'testdb'
    mock_settings.DATABASE_USER = 'testuser'
    mock_settings.DATABASE_PASSWORD = 'testpass'
    mock_get_settings.return_value = mock_settings

    from src.a_stock_list_fetcher import (
        fetch_akshare_stock_list,
        fetch_tushare_stock_list,
        fetch_and_save_a_stock_list,
        save_stock_list_to_database,
        get_a_stock_list_detailed,
        update_stock_list_from_database
    )


# ==================== Fixtures ====================

@pytest.fixture
def sample_akshare_data():
    """创建模拟的AkShare数据"""
    return pd.DataFrame({
        '代码': pd.Series(['000001', '000002', '600000', '600001', '300001', '688001'], dtype='str'),
        '名称': pd.Series(['平安银行', '万科A', '浦发银行', '邮储银行', '特锐德', '华兴源创'], dtype='str'),
        '市盈率-动态': [5.2, 8.5, 6.3, 7.1, 25.3, 35.6],
        '市净率': [0.8, 1.2, 0.9, 1.0, 3.5, 4.2]
    })


@pytest.fixture
def sample_tushare_data():
    """创建模拟的Tushare数据"""
    return pd.DataFrame({
        'ts_code': ['000001.SZ', '000002.SZ', '600000.SH', '600001.SH'],
        'symbol': ['000001', '000002', '600000', '600001'],
        'name': ['平安银行', '万科A', '浦发银行', '邮储银行'],
        'area': ['深圳', '深圳', '上海', '北京'],
        'industry': ['银行', '房地产', '银行', '银行'],
        'market': ['主板', '主板', '主板', '主板'],
        'list_date': ['19910403', '19910129', '19991110', '20121220'],
        'is_hs': ['H', 'H', 'H', 'H']
    })


@pytest.fixture
def temp_directory():
    """创建临时目录用于测试"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ==================== fetch_akshare_stock_list 测试 ====================

class TestFetchAkshareStockList:
    """测试 fetch_akshare_stock_list 函数"""

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    @patch('src.a_stock_list_fetcher.logger')
    def test_fetch_akshare_success(self, mock_logger, mock_ak, sample_akshare_data, temp_directory):
        """测试成功获取AkShare数据"""
        mock_ak.return_value = sample_akshare_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_success()
        assert os.path.exists(save_path)
        assert result.data is not None
        assert len(result.data) == 6

        # 读取保存的文件验证
        saved_df = pd.read_csv(save_path)
        assert len(saved_df) == 6
        assert 'ts_code' in saved_df.columns
        assert 'symbol' in saved_df.columns
        assert 'name' in saved_df.columns
        assert 'market' in saved_df.columns
        assert 'exchange' in saved_df.columns

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_fetch_akshare_ts_code_generation(self, mock_ak, sample_akshare_data, temp_directory):
        """测试 ts_code 生成逻辑"""
        mock_ak.return_value = sample_akshare_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path, dtype={'symbol': str, 'ts_code': str})

        # 验证6开头的股票是SH
        sh_stocks = saved_df[saved_df['symbol'].str.startswith('6')]
        assert all(sh_stocks['ts_code'].str.endswith('.SH'))

        # 验证0/3/688开头的股票是SZ
        sz_stocks = saved_df[~saved_df['symbol'].str.startswith('6')]
        assert all(sz_stocks['ts_code'].str.endswith('.SZ'))

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_fetch_akshare_market_type_classification(self, mock_ak, sample_akshare_data, temp_directory):
        """测试市场类型分类"""
        mock_ak.return_value = sample_akshare_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path, dtype={'symbol': str})

        # 688开头 -> 科创板
        kcb_stocks = saved_df[saved_df['symbol'] == '688001']
        assert len(kcb_stocks) > 0 and kcb_stocks['market'].values[0] == '科创板'

        # 300开头 -> 创业板
        cyb_stocks = saved_df[saved_df['symbol'] == '300001']
        assert len(cyb_stocks) > 0 and cyb_stocks['market'].values[0] == '创业板'

        # 000开头 -> 主板
        zb_stocks = saved_df[saved_df['symbol'] == '000001']
        assert len(zb_stocks) > 0 and zb_stocks['market'].values[0] == '主板'

        # 600开头 -> 主板
        sh_stocks = saved_df[saved_df['symbol'] == '600000']
        assert len(sh_stocks) > 0 and sh_stocks['market'].values[0] == '主板'

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_fetch_akshare_exchange_detection(self, mock_ak, sample_akshare_data, temp_directory):
        """测试交易所判断"""
        mock_ak.return_value = sample_akshare_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path, dtype={'symbol': str})

        # 6开头 -> SSE (上交所)
        sse_stocks = saved_df[saved_df['symbol'].str.startswith('6')]
        assert len(sse_stocks) > 0 and all(sse_stocks['exchange'] == 'SSE')

        # 0/3开头 -> SZSE (深交所)
        sz_stocks = saved_df[~saved_df['symbol'].str.startswith('6')]
        assert len(sz_stocks) > 0 and all(sz_stocks['exchange'] == 'SZSE')

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    @patch('src.a_stock_list_fetcher.save_stock_list_to_database')
    def test_fetch_akshare_with_db_save(self, mock_save_db, mock_ak, sample_akshare_data, temp_directory):
        """测试保存到数据库"""
        from src.utils.response import Response
        mock_ak.return_value = sample_akshare_data
        mock_save_db.return_value = Response.success(message="数据库保存成功")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_akshare_stock_list(save_path=save_path, save_to_db=True)

        assert result.is_success()
        mock_save_db.assert_called_once()

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    @patch('src.a_stock_list_fetcher.logger')
    def test_fetch_akshare_exception_handling(self, mock_logger, mock_ak, temp_directory):
        """测试异常处理"""
        mock_ak.side_effect = Exception("Network error")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_error()
        assert result.error_code is not None
        mock_logger.error.assert_called()

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_fetch_akshare_sorted_output(self, mock_ak, sample_akshare_data, temp_directory):
        """测试输出按 ts_code 排序"""
        mock_ak.return_value = sample_akshare_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path)

        # 验证已排序
        assert saved_df['ts_code'].equals(saved_df['ts_code'].sort_values().reset_index(drop=True))


# ==================== fetch_tushare_stock_list 测试 ====================

class TestFetchTushareStockList:
    """测试 fetch_tushare_stock_list 函数"""

    @patch('src.a_stock_list_fetcher.ts')
    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', 'test_token')
    def test_fetch_tushare_success(self, mock_ts, sample_tushare_data, temp_directory):
        """测试成功获取Tushare数据"""
        mock_pro = Mock()
        mock_pro.stock_basic.return_value = sample_tushare_data
        mock_ts.pro_api.return_value = mock_pro

        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_tushare_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_success()
        assert os.path.exists(save_path)
        assert result.data is not None
        mock_ts.set_token.assert_called_once_with('test_token')

    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', '')
    @patch('src.a_stock_list_fetcher.logger')
    def test_fetch_tushare_no_token(self, mock_logger, temp_directory):
        """测试没有 token 的情况"""
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_tushare_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_error()
        assert result.error_code == "TUSHARE_TOKEN_NOT_CONFIGURED"
        mock_logger.error.assert_called()

    @patch('src.a_stock_list_fetcher.ts')
    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', 'test_token')
    @patch('src.a_stock_list_fetcher.save_stock_list_to_database')
    def test_fetch_tushare_with_db_save(self, mock_save_db, mock_ts, sample_tushare_data, temp_directory):
        """测试保存到数据库"""
        from src.utils.response import Response
        mock_pro = Mock()
        mock_pro.stock_basic.return_value = sample_tushare_data
        mock_ts.pro_api.return_value = mock_pro
        mock_save_db.return_value = Response.success(message="数据库保存成功")

        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_tushare_stock_list(save_path=save_path, save_to_db=True)

        assert result.is_success()
        mock_save_db.assert_called_once()

    @patch('src.a_stock_list_fetcher.ts')
    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', 'test_token')
    @patch('src.a_stock_list_fetcher.logger')
    def test_fetch_tushare_exception_handling(self, mock_logger, mock_ts, temp_directory):
        """测试异常处理"""
        mock_ts.pro_api.side_effect = Exception("API error")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_tushare_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_error()
        assert result.error_code is not None
        mock_logger.error.assert_called()


# ==================== fetch_and_save_a_stock_list 测试 ====================

class TestFetchAndSaveAStockList:
    """测试 fetch_and_save_a_stock_list 智能数据源选择"""

    @patch('src.a_stock_list_fetcher.fetch_akshare_stock_list')
    def test_fetch_default_akshare(self, mock_akshare, temp_directory):
        """测试默认使用 AkShare"""
        from src.utils.response import Response
        mock_akshare.return_value = Response.success(data=pd.DataFrame(), message="成功")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_and_save_a_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_success()
        mock_akshare.assert_called_once_with(save_path, False)

    @patch('src.a_stock_list_fetcher.fetch_akshare_stock_list')
    def test_fetch_explicit_akshare(self, mock_akshare, temp_directory):
        """测试显式指定 AkShare"""
        from src.utils.response import Response
        mock_akshare.return_value = Response.success(data=pd.DataFrame(), message="成功")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_and_save_a_stock_list(save_path=save_path, save_to_db=False, data_source='akshare')

        assert result.is_success()
        mock_akshare.assert_called_once()

    @patch('src.a_stock_list_fetcher.fetch_tushare_stock_list')
    def test_fetch_explicit_tushare(self, mock_tushare, temp_directory):
        """测试显式指定 Tushare"""
        from src.utils.response import Response
        mock_tushare.return_value = Response.success(data=pd.DataFrame(), message="成功")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_and_save_a_stock_list(save_path=save_path, save_to_db=False, data_source='tushare')

        assert result.is_success()
        mock_tushare.assert_called_once()

    @patch('src.a_stock_list_fetcher.fetch_akshare_stock_list')
    @patch('src.a_stock_list_fetcher.logger')
    def test_fetch_unknown_source_fallback(self, mock_logger, mock_akshare, temp_directory):
        """测试未知数据源回退到 AkShare"""
        from src.utils.response import Response
        mock_akshare.return_value = Response.success(data=pd.DataFrame(), message="成功")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_and_save_a_stock_list(save_path=save_path, save_to_db=False, data_source='unknown')

        assert result.is_success()
        mock_akshare.assert_called_once()
        mock_logger.warning.assert_called()


# ==================== save_stock_list_to_database 测试 ====================

class TestSaveStockListToDatabase:
    """测试 save_stock_list_to_database 函数"""

    @patch('src.a_stock_list_fetcher.pd.Timestamp')
    @patch('src.a_stock_list_fetcher.create_engine')
    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', {
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    })
    def test_save_to_database_success(self, mock_create_engine, mock_timestamp, sample_tushare_data):
        """测试成功保存到数据库"""
        # Mock Timestamp.now()
        mock_timestamp.now.return_value = pd.Timestamp('2026-01-29')

        # Mock engine and connection
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        result = save_stock_list_to_database(sample_tushare_data)

        assert result.is_success()
        assert result.metadata.get('n_saved') == len(sample_tushare_data)
        mock_create_engine.assert_called_once()

    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', None)
    @patch('src.a_stock_list_fetcher.logger')
    def test_save_to_database_no_config(self, mock_logger, sample_tushare_data):
        """测试没有数据库配置"""
        result = save_stock_list_to_database(sample_tushare_data)

        assert result.is_error()
        assert result.error_code == "DATABASE_CONFIG_NOT_SET"
        mock_logger.error.assert_called()

    @patch('src.a_stock_list_fetcher.create_engine')
    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', {
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    })
    @patch('src.a_stock_list_fetcher.logger')
    def test_save_to_database_connection_error(self, mock_logger, mock_create_engine, sample_tushare_data):
        """测试数据库连接错误"""
        mock_create_engine.side_effect = Exception("Connection failed")

        result = save_stock_list_to_database(sample_tushare_data)

        assert result.is_error()
        assert result.error_code is not None
        mock_logger.error.assert_called()


# ==================== get_a_stock_list_detailed 测试 ====================

class TestGetAStockListDetailed:
    """测试 get_a_stock_list_detailed 函数"""

    @patch('src.a_stock_list_fetcher.ts')
    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', 'test_token')
    def test_get_detailed_success(self, mock_ts, sample_tushare_data, temp_directory):
        """测试成功获取详细数据"""
        mock_pro = Mock()
        mock_pro.stock_basic.return_value = sample_tushare_data
        mock_ts.pro_api.return_value = mock_pro

        result = get_a_stock_list_detailed(save_dir=temp_directory, save_to_db=False)

        assert result.is_success()
        assert result.data is not None
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) > 0

    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', '')
    @patch('src.a_stock_list_fetcher.logger')
    def test_get_detailed_no_token(self, mock_logger, temp_directory):
        """测试没有 token"""
        result = get_a_stock_list_detailed(save_dir=temp_directory, save_to_db=False)

        assert result.is_error()
        assert result.error_code == "TUSHARE_TOKEN_NOT_CONFIGURED"
        mock_logger.error.assert_called()

    @patch('src.a_stock_list_fetcher.ts')
    @patch('src.a_stock_list_fetcher.TUSHARE_TOKEN', 'test_token')
    @patch('src.a_stock_list_fetcher.logger')
    def test_get_detailed_exception(self, mock_logger, mock_ts, temp_directory):
        """测试异常处理"""
        mock_ts.pro_api.side_effect = Exception("API error")

        result = get_a_stock_list_detailed(save_dir=temp_directory, save_to_db=False)

        assert result.is_error()
        assert result.error_code is not None
        mock_logger.error.assert_called()


# ==================== update_stock_list_from_database 测试 ====================

class TestUpdateStockListFromDatabase:
    """测试 update_stock_list_from_database 函数"""

    @patch('src.a_stock_list_fetcher.create_engine')
    @patch('src.a_stock_list_fetcher.pd.read_sql')
    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', {
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    })
    def test_update_from_database_success(self, mock_read_sql, mock_create_engine, sample_tushare_data):
        """测试成功从数据库读取"""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        mock_read_sql.return_value = sample_tushare_data

        result = update_stock_list_from_database()

        assert result.is_success()
        assert result.data is not None
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == len(sample_tushare_data)

    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', None)
    @patch('src.a_stock_list_fetcher.logger')
    def test_update_from_database_no_config(self, mock_logger):
        """测试没有数据库配置"""
        result = update_stock_list_from_database()

        assert result.is_error()
        assert result.error_code == "DATABASE_CONFIG_NOT_SET"
        mock_logger.error.assert_called()

    @patch('src.a_stock_list_fetcher.create_engine')
    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', {
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    })
    @patch('src.a_stock_list_fetcher.logger')
    def test_update_from_database_exception(self, mock_logger, mock_create_engine):
        """测试数据库读取异常"""
        mock_create_engine.side_effect = Exception("Connection failed")

        result = update_stock_list_from_database()

        assert result.is_error()
        assert result.error_code is not None
        mock_logger.error.assert_called()


# ==================== 市场类型判断边界测试 ====================

class TestMarketTypeClassification:
    """测试市场类型分类的边界情况"""

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_market_type_689_code(self, mock_ak, temp_directory):
        """测试689开头的科创板"""
        test_data = pd.DataFrame({
            '代码': pd.Series(['689001'], dtype='str'),
            '名称': pd.Series(['测试股票'], dtype='str')
        })
        mock_ak.return_value = test_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path)
        assert saved_df['market'].iloc[0] == '科创板'

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_market_type_001_code(self, mock_ak, temp_directory):
        """测试001开头的主板"""
        test_data = pd.DataFrame({
            '代码': pd.Series(['001001'], dtype='str'),
            '名称': pd.Series(['测试股票'], dtype='str')
        })
        mock_ak.return_value = test_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path)
        assert saved_df['market'].iloc[0] == '主板'

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_market_type_002_code(self, mock_ak, temp_directory):
        """测试002开头的中小板"""
        test_data = pd.DataFrame({
            '代码': pd.Series(['002001'], dtype='str'),
            '名称': pd.Series(['测试股票'], dtype='str')
        })
        mock_ak.return_value = test_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path)
        assert saved_df['market'].iloc[0] == '中小板'

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_market_type_601_603_code(self, mock_ak, temp_directory):
        """测试601和603开头的主板"""
        test_data = pd.DataFrame({
            '代码': pd.Series(['601001', '603001'], dtype='str'),
            '名称': pd.Series(['测试股票1', '测试股票2'], dtype='str')
        })
        mock_ak.return_value = test_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path)
        assert all(saved_df['market'] == '主板')

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_market_type_unknown_code(self, mock_ak, temp_directory):
        """测试未知开头的股票代码"""
        test_data = pd.DataFrame({
            '代码': pd.Series(['999001'], dtype='str'),
            '名称': pd.Series(['测试股票'], dtype='str')
        })
        mock_ak.return_value = test_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        saved_df = pd.read_csv(save_path)
        assert saved_df['market'].iloc[0] == '其他'


# ==================== 边界情况和异常测试 ====================

class TestEdgeCases:
    """测试边界情况和异常处理"""

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    @patch('src.a_stock_list_fetcher.logger')
    def test_fetch_akshare_empty_data(self, mock_logger, mock_ak, temp_directory):
        """测试空数据集"""
        # 空DataFrame会导致KeyError，因为缺少'代码'列
        mock_ak.return_value = pd.DataFrame()
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        # 空数据会导致失败
        assert result.is_error()
        assert result.error_code == "AKSHARE_DATA_FORMAT_ERROR"
        mock_logger.error.assert_called()

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_fetch_akshare_directory_creation(self, mock_ak, sample_akshare_data):
        """测试自动创建目录"""
        mock_ak.return_value = sample_akshare_data

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'new_dir', 'test_stock_list.csv')

            result = fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

            assert result.is_success()
            assert os.path.exists(save_path)

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    def test_fetch_akshare_large_dataset(self, mock_ak, temp_directory):
        """测试大数据集处理"""
        # 模拟5000只股票
        large_data = pd.DataFrame({
            '代码': pd.Series([f'{i:06d}' for i in range(5000)], dtype='str'),
            '名称': pd.Series([f'股票{i}' for i in range(5000)], dtype='str')
        })
        mock_ak.return_value = large_data
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_akshare_stock_list(save_path=save_path, save_to_db=False)

        assert result.is_success()
        assert result.metadata.get('n_stocks') == 5000
        saved_df = pd.read_csv(save_path)
        assert len(saved_df) == 5000


# ==================== 集成测试 ====================

class TestIntegration:
    """集成测试"""

    @patch('src.a_stock_list_fetcher.pd.Timestamp')
    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    @patch('src.a_stock_list_fetcher.create_engine')
    @patch('src.a_stock_list_fetcher.DATABASE_CONFIG', {
        'host': 'localhost',
        'port': 5432,
        'database': 'testdb',
        'user': 'testuser',
        'password': 'testpass'
    })
    def test_full_workflow_akshare_to_db(self, mock_create_engine, mock_ak, mock_timestamp, sample_akshare_data, temp_directory):
        """测试完整工作流：AkShare -> CSV + 数据库"""
        mock_ak.return_value = sample_akshare_data
        mock_timestamp.now.return_value = pd.Timestamp('2026-01-29')

        mock_engine = MagicMock()
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_engine.connect.return_value.__exit__ = Mock(return_value=False)
        mock_conn.execute = Mock()
        mock_create_engine.return_value = mock_engine

        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_and_save_a_stock_list(
            save_path=save_path,
            save_to_db=True,
            data_source='akshare'
        )

        assert result.is_success()
        assert os.path.exists(save_path)
        assert result.metadata.get('db_saved') is True
        mock_create_engine.assert_called_once()

    @patch('src.a_stock_list_fetcher.ak.stock_zh_a_spot_em')
    @patch('src.a_stock_list_fetcher.save_stock_list_to_database')
    @patch('src.a_stock_list_fetcher.logger')
    def test_csv_success_db_failure(self, mock_logger, mock_save_db, mock_ak, sample_akshare_data, temp_directory):
        """测试CSV成功但数据库失败的情况"""
        from src.utils.response import Response
        mock_ak.return_value = sample_akshare_data
        mock_save_db.return_value = Response.error(error="数据库连接失败", error_code="DB_ERROR")
        save_path = os.path.join(temp_directory, 'test_stock_list.csv')

        result = fetch_akshare_stock_list(save_path=save_path, save_to_db=True)

        # 主函数返回成功（CSV成功）
        assert result.is_success()
        # 但数据库保存失败
        assert result.metadata.get('db_saved') is False
        # 但应该有错误日志
        mock_logger.error.assert_called()
