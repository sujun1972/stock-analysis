"""
测试 AkShare 配置模块
"""

import pytest
from src.providers.akshare.config import AkShareConfig, AkShareFields, AkShareNotes


class TestAkShareConfig:
    """测试 AkShareConfig 配置类"""

    def test_default_parameters(self):
        """测试默认参数配置"""
        assert AkShareConfig.DEFAULT_TIMEOUT == 30
        assert AkShareConfig.DEFAULT_RETRY_COUNT == 3
        assert AkShareConfig.DEFAULT_RETRY_DELAY == 1
        assert AkShareConfig.DEFAULT_REQUEST_DELAY == 0.3

    def test_data_range_defaults(self):
        """测试数据范围默认值"""
        assert AkShareConfig.DEFAULT_HISTORY_DAYS == 365
        assert AkShareConfig.DEFAULT_NEW_STOCK_DAYS == 30
        assert AkShareConfig.DEFAULT_MINUTE_DAYS == 5

    def test_minute_period_map(self):
        """测试分钟周期映射"""
        period_map = AkShareConfig.MINUTE_PERIOD_MAP
        assert period_map['1'] == '1'
        assert period_map['5'] == '5'
        assert period_map['15'] == '15'
        assert period_map['30'] == '30'
        assert period_map['60'] == '60'

    def test_adjust_map(self):
        """测试复权方式映射"""
        adjust_map = AkShareConfig.ADJUST_MAP
        assert adjust_map['qfq'] == 'qfq'
        assert adjust_map['hfq'] == 'hfq'
        assert adjust_map[''] == ''

    def test_parse_market_from_code_shanghai(self):
        """测试上海市场代码解析"""
        assert AkShareConfig.parse_market_from_code('600000') == '上海主板'
        assert AkShareConfig.parse_market_from_code('601000') == '上海主板'
        assert AkShareConfig.parse_market_from_code('688001') == '科创板'

    def test_parse_market_from_code_shenzhen(self):
        """测试深圳市场代码解析"""
        assert AkShareConfig.parse_market_from_code('000001') == '深圳主板'
        assert AkShareConfig.parse_market_from_code('001000') == '深圳主板'
        assert AkShareConfig.parse_market_from_code('002000') == '深圳主板'

    def test_parse_market_from_code_chinext(self):
        """测试创业板代码解析"""
        assert AkShareConfig.parse_market_from_code('300001') == '创业板'

    def test_parse_market_from_code_star(self):
        """测试科创板代码解析"""
        assert AkShareConfig.parse_market_from_code('688000') == '科创板'

    def test_parse_market_from_code_bse(self):
        """测试北交所代码解析"""
        assert AkShareConfig.parse_market_from_code('830000') == '北交所'
        assert AkShareConfig.parse_market_from_code('430000') == '北交所'

    def test_parse_market_from_code_invalid(self):
        """测试无效代码解析"""
        assert AkShareConfig.parse_market_from_code('999999') == '其他'
        assert AkShareConfig.parse_market_from_code('') == '其他'
        assert AkShareConfig.parse_market_from_code(None) == '其他'
        assert AkShareConfig.parse_market_from_code(123) == '其他'


class TestAkShareFields:
    """测试 AkShareFields 字段映射类"""

    def test_stock_list_fields(self):
        """测试股票列表字段"""
        assert 'code' in AkShareFields.STOCK_LIST_RENAME
        assert 'name' in AkShareFields.STOCK_LIST_RENAME
        assert AkShareFields.STOCK_LIST_OUTPUT == ['code', 'name', 'market', 'status']

    def test_daily_data_fields(self):
        """测试日线数据字段"""
        rename = AkShareFields.DAILY_DATA_RENAME
        assert rename['日期'] == 'trade_date'
        assert rename['开盘'] == 'open'
        assert rename['最高'] == 'high'
        assert rename['最低'] == 'low'
        assert rename['收盘'] == 'close'
        assert rename['成交量'] == 'volume'
        assert rename['成交额'] == 'amount'

        output = AkShareFields.DAILY_DATA_OUTPUT
        assert 'trade_date' in output
        assert 'open' in output
        assert 'high' in output
        assert 'low' in output
        assert 'close' in output

    def test_minute_data_fields(self):
        """测试分时数据字段"""
        rename = AkShareFields.MINUTE_DATA_RENAME
        assert rename['时间'] == 'trade_time'
        assert rename['开盘'] == 'open'
        assert rename['收盘'] == 'close'

        output = AkShareFields.MINUTE_DATA_OUTPUT
        assert 'trade_time' in output
        assert 'period' in output
        assert 'open' in output

    def test_realtime_quote_fields(self):
        """测试实时行情字段"""
        rename = AkShareFields.REALTIME_QUOTE_RENAME
        assert rename['代码'] == 'code'
        assert rename['名称'] == 'name'
        assert rename['最新价'] == 'latest_price'

        output = AkShareFields.REALTIME_QUOTE_OUTPUT
        assert 'code' in output
        assert 'name' in output
        assert 'latest_price' in output
        assert 'trade_time' in output

    def test_new_stock_fields(self):
        """测试新股字段"""
        rename = AkShareFields.NEW_STOCK_RENAME
        assert rename['代码'] == 'code'
        assert rename['名称'] == 'name'
        assert rename['上市日期'] == 'list_date'

        output = AkShareFields.NEW_STOCK_OUTPUT
        assert 'code' in output
        assert 'list_date' in output

    def test_delisted_stock_fields(self):
        """测试退市股票字段"""
        rename_sh = AkShareFields.DELISTED_STOCK_RENAME_SH
        assert rename_sh['公司代码'] == 'code'
        assert rename_sh['暂停上市日期'] == 'delist_date'

        rename_sz = AkShareFields.DELISTED_STOCK_RENAME_SZ
        assert rename_sz['公司代码'] == 'code'
        assert rename_sz['终止上市日期'] == 'delist_date'

        output = AkShareFields.DELISTED_STOCK_OUTPUT
        assert 'delist_date' in output


class TestAkShareNotes:
    """测试 AkShareNotes 注意事项类"""

    def test_notes_exist(self):
        """测试注意事项文本存在"""
        assert isinstance(AkShareNotes.RATE_LIMIT_WARNING, str)
        assert isinstance(AkShareNotes.REALTIME_QUOTE_WARNING, str)
        assert isinstance(AkShareNotes.DATA_SOURCE_INFO, str)

    def test_rate_limit_warning_content(self):
        """测试限流警告内容"""
        warning = AkShareNotes.RATE_LIMIT_WARNING
        assert 'IP 限流' in warning or '限流' in warning
        assert '0.3' in warning

    def test_realtime_quote_warning_content(self):
        """测试实时行情警告内容"""
        warning = AkShareNotes.REALTIME_QUOTE_WARNING
        assert '实时行情' in warning
        assert '58' in warning or '分钟' in warning

    def test_data_source_info_content(self):
        """测试数据源信息内容"""
        info = AkShareNotes.DATA_SOURCE_INFO
        assert '东方财富' in info or '数据来源' in info
