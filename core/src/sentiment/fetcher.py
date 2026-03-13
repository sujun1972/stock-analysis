"""
市场情绪数据抓取器

负责从配置的数据源抓取市场情绪相关数据。
支持通过admin配置数据源（akshare/tushare）
"""

import pandas as pd
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from loguru import logger

from ..database.connection_pool_manager import ConnectionPoolManager
from ..config.data_source_helper import create_provider, get_data_source_config
from .models import (
    MarketIndices,
    LimitUpPool,
    DragonTigerRecord,
    TradingCalendar,
    SentimentSyncResult
)


class SentimentDataFetcher:
    """市场情绪数据抓取器（支持配置化数据源）"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化

        Args:
            pool_manager: 数据库连接池管理器
        """
        self.pool_manager = pool_manager
        self.rate_limit_delay = 0.3  # 数据源限流延迟（秒）

        # 从配置获取数据源
        self.config = get_data_source_config()
        self.data_source = self.config["data_source"]

        # 创建数据提供者
        try:
            self.provider = create_provider("data")
            logger.info(f"✓ 情绪数据抓取器初始化成功，使用数据源: {self.data_source}")
        except Exception as e:
            logger.warning(f"创建数据提供者失败，将在需要时重试: {e}")
            self.provider = None

    # ========== 1. 交易日历相关 ==========

    def sync_trading_calendar(self, year: int) -> int:
        """
        同步指定年份的交易日历

        Args:
            year: 年份

        Returns:
            同步的交易日数量
        """
        try:
            logger.info(f"开始同步{year}年交易日历...")

            # 使用配置的数据源获取交易日历
            if self.data_source == "akshare":
                import akshare as ak
                df = ak.tool_trade_date_hist_sina()
            elif self.data_source == "tushare":
                # Tushare获取交易日历
                df = self.provider.api_client.query(
                    'trade_cal',
                    exchange='SSE',
                    start_date=f'{year}0101',
                    end_date=f'{year}1231',
                    is_open='1'
                )
                # 转换为统一格式
                df = df.rename(columns={'cal_date': 'trade_date'})
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            else:
                raise ValueError(f"不支持的数据源: {self.data_source}")

            # 过滤指定年份
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df_year = df[df['trade_date'].dt.year == year].copy()

            if df_year.empty:
                logger.warning(f"{year}年没有交易日历数据")
                return 0

            # 插入数据库
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            inserted_count = 0
            for _, row in df_year.iterrows():
                trade_date = row['trade_date'].strftime('%Y-%m-%d')

                cursor.execute("""
                    INSERT INTO trading_calendar (trade_date, is_trading_day, exchange, day_type)
                    VALUES (%s, true, 'SSE', '工作日')
                    ON CONFLICT (trade_date) DO NOTHING
                """, (trade_date,))

                inserted_count += cursor.rowcount

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"{year}年交易日历同步完成，插入{inserted_count}条记录 (数据源: {self.data_source})")
            return inserted_count

        except Exception as e:
            logger.error(f"同步交易日历失败: {e}")
            raise

    def is_trading_day(self, date_str: str) -> bool:
        """
        判断是否为交易日

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)

        Returns:
            是否为交易日
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT is_trading_day FROM trading_calendar WHERE trade_date = %s
            """, (date_str,))

            result = cursor.fetchone()
            cursor.close()
            self.pool_manager.release_connection(conn)

            if result:
                return result[0]
            else:
                # 如果数据库中没有，简单判断是否周末
                dt = datetime.strptime(date_str, '%Y-%m-%d')
                is_weekday = dt.weekday() < 5
                logger.warning(f"{date_str}不在交易日历中，使用简单周末判断: {is_weekday}")
                return is_weekday

        except Exception as e:
            logger.error(f"查询交易日失败: {e}")
            return False

    # ========== 2. 大盘基础数据相关 ==========

    def fetch_market_indices(self, date_str: Optional[str] = None) -> MarketIndices:
        """
        抓取三大指数数据

        Args:
            date_str: 日期字符串，None表示最新

        Returns:
            大盘指数数据
        """
        try:
            logger.info(f"开始抓取大盘指数数据 (数据源: {self.data_source})...")

            if not date_str:
                date_str = datetime.now().strftime('%Y-%m-%d')

            # 使用配置的数据源获取指数数据
            if self.data_source == "akshare":
                import akshare as ak
                df = ak.stock_zh_index_spot_em()

                # 查找三大指数
                sh_data = df[df['代码'] == '000001'].iloc[0] if '000001' in df['代码'].values else None
                sz_data = df[df['代码'] == '399001'].iloc[0] if '399001' in df['代码'].values else None
                cyb_data = df[df['代码'] == '399006'].iloc[0] if '399006' in df['代码'].values else None

                market_indices = MarketIndices(
                    trade_date=date_str,
                    # 上证指数
                    sh_index_close=float(sh_data['最新价']) if sh_data is not None else 0.0,
                    sh_index_change=float(sh_data['涨跌幅']) if sh_data is not None else 0.0,
                    sh_index_amplitude=float(sh_data['振幅']) if sh_data is not None else 0.0,
                    sh_index_volume=int(sh_data['成交量']) if sh_data is not None else 0,
                    sh_index_amount=float(sh_data['成交额']) if sh_data is not None else 0.0,
                    # 深成指数
                    sz_index_close=float(sz_data['最新价']) if sz_data is not None else 0.0,
                    sz_index_change=float(sz_data['涨跌幅']) if sz_data is not None else 0.0,
                    sz_index_amplitude=float(sz_data['振幅']) if sz_data is not None else 0.0,
                    sz_index_volume=int(sz_data['成交量']) if sz_data is not None else 0,
                    sz_index_amount=float(sz_data['成交额']) if sz_data is not None else 0.0,
                    # 创业板指数
                    cyb_index_close=float(cyb_data['最新价']) if cyb_data is not None else 0.0,
                    cyb_index_change=float(cyb_data['涨跌幅']) if cyb_data is not None else 0.0,
                    cyb_index_amplitude=float(cyb_data['振幅']) if cyb_data is not None else 0.0,
                    cyb_index_volume=int(cyb_data['成交量']) if cyb_data is not None else 0,
                    cyb_index_amount=float(cyb_data['成交额']) if cyb_data is not None else 0.0,
                )

            elif self.data_source == "tushare":
                # Tushare获取指数行情
                indices = ['000001.SH', '399001.SZ', '399006.SZ']  # 上证、深成、创业板
                df = self.provider.api_client.query(
                    'index_daily',
                    ts_code=','.join(indices),
                    trade_date=date_str.replace('-', ''),
                )

                # 解析数据
                sh_data = df[df['ts_code'] == '000001.SH'].iloc[0] if len(df[df['ts_code'] == '000001.SH']) > 0 else None
                sz_data = df[df['ts_code'] == '399001.SZ'].iloc[0] if len(df[df['ts_code'] == '399001.SZ']) > 0 else None
                cyb_data = df[df['ts_code'] == '399006.SZ'].iloc[0] if len(df[df['ts_code'] == '399006.SZ']) > 0 else None

                market_indices = MarketIndices(
                    trade_date=date_str,
                    # 上证指数
                    sh_index_close=float(sh_data['close']) if sh_data is not None else 0.0,
                    sh_index_change=float(sh_data['pct_chg']) if sh_data is not None else 0.0,
                    sh_index_amplitude=0.0,  # Tushare没有振幅字段
                    sh_index_volume=int(sh_data['vol']) if sh_data is not None else 0,
                    sh_index_amount=float(sh_data['amount']) if sh_data is not None else 0.0,
                    # 深成指数
                    sz_index_close=float(sz_data['close']) if sz_data is not None else 0.0,
                    sz_index_change=float(sz_data['pct_chg']) if sz_data is not None else 0.0,
                    sz_index_amplitude=0.0,
                    sz_index_volume=int(sz_data['vol']) if sz_data is not None else 0,
                    sz_index_amount=float(sz_data['amount']) if sz_data is not None else 0.0,
                    # 创业板指数
                    cyb_index_close=float(cyb_data['close']) if cyb_data is not None else 0.0,
                    cyb_index_change=float(cyb_data['pct_chg']) if cyb_data is not None else 0.0,
                    cyb_index_amplitude=0.0,
                    cyb_index_volume=int(cyb_data['vol']) if cyb_data is not None else 0,
                    cyb_index_amount=float(cyb_data['amount']) if cyb_data is not None else 0.0,
                )
            else:
                raise ValueError(f"不支持的数据源: {self.data_source}")

            # 计算两市总成交
            market_indices.total_volume = (
                market_indices.sh_index_volume + market_indices.sz_index_volume
            )
            market_indices.total_amount = (
                market_indices.sh_index_amount + market_indices.sz_index_amount
            )

            logger.success(f"大盘指数数据抓取成功: 上证{market_indices.sh_index_close}, "
                          f"深成{market_indices.sz_index_close}, 创业板{market_indices.cyb_index_close}")

            return market_indices

        except Exception as e:
            logger.error(f"抓取大盘指数失败: {e}")
            raise

    def save_market_indices(self, data: MarketIndices) -> bool:
        """
        保存大盘指数数据到数据库

        Args:
            data: 大盘指数数据

        Returns:
            是否成功
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO market_sentiment_daily (
                    trade_date,
                    sh_index_code, sh_index_close, sh_index_change, sh_index_amplitude,
                    sh_index_volume, sh_index_amount,
                    sz_index_code, sz_index_close, sz_index_change, sz_index_amplitude,
                    sz_index_volume, sz_index_amount,
                    cyb_index_code, cyb_index_close, cyb_index_change, cyb_index_amplitude,
                    cyb_index_volume, cyb_index_amount,
                    total_volume, total_amount
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (trade_date)
                DO UPDATE SET
                    sh_index_close = EXCLUDED.sh_index_close,
                    sh_index_change = EXCLUDED.sh_index_change,
                    sh_index_amplitude = EXCLUDED.sh_index_amplitude,
                    sh_index_volume = EXCLUDED.sh_index_volume,
                    sh_index_amount = EXCLUDED.sh_index_amount,
                    sz_index_close = EXCLUDED.sz_index_close,
                    sz_index_change = EXCLUDED.sz_index_change,
                    sz_index_amplitude = EXCLUDED.sz_index_amplitude,
                    sz_index_volume = EXCLUDED.sz_index_volume,
                    sz_index_amount = EXCLUDED.sz_index_amount,
                    cyb_index_close = EXCLUDED.cyb_index_close,
                    cyb_index_change = EXCLUDED.cyb_index_change,
                    cyb_index_amplitude = EXCLUDED.cyb_index_amplitude,
                    cyb_index_volume = EXCLUDED.cyb_index_volume,
                    cyb_index_amount = EXCLUDED.cyb_index_amount,
                    total_volume = EXCLUDED.total_volume,
                    total_amount = EXCLUDED.total_amount,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                data.trade_date,
                data.sh_index_code, data.sh_index_close, data.sh_index_change, data.sh_index_amplitude,
                data.sh_index_volume, data.sh_index_amount,
                data.sz_index_code, data.sz_index_close, data.sz_index_change, data.sz_index_amplitude,
                data.sz_index_volume, data.sz_index_amount,
                data.cyb_index_code, data.cyb_index_close, data.cyb_index_change, data.cyb_index_amplitude,
                data.cyb_index_volume, data.cyb_index_amount,
                data.total_volume, data.total_amount
            ))

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"大盘指数数据已保存: {data.trade_date}")
            return True

        except Exception as e:
            logger.error(f"保存大盘指数数据失败: {e}")
            return False

    # ========== 3. 涨停板情绪池相关 ==========

    def _filter_st_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        剔除ST、*ST、退市股

        Args:
            df: 股票数据

        Returns:
            过滤后的数据
        """
        if '名称' in df.columns:
            df = df[~df['名称'].str.contains('ST|退|N', na=False)]
        if '代码' in df.columns:
            # 剔除北交所（4开头）
            df = df[~df['代码'].str.startswith('4')]

        return df

    def _calculate_continuous_ladder(self, df: pd.DataFrame) -> Tuple[Dict[str, int], int, int]:
        """
        计算连板天梯树

        Args:
            df: 涨停板数据（包含连板天数列）

        Returns:
            (连板天梯树, 最高连板天数, 最高连板股票数)
        """
        ladder = {}
        max_days = 0
        max_count = 0

        if '连板天数' in df.columns:
            for days in range(2, 11):  # 2-10连板
                if days < 10:
                    count = len(df[df['连板天数'] == days])
                else:
                    # 10连板及以上
                    count = len(df[df['连板天数'] >= days])

                if count > 0:
                    key = f"{days}连板" if days < 10 else "10连板及以上"
                    ladder[key] = int(count)

                    if days > max_days:
                        max_days = days
                        max_count = count

        return ladder, max_days, max_count

    def fetch_limit_up_pool(self, date_str: Optional[str] = None) -> LimitUpPool:
        """
        抓取涨停板池数据

        注意：涨停板池是AkShare特有功能，如果配置了Tushare会自动降级使用AkShare

        Args:
            date_str: 日期字符串

        Returns:
            涨停板情绪池数据
        """
        try:
            logger.info("开始抓取涨停板池数据...")

            if not date_str:
                date_str = datetime.now().strftime('%Y-%m-%d')

            # 涨停板池是AkShare特有功能，即使配置了Tushare也使用AkShare
            if self.data_source == "tushare":
                logger.warning("涨停板池功能仅AkShare支持，自动降级使用AkShare")

            import akshare as ak

            # 1. 获取涨停板池
            df_limit_up = ak.stock_zt_pool_em(date=date_str.replace('-', ''))
            df_limit_up = self._filter_st_stocks(df_limit_up)

            # 2. 获取炸板数据
            try:
                df_blast = ak.stock_zt_pool_dtgc_em(date=date_str.replace('-', ''))
                df_blast = self._filter_st_stocks(df_blast)
                blast_count = len(df_blast)
            except Exception as e:
                logger.warning(f"获取炸板数据失败: {e}")
                df_blast = pd.DataFrame()
                blast_count = 0

            # 3. 计算统计数据
            limit_up_count = len(df_limit_up)
            blast_rate = blast_count / (blast_count + limit_up_count) if (blast_count + limit_up_count) > 0 else 0

            # 4. 计算连板天梯
            continuous_ladder, max_days, max_count = self._calculate_continuous_ladder(df_limit_up)

            # 5. 提取涨停股票列表
            limit_up_stocks = []
            if not df_limit_up.empty:
                for _, row in df_limit_up.head(100).iterrows():  # 最多100只
                    limit_up_stocks.append({
                        'code': str(row.get('代码', '')),
                        'name': str(row.get('名称', '')),
                        'days': int(row.get('连板天数', 1)),
                        'reason': str(row.get('涨停原因', '')),
                        'first_limit_time': str(row.get('首次封板时间', ''))
                    })

            # 6. 提取炸板股票列表
            blast_stocks = []
            if not df_blast.empty:
                for _, row in df_blast.head(100).iterrows():
                    blast_stocks.append({
                        'code': str(row.get('代码', '')),
                        'name': str(row.get('名称', '')),
                        'blast_times': int(row.get('炸板次数', 1)),
                        'final_change': float(row.get('最新涨跌幅', 0))
                    })

            # 7. 获取跌停数据（尝试）
            limit_down_count = 0
            try:
                df_limit_down = ak.stock_zt_pool_dtgc_em(date=date_str.replace('-', ''))
                limit_down_count = len(self._filter_st_stocks(df_limit_down))
            except:
                pass

            pool_data = LimitUpPool(
                trade_date=date_str,
                limit_up_count=limit_up_count,
                limit_down_count=limit_down_count,
                blast_count=blast_count,
                blast_rate=round(blast_rate, 4),
                max_continuous_days=max_days,
                max_continuous_count=max_count,
                continuous_ladder=continuous_ladder,
                limit_up_stocks=limit_up_stocks,
                blast_stocks=blast_stocks
            )

            logger.success(f"涨停板池数据抓取成功: 涨停{limit_up_count}只, 炸板{blast_count}只, "
                          f"炸板率{blast_rate:.2%}, 最高{max_days}连板")

            return pool_data

        except Exception as e:
            logger.error(f"抓取涨停板池失败: {e}")
            raise

    def save_limit_up_pool(self, data: LimitUpPool) -> bool:
        """
        保存涨停板池数据到数据库

        Args:
            data: 涨停板池数据

        Returns:
            是否成功
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO limit_up_pool (
                    trade_date, limit_up_count, limit_down_count, blast_count, blast_rate,
                    max_continuous_days, max_continuous_count, continuous_ladder,
                    limit_up_stocks, blast_stocks
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (trade_date)
                DO UPDATE SET
                    limit_up_count = EXCLUDED.limit_up_count,
                    limit_down_count = EXCLUDED.limit_down_count,
                    blast_count = EXCLUDED.blast_count,
                    blast_rate = EXCLUDED.blast_rate,
                    max_continuous_days = EXCLUDED.max_continuous_days,
                    max_continuous_count = EXCLUDED.max_continuous_count,
                    continuous_ladder = EXCLUDED.continuous_ladder,
                    limit_up_stocks = EXCLUDED.limit_up_stocks,
                    blast_stocks = EXCLUDED.blast_stocks,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                data.trade_date,
                data.limit_up_count,
                data.limit_down_count,
                data.blast_count,
                data.blast_rate,
                data.max_continuous_days,
                data.max_continuous_count,
                json.dumps(data.continuous_ladder, ensure_ascii=False),
                json.dumps(data.limit_up_stocks, ensure_ascii=False),
                json.dumps(data.blast_stocks, ensure_ascii=False)
            ))

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"涨停板池数据已保存: {data.trade_date}")
            return True

        except Exception as e:
            logger.error(f"保存涨停板池数据失败: {e}")
            return False

    # ========== 4. 龙虎榜相关 ==========

    def fetch_dragon_tiger_list(self, date_str: str) -> List[DragonTigerRecord]:
        """
        抓取龙虎榜数据（包含席位明细）

        注意：龙虎榜详细数据是AkShare特有功能，如果配置了Tushare会自动降级使用AkShare

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)

        Returns:
            龙虎榜记录列表
        """
        try:
            logger.info(f"开始抓取龙虎榜数据: {date_str}")

            # 龙虎榜详细数据是AkShare特有功能，即使配置了Tushare也使用AkShare
            if self.data_source == "tushare":
                logger.warning("龙虎榜详细数据仅AkShare支持，自动降级使用AkShare")

            import akshare as ak

            # 获取龙虎榜数据（使用start_date和end_date查询单日数据）
            date_formatted = date_str.replace('-', '')
            df = ak.stock_lhb_detail_em(start_date=date_formatted, end_date=date_formatted)

            if df.empty:
                logger.info(f"{date_str}没有龙虎榜数据")
                return []

            records = []

            # 遍历每条记录（这是汇总数据，每行一只股票）
            for idx, row in df.iterrows():
                stock_code = str(row.get('代码', ''))

                # 使用龙虎榜买入额、卖出额、净买额
                buy_amount = float(row.get('龙虎榜买入额', 0))
                sell_amount = float(row.get('龙虎榜卖出额', 0))
                net_amount = float(row.get('龙虎榜净买额', 0))

                # 获取席位明细
                top_buyers = []
                top_sellers = []
                has_institution = False
                institution_count = 0

                try:
                    import akshare as ak
                    # 抓取买入席位（前5名）
                    time.sleep(0.3)  # 限速
                    df_buy = ak.stock_lhb_stock_detail_em(symbol=stock_code, date=date_formatted, flag='买入')
                    if not df_buy.empty:
                        for rank, seat_row in df_buy.iterrows():
                            seat_name = str(seat_row.get('交易营业部名称', ''))
                            # 处理NaN值：使用pd.isna检查，将NaN转换为0
                            seat_buy_raw = seat_row.get('买入金额', 0)
                            seat_sell_raw = seat_row.get('卖出金额', 0)
                            seat_net_raw = seat_row.get('净额', 0)

                            seat_buy = 0.0 if pd.isna(seat_buy_raw) else float(seat_buy_raw)
                            seat_sell = 0.0 if pd.isna(seat_sell_raw) else float(seat_sell_raw)
                            seat_net = 0.0 if pd.isna(seat_net_raw) else float(seat_net_raw)

                            top_buyers.append({
                                'rank': rank + 1,
                                'name': seat_name,
                                'buy_amount': seat_buy,
                                'sell_amount': seat_sell,
                                'net_amount': seat_net
                            })

                            # 检测机构席位
                            if '机构' in seat_name:
                                has_institution = True
                                institution_count += 1

                    # 抓取卖出席位（前5名）
                    time.sleep(0.3)  # 限速
                    df_sell = ak.stock_lhb_stock_detail_em(symbol=stock_code, date=date_formatted, flag='卖出')
                    if not df_sell.empty:
                        for rank, seat_row in df_sell.iterrows():
                            seat_name = str(seat_row.get('交易营业部名称', ''))
                            # 处理NaN值
                            seat_buy_raw = seat_row.get('买入金额', 0)
                            seat_sell_raw = seat_row.get('卖出金额', 0)
                            seat_net_raw = seat_row.get('净额', 0)

                            seat_buy = 0.0 if pd.isna(seat_buy_raw) else float(seat_buy_raw)
                            seat_sell = 0.0 if pd.isna(seat_sell_raw) else float(seat_sell_raw)
                            seat_net = 0.0 if pd.isna(seat_net_raw) else float(seat_net_raw)

                            top_sellers.append({
                                'rank': rank + 1,
                                'name': seat_name,
                                'buy_amount': seat_buy,
                                'sell_amount': seat_sell,
                                'net_amount': seat_net
                            })

                            # 检测机构席位（卖方）
                            if '机构' in seat_name and seat_name not in [b['name'] for b in top_buyers]:
                                has_institution = True
                                institution_count += 1

                    logger.debug(f"[{stock_code}] 获取席位明细: 买方{len(top_buyers)}席, 卖方{len(top_sellers)}席, 机构{institution_count}家")

                except Exception as seat_err:
                    logger.warning(f"[{stock_code}] 获取席位明细失败: {seat_err}")

                record = DragonTigerRecord(
                    trade_date=date_str,
                    stock_code=stock_code,
                    stock_name=str(row.get('名称', '')),
                    reason=str(row.get('上榜原因', '')),
                    reason_type=self._classify_lhb_reason(str(row.get('上榜原因', ''))),
                    close_price=float(row.get('收盘价', 0)),
                    price_change=float(row.get('涨跌幅', 0)),
                    turnover_rate=float(row.get('换手率', 0)),
                    buy_amount=buy_amount,
                    sell_amount=sell_amount,
                    net_amount=net_amount,
                    top_buyers=top_buyers,
                    top_sellers=top_sellers,
                    has_institution=has_institution,
                    institution_count=institution_count,
                    dept_buy_count=len(top_buyers),
                    dept_sell_count=len(top_sellers)
                )

                records.append(record)

            logger.success(f"龙虎榜数据抓取成功: {len(records)}只股票上榜，共{sum(r.institution_count for r in records)}家机构参与")
            return records

        except Exception as e:
            logger.error(f"抓取龙虎榜数据失败: {e}")
            return []

    def _classify_lhb_reason(self, reason: str) -> str:
        """
        分类上榜原因

        Args:
            reason: 上榜原因

        Returns:
            原因类型
        """
        if '涨幅' in reason or '偏离' in reason:
            return '涨幅偏离'
        elif '换手' in reason:
            return '换手异常'
        elif '振幅' in reason:
            return '振幅异常'
        elif '跌幅' in reason:
            return '跌幅异常'
        else:
            return '其他'

    def save_dragon_tiger_list(self, records: List[DragonTigerRecord]) -> int:
        """
        保存龙虎榜数据到数据库

        Args:
            records: 龙虎榜记录列表

        Returns:
            保存的记录数
        """
        if not records:
            return 0

        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for record in records:
                cursor.execute("""
                    INSERT INTO dragon_tiger_list (
                        trade_date, stock_code, stock_name, reason, reason_type,
                        close_price, price_change, turnover_rate,
                        buy_amount, sell_amount, net_amount,
                        top_buyers, top_sellers,
                        has_institution, institution_count,
                        dept_buy_count, dept_sell_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (trade_date, stock_code)
                    DO UPDATE SET
                        stock_name = EXCLUDED.stock_name,
                        reason = EXCLUDED.reason,
                        reason_type = EXCLUDED.reason_type,
                        close_price = EXCLUDED.close_price,
                        price_change = EXCLUDED.price_change,
                        turnover_rate = EXCLUDED.turnover_rate,
                        buy_amount = EXCLUDED.buy_amount,
                        sell_amount = EXCLUDED.sell_amount,
                        net_amount = EXCLUDED.net_amount,
                        top_buyers = EXCLUDED.top_buyers,
                        top_sellers = EXCLUDED.top_sellers,
                        has_institution = EXCLUDED.has_institution,
                        institution_count = EXCLUDED.institution_count,
                        dept_buy_count = EXCLUDED.dept_buy_count,
                        dept_sell_count = EXCLUDED.dept_sell_count,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    record.trade_date, record.stock_code, record.stock_name,
                    record.reason, record.reason_type,
                    record.close_price, record.price_change, record.turnover_rate,
                    record.buy_amount, record.sell_amount, record.net_amount,
                    json.dumps(record.top_buyers, ensure_ascii=False),
                    json.dumps(record.top_sellers, ensure_ascii=False),
                    record.has_institution, record.institution_count,
                    record.dept_buy_count, record.dept_sell_count
                ))

                saved_count += cursor.rowcount

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"龙虎榜数据已保存: {saved_count}条记录")
            return saved_count

        except Exception as e:
            logger.error(f"保存龙虎榜数据失败: {e}")
            return 0

    # ========== 5. 完整同步流程 ==========

    def sync_daily_sentiment(self, date_str: Optional[str] = None) -> SentimentSyncResult:
        """
        完整的每日情绪数据同步流程

        Args:
            date_str: 日期字符串，None表示今天

        Returns:
            同步结果
        """
        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"========== 开始同步{date_str}的市场情绪数据 ==========")

        result = SentimentSyncResult(
            success=False,
            is_trading_day=False
        )

        try:
            # 1. 校验交易日
            is_trading = self.is_trading_day(date_str)
            result.is_trading_day = is_trading

            if not is_trading:
                logger.info(f"{date_str}非交易日，跳过数据采集")
                result.success = True
                result.details['skip_reason'] = '非交易日'
                return result

            # 2. 抓取大盘数据
            logger.info("步骤1/3: 抓取大盘数据...")
            market_data = self.fetch_market_indices(date_str)
            if self.save_market_indices(market_data):
                result.synced_tables.append('market_sentiment_daily')

            import time
            time.sleep(self.rate_limit_delay)

            # 3. 抓取涨停板池
            logger.info("步骤2/3: 抓取涨停板池...")
            limit_up_data = self.fetch_limit_up_pool(date_str)
            if self.save_limit_up_pool(limit_up_data):
                result.synced_tables.append('limit_up_pool')

            time.sleep(self.rate_limit_delay)

            # 4. 抓取龙虎榜
            logger.info("步骤3/3: 抓取龙虎榜...")
            dragon_tiger_records = self.fetch_dragon_tiger_list(date_str)
            saved_count = self.save_dragon_tiger_list(dragon_tiger_records)
            if saved_count > 0:
                result.synced_tables.append('dragon_tiger_list')

            result.success = True
            result.details = {
                'market_indices': {
                    'sh_close': market_data.sh_index_close,
                    'sh_change': market_data.sh_index_change
                },
                'limit_up': {
                    'count': limit_up_data.limit_up_count,
                    'blast_rate': limit_up_data.blast_rate
                },
                'dragon_tiger': {
                    'count': saved_count
                }
            }

            logger.success(f"========== {date_str}市场情绪数据同步完成 ==========")

        except Exception as e:
            logger.error(f"同步市场情绪数据失败: {e}")
            result.success = False
            result.error = str(e)

        return result
