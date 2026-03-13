"""
盘前外盘数据抓取器

负责抓取隔夜外盘核心数据:
- A50期指、中概股指数
- 大宗商品(原油、黄金、铜)
- 外汇(美元兑人民币)
- 美股三大指数
- 盘前核心新闻(财联社/金十快讯)

注意：盘前外盘数据主要使用AkShare数据源
      即使配置了Tushare，外盘数据也会自动降级使用AkShare

作者: AI Strategy Team
创建日期: 2026-03-11
"""

import pandas as pd
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger

from ..database.connection_pool_manager import ConnectionPoolManager
from ..config.data_source_helper import get_data_source_config
from .models import OvernightData, PremarketNews, PremarketSyncResult


class PremarketDataFetcher:
    """盘前外盘数据抓取器（支持配置化数据源）"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化

        Args:
            pool_manager: 数据库连接池管理器
        """
        self.pool_manager = pool_manager
        self.rate_limit_delay = 0.5  # 数据源限流延迟（秒）

        # 从配置获取数据源
        self.config = get_data_source_config()
        self.data_source = self.config["data_source"]

        # 盘前外盘数据主要使用AkShare
        if self.data_source == "tushare":
            logger.info("盘前外盘数据使用AkShare（Tushare不支持外盘数据）")

        logger.info(f"✓ 盘前数据抓取器初始化成功，数据源: AkShare (外盘数据)")

        # 强情绪关键词列表
        self.CRITICAL_KEYWORDS = [
            "超预期", "停牌", "立案调查", "战争", "发布会",
            "印发", "暴涨", "暴跌", "崩盘", "熔断",
            "降息", "加息", "降准", "加税", "减税",
            "禁令", "制裁", "突发", "紧急", "重大利好", "重大利空",
            "破产", "退市", "复牌", "涨停", "跌停"
        ]

    # ========== 1. 交易日判断 ==========

    def is_trading_day(self, date_str: str) -> bool:
        """
        判断是否为交易日（复用sentiment模块的逻辑）

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

    # ========== 2. 隔夜外盘数据抓取 ==========

    def fetch_overnight_data(self, trade_date: str) -> OvernightData:
        """
        抓取隔夜外盘数据

        Args:
            trade_date: A股交易日期 (YYYY-MM-DD)

        Returns:
            隔夜外盘数据
        """
        try:
            logger.info(f"开始抓取{trade_date}的隔夜外盘数据...")

            data = OvernightData(
                trade_date=trade_date,
                fetch_time=datetime.now()
            )

            # 1. A50期指(富时中国A50指数期货)
            try:
                # 注意：AkShare的API可能有变化，这里使用最新的接口
                df_a50 = ak.futures_main_sina(symbol="A50", market="vn")
                if not df_a50.empty:
                    latest = df_a50.iloc[-1]
                    data.a50_close = float(latest.get('现价', 0))
                    data.a50_change = float(latest.get('涨跌幅', 0))
                    logger.info(f"A50期指: {data.a50_close} ({data.a50_change}%)")
            except Exception as e:
                logger.warning(f"获取A50数据失败: {e}，尝试备用方法...")
                try:
                    # 备用方法：直接获取指数
                    df_a50_alt = ak.index_investing_global(country="中国", index_name="富时中国A50指数")
                    if not df_a50_alt.empty:
                        latest = df_a50_alt.iloc[0]
                        data.a50_close = float(latest.get('最新价', 0))
                        data.a50_change = float(latest.get('涨跌幅', 0))
                        logger.info(f"A50期指(备用): {data.a50_close} ({data.a50_change}%)")
                except Exception as e2:
                    logger.error(f"A50备用方法也失败: {e2}")

            time.sleep(self.rate_limit_delay)

            # 2. 中概股指数(纳斯达克金龙中国指数 HXC)
            try:
                df_hxc = ak.index_us_stock_sina(symbol=".HXC")
                if not df_hxc.empty:
                    latest = df_hxc.iloc[-1]
                    data.china_concept_close = float(latest.get('收盘', 0))
                    data.china_concept_change = float(latest.get('涨跌幅', 0))
                    logger.info(f"中概股指数: {data.china_concept_close} ({data.china_concept_change}%)")
            except Exception as e:
                logger.warning(f"获取中概股指数失败: {e}")

            time.sleep(self.rate_limit_delay)

            # 3. 大宗商品 - WTI原油
            try:
                df_oil = ak.futures_global_em(symbol="CL")  # WTI原油期货
                if not df_oil.empty:
                    latest = df_oil.iloc[-1]
                    data.wti_crude_close = float(latest.get('最新价', 0))
                    data.wti_crude_change = float(latest.get('涨跌幅', 0))
                    logger.info(f"WTI原油: {data.wti_crude_close} ({data.wti_crude_change}%)")
            except Exception as e:
                logger.warning(f"获取原油数据失败: {e}")

            time.sleep(self.rate_limit_delay)

            # 4. COMEX黄金
            try:
                df_gold = ak.futures_global_em(symbol="GC")  # COMEX黄金期货
                if not df_gold.empty:
                    latest = df_gold.iloc[-1]
                    data.comex_gold_close = float(latest.get('最新价', 0))
                    data.comex_gold_change = float(latest.get('涨跌幅', 0))
                    logger.info(f"COMEX黄金: {data.comex_gold_close} ({data.comex_gold_change}%)")
            except Exception as e:
                logger.warning(f"获取黄金数据失败: {e}")

            time.sleep(self.rate_limit_delay)

            # 5. 伦敦铜(LME Copper)
            try:
                df_copper = ak.futures_global_em(symbol="HG")  # COMEX铜期货
                if not df_copper.empty:
                    latest = df_copper.iloc[-1]
                    data.lme_copper_close = float(latest.get('最新价', 0))
                    data.lme_copper_change = float(latest.get('涨跌幅', 0))
                    logger.info(f"伦敦铜: {data.lme_copper_close} ({data.lme_copper_change}%)")
            except Exception as e:
                logger.warning(f"获取铜数据失败: {e}")

            time.sleep(self.rate_limit_delay)

            # 6. 美元兑离岸人民币(USDCNH)
            try:
                df_fx = ak.fx_spot_quote()
                usdcnh_row = df_fx[df_fx['货币对'] == 'USDCNH']
                if not usdcnh_row.empty:
                    data.usdcnh_close = float(usdcnh_row.iloc[0].get('买入价', 0))
                    # 计算涨跌幅（与昨日收盘对比）
                    yesterday_close = float(usdcnh_row.iloc[0].get('昨收', data.usdcnh_close))
                    if yesterday_close > 0:
                        data.usdcnh_change = ((data.usdcnh_close - yesterday_close) / yesterday_close) * 100
                    logger.info(f"USDCNH: {data.usdcnh_close} ({data.usdcnh_change:.2f}%)")
            except Exception as e:
                logger.warning(f"获取汇率数据失败: {e}")

            time.sleep(self.rate_limit_delay)

            # 7. 美股三大指数
            try:
                # 标普500
                df_sp500 = ak.index_us_stock_sina(symbol=".INX")
                if not df_sp500.empty:
                    latest = df_sp500.iloc[-1]
                    data.sp500_close = float(latest.get('收盘', 0))
                    data.sp500_change = float(latest.get('涨跌幅', 0))

                time.sleep(self.rate_limit_delay)

                # 纳斯达克
                df_nasdaq = ak.index_us_stock_sina(symbol=".IXIC")
                if not df_nasdaq.empty:
                    latest = df_nasdaq.iloc[-1]
                    data.nasdaq_close = float(latest.get('收盘', 0))
                    data.nasdaq_change = float(latest.get('涨跌幅', 0))

                time.sleep(self.rate_limit_delay)

                # 道琼斯
                df_dow = ak.index_us_stock_sina(symbol=".DJI")
                if not df_dow.empty:
                    latest = df_dow.iloc[-1]
                    data.dow_close = float(latest.get('收盘', 0))
                    data.dow_change = float(latest.get('涨跌幅', 0))

                logger.info(f"美股: 标普{data.sp500_change}%, 纳指{data.nasdaq_change}%, 道指{data.dow_change}%")
            except Exception as e:
                logger.warning(f"获取美股数据失败: {e}")

            logger.success(f"隔夜外盘数据抓取完成")
            return data

        except Exception as e:
            logger.error(f"抓取隔夜数据失败: {e}")
            # 返回空数据对象，避免流程中断
            return OvernightData(trade_date=trade_date, fetch_time=datetime.now())

    def save_overnight_data(self, data: OvernightData) -> bool:
        """
        保存隔夜数据到数据库

        Args:
            data: 隔夜外盘数据

        Returns:
            是否成功
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO overnight_market_data (
                    trade_date, a50_close, a50_change, a50_amplitude,
                    china_concept_close, china_concept_change,
                    wti_crude_close, wti_crude_change,
                    comex_gold_close, comex_gold_change,
                    lme_copper_close, lme_copper_change,
                    usdcnh_close, usdcnh_change,
                    sp500_close, sp500_change,
                    nasdaq_close, nasdaq_change,
                    dow_close, dow_change,
                    fetch_time
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (trade_date) DO UPDATE SET
                    a50_close = EXCLUDED.a50_close,
                    a50_change = EXCLUDED.a50_change,
                    a50_amplitude = EXCLUDED.a50_amplitude,
                    china_concept_close = EXCLUDED.china_concept_close,
                    china_concept_change = EXCLUDED.china_concept_change,
                    wti_crude_close = EXCLUDED.wti_crude_close,
                    wti_crude_change = EXCLUDED.wti_crude_change,
                    comex_gold_close = EXCLUDED.comex_gold_close,
                    comex_gold_change = EXCLUDED.comex_gold_change,
                    lme_copper_close = EXCLUDED.lme_copper_close,
                    lme_copper_change = EXCLUDED.lme_copper_change,
                    usdcnh_close = EXCLUDED.usdcnh_close,
                    usdcnh_change = EXCLUDED.usdcnh_change,
                    sp500_close = EXCLUDED.sp500_close,
                    sp500_change = EXCLUDED.sp500_change,
                    nasdaq_close = EXCLUDED.nasdaq_close,
                    nasdaq_change = EXCLUDED.nasdaq_change,
                    dow_close = EXCLUDED.dow_close,
                    dow_change = EXCLUDED.dow_change,
                    fetch_time = EXCLUDED.fetch_time
            """, (
                data.trade_date,
                data.a50_close, data.a50_change, data.a50_amplitude,
                data.china_concept_close, data.china_concept_change,
                data.wti_crude_close, data.wti_crude_change,
                data.comex_gold_close, data.comex_gold_change,
                data.lme_copper_close, data.lme_copper_change,
                data.usdcnh_close, data.usdcnh_change,
                data.sp500_close, data.sp500_change,
                data.nasdaq_close, data.nasdaq_change,
                data.dow_close, data.dow_change,
                data.fetch_time
            ))

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"隔夜数据已保存: {data.trade_date}")
            return True

        except Exception as e:
            logger.error(f"保存隔夜数据失败: {e}")
            return False

    # ========== 3. 盘前新闻抓取 ==========

    def fetch_premarket_news(self, start_time: str, end_time: str, trade_date: str) -> List[PremarketNews]:
        """
        抓取盘前核心新闻(财联社/金十快讯)

        Args:
            start_time: 开始时间 (YYYY-MM-DD HH:MM:SS)
            end_time: 结束时间 (YYYY-MM-DD HH:MM:SS)
            trade_date: 对应的交易日

        Returns:
            新闻列表
        """
        try:
            logger.info(f"抓取盘前新闻: {start_time} ~ {end_time}")

            news_list = []

            # 方法1: 抓取金十数据快讯
            try:
                df = ak.js_news()  # 金十数据-快讯
                if not df.empty and '时间' in df.columns and '内容' in df.columns:
                    # 转换时间格式
                    df['时间'] = pd.to_datetime(df['时间'])

                    # 过滤时间范围
                    start_dt = pd.to_datetime(start_time)
                    end_dt = pd.to_datetime(end_time)
                    mask = (df['时间'] >= start_dt) & (df['时间'] <= end_dt)
                    df_filtered = df[mask]

                    # 关键词过滤
                    for _, row in df_filtered.iterrows():
                        content = str(row.get('内容', ''))
                        title = content[:50] if len(content) > 50 else content  # 取前50字作为标题

                        matched_keywords = [kw for kw in self.CRITICAL_KEYWORDS if kw in content]

                        if matched_keywords:
                            news_list.append(PremarketNews(
                                news_time=row['时间'].strftime('%Y-%m-%d %H:%M:%S'),
                                source='jin10',
                                title=title,
                                content=content,
                                keywords=matched_keywords,
                                importance_level=self._classify_importance(matched_keywords)
                            ))

                    logger.info(f"金十数据抓取到 {len(df_filtered)} 条快讯，过滤后 {len([n for n in news_list if n.source == 'jin10'])} 条")
            except Exception as e:
                logger.warning(f"抓取金十数据快讯失败: {e}")

            # 方法2: 抓取财联社快讯（如果AkShare支持）
            try:
                # 注意：这个API可能需要根据AkShare的实际接口调整
                df_cls = ak.stock_news_em()  # 东方财富网-股吧-新闻
                if not df_cls.empty:
                    # 这里需要根据实际返回的数据格式调整
                    pass
            except Exception as e:
                logger.debug(f"财联社接口不可用: {e}")

            logger.success(f"盘前新闻抓取完成: {len(news_list)}条")
            return news_list

        except Exception as e:
            logger.error(f"抓取盘前新闻失败: {e}")
            return []

    def _classify_importance(self, keywords: List[str]) -> str:
        """
        根据关键词分类新闻重要性

        Args:
            keywords: 匹配的关键词列表

        Returns:
            重要性级别: 'critical', 'high', 'medium'
        """
        critical_set = {"战争", "熔断", "崩盘", "禁令", "制裁", "破产", "退市"}
        high_set = {"超预期", "停牌", "立案调查", "重大利好", "重大利空", "突发", "紧急"}

        if any(kw in critical_set for kw in keywords):
            return "critical"
        elif any(kw in high_set for kw in keywords):
            return "high"
        else:
            return "medium"

    def save_premarket_news(self, news_list: List[PremarketNews], trade_date: str) -> int:
        """
        保存盘前新闻到数据库

        Args:
            news_list: 新闻列表
            trade_date: 交易日期

        Returns:
            保存的记录数
        """
        if not news_list:
            return 0

        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            saved_count = 0

            for news in news_list:
                cursor.execute("""
                    INSERT INTO premarket_news_flash (
                        trade_date, news_time, source, title, content,
                        keywords, importance_level
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (
                    trade_date,
                    news.news_time,
                    news.source,
                    news.title,
                    news.content,
                    json.dumps(news.keywords, ensure_ascii=False),
                    news.importance_level
                ))
                saved_count += cursor.rowcount

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.success(f"盘前新闻已保存: {saved_count}条")
            return saved_count

        except Exception as e:
            logger.error(f"保存盘前新闻失败: {e}")
            return 0

    # ========== 4. 完整同步流程 ==========

    def sync_premarket_data(self, trade_date: Optional[str] = None) -> PremarketSyncResult:
        """
        完整的盘前数据同步流程

        Args:
            trade_date: 交易日期，None表示今天

        Returns:
            同步结果
        """
        if not trade_date:
            trade_date = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"========== 开始同步{trade_date}的盘前数据 ==========")

        result = PremarketSyncResult(
            success=False,
            trade_date=trade_date,
            is_trading_day=False
        )

        try:
            # 1. 校验交易日
            is_trading = self.is_trading_day(trade_date)
            result.is_trading_day = is_trading

            if not is_trading:
                logger.info(f"{trade_date}非交易日，跳过数据采集")
                result.success = True
                result.details['skip_reason'] = '非交易日'
                return result

            # 2. 抓取隔夜外盘数据
            logger.info("步骤1/2: 抓取隔夜外盘数据...")
            overnight_data = self.fetch_overnight_data(trade_date)
            if self.save_overnight_data(overnight_data):
                result.synced_tables.append('overnight_market_data')

            time.sleep(self.rate_limit_delay)

            # 3. 抓取盘前新闻（从昨晚22:00到今早8:00）
            logger.info("步骤2/2: 抓取盘前核心新闻...")
            yesterday = (datetime.strptime(trade_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            start_time = f"{yesterday} 22:00:00"
            end_time = f"{trade_date} 08:00:00"

            news_list = self.fetch_premarket_news(start_time, end_time, trade_date)
            saved_count = self.save_premarket_news(news_list, trade_date)
            if saved_count > 0:
                result.synced_tables.append('premarket_news_flash')

            result.success = True
            result.details = {
                'overnight_data': {
                    'a50_change': overnight_data.a50_change,
                    'china_concept_change': overnight_data.china_concept_change,
                    'wti_crude_change': overnight_data.wti_crude_change
                },
                'news': {
                    'count': saved_count,
                    'critical_count': len([n for n in news_list if n.importance_level == 'critical'])
                }
            }

            logger.success(f"========== {trade_date}盘前数据同步完成 ==========")

        except Exception as e:
            logger.error(f"同步盘前数据失败: {e}")
            result.success = False
            result.error = str(e)

        return result
