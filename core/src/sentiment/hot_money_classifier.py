"""
游资席位分类器

负责识别和分类龙虎榜席位，将席位打上标签（一线顶级游资、知名游资、散户大本营、机构等）。
"""

from typing import Dict, List, Optional, Tuple
from loguru import logger

from ..database.connection_pool_manager import ConnectionPoolManager
from .models import HotMoneySeat
from .config import HotMoneyDict, get_seat_type_label


class HotMoneyClassifier:
    """游资席位分类器"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化

        Args:
            pool_manager: 数据库连接池管理器
        """
        self.pool_manager = pool_manager
        self.hot_money_dict = HotMoneyDict()

        # 缓存席位字典（用于快速查询）
        self._seat_cache: Dict[str, HotMoneySeat] = {}
        self._load_seat_dict()

    def _load_seat_dict(self):
        """从数据库加载游资席位字典到缓存"""
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    seat_name, seat_type, seat_label, match_keywords,
                    city, broker, branch_office, trade_style, priority
                FROM hot_money_seats
                WHERE is_active = true
                ORDER BY priority DESC
            """)

            rows = cursor.fetchall()
            for row in rows:
                seat = HotMoneySeat(
                    seat_name=row[0],
                    seat_type=row[1],
                    seat_label=row[2],
                    match_keywords=row[3] or [],
                    city=row[4],
                    broker=row[5],
                    branch_office=row[6],
                    trade_style=row[7],
                    priority=row[8]
                )
                self._seat_cache[row[0]] = seat

            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.info(f"已加载 {len(self._seat_cache)} 个游资席位到缓存")

        except Exception as e:
            logger.error(f"加载游资席位字典失败: {e}")

    def classify_seat(self, seat_name: str) -> Tuple[str, str]:
        """
        对席位进行分类

        Args:
            seat_name: 席位完整名称

        Returns:
            (seat_type, seat_label) 元组
            例如: ('top_tier', '[一线顶级游资]')
        """
        # 1. 优先从缓存中精确匹配
        if seat_name in self._seat_cache:
            seat = self._seat_cache[seat_name]
            return seat.seat_type, seat.seat_label

        # 2. 关键词模糊匹配
        seat_type, seat_label = self._fuzzy_match(seat_name)

        return seat_type, seat_label

    def _fuzzy_match(self, seat_name: str) -> Tuple[str, str]:
        """
        关键词模糊匹配

        Args:
            seat_name: 席位名称

        Returns:
            (seat_type, seat_label)
        """
        # 优先级从高到低匹配

        # 1. 机构席位（最高优先级）
        for keyword in self.hot_money_dict.INSTITUTION_KEYWORDS:
            if keyword in seat_name:
                return 'institution', '[机构]'

        # 2. 一线顶级游资
        for keyword in self.hot_money_dict.TOP_TIER_KEYWORDS:
            if keyword in seat_name:
                return 'top_tier', '[一线顶级游资]'

        # 3. 散户大本营
        for keyword in self.hot_money_dict.RETAIL_BASE_KEYWORDS:
            if keyword in seat_name:
                return 'retail_base', '[散户大本营]'

        # 4. 知名游资（通过券商名称判断）
        for broker in self.hot_money_dict.FAMOUS_BROKERS:
            if broker in seat_name:
                return 'famous', '[知名游资]'

        # 5. 未识别
        return 'unknown', '[未知席位]'

    def classify_dragon_tiger_seats(self, trade_date: str) -> Dict:
        """
        对指定日期的所有龙虎榜席位进行分类统计

        Args:
            trade_date: 交易日期 (YYYY-MM-DD)

        Returns:
            分类统计结果
            {
                'top_tier': [席位列表],
                'institution': [席位列表],
                'retail_base': [席位列表],
                'famous': [席位列表],
                'unknown': [席位列表],
                'statistics': {统计数据}
            }
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询当日所有龙虎榜席位
            cursor.execute("""
                SELECT
                    stock_code, stock_name, close_price, price_change,
                    top_buyers, top_sellers, net_amount
                FROM dragon_tiger_list
                WHERE trade_date = %s
            """, (trade_date,))

            rows = cursor.fetchall()
            cursor.close()
            self.pool_manager.release_connection(conn)

            # 分类结果
            classified_seats = {
                'top_tier': [],
                'institution': [],
                'retail_base': [],
                'famous': [],
                'unknown': []
            }

            # 统计数据
            statistics = {
                'total_records': len(rows),
                'top_tier_count': 0,
                'institution_count': 0,
                'retail_base_count': 0,
                'famous_count': 0,
                'unknown_count': 0,
                'top_tier_buy_amount': 0.0,
                'institution_buy_amount': 0.0
            }

            for row in rows:
                stock_code, stock_name, close_price, price_change = row[0], row[1], row[2], row[3]
                top_buyers = row[4] or []
                top_sellers = row[5] or []
                net_amount = row[6] or 0.0

                # 处理买入席位
                for buyer in top_buyers:
                    seat_name = buyer.get('name', '')
                    buy_amount = buyer.get('buy_amount', 0) or buyer.get('amount', 0)

                    seat_type, seat_label = self.classify_seat(seat_name)

                    seat_info = {
                        'seat_name': seat_name,
                        'seat_label': seat_label,
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'buy_amount': buy_amount,
                        'price_change': price_change,
                        'rank': buyer.get('rank', 0)
                    }

                    classified_seats[seat_type].append(seat_info)
                    statistics[f'{seat_type}_count'] += 1

                    # 统计买入金额
                    if seat_type in ['top_tier', 'institution']:
                        statistics[f'{seat_type}_buy_amount'] += buy_amount

            return {
                'trade_date': trade_date,
                'classified_seats': classified_seats,
                'statistics': statistics
            }

        except Exception as e:
            logger.error(f"分类龙虎榜席位失败: {e}")
            raise

    def get_institution_top_stocks(self, trade_date: str, limit: int = 3) -> List[Dict]:
        """
        获取机构净买入前N的个股

        Args:
            trade_date: 交易日期
            limit: 返回数量

        Returns:
            机构净买入排行榜
            [
                {
                    'stock_code': '000001',
                    'stock_name': '平安银行',
                    'net_buy_amount': 50000000,
                    'institution_seats': [席位列表],
                    'institution_count': 3
                }
            ]
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询有机构参与的龙虎榜记录
            cursor.execute("""
                SELECT
                    stock_code, stock_name, close_price, price_change,
                    top_buyers, net_amount, reason
                FROM dragon_tiger_list
                WHERE trade_date = %s AND has_institution = true
                ORDER BY net_amount DESC
            """, (trade_date,))

            rows = cursor.fetchall()
            cursor.close()
            self.pool_manager.release_connection(conn)

            # 统计每只股票的机构净买入
            stock_institution_map = {}

            for row in rows:
                stock_code, stock_name = row[0], row[1]
                close_price, price_change = row[2], row[3]
                top_buyers = row[4] or []
                net_amount = row[5] or 0.0
                reason = row[6]

                institution_seats = []
                institution_buy_amount = 0.0

                # 过滤出机构席位
                for buyer in top_buyers:
                    seat_name = buyer.get('name', '')
                    buy_amount = buyer.get('buy_amount', 0) or buyer.get('amount', 0)

                    seat_type, seat_label = self.classify_seat(seat_name)

                    if seat_type == 'institution':
                        institution_seats.append({
                            'seat_name': seat_name,
                            'buy_amount': buy_amount,
                            'rank': buyer.get('rank', 0)
                        })
                        institution_buy_amount += buy_amount

                if institution_seats:
                    stock_institution_map[stock_code] = {
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'close_price': close_price,
                        'price_change': price_change,
                        'net_buy_amount': institution_buy_amount,
                        'institution_seats': institution_seats,
                        'institution_count': len(institution_seats),
                        'reason': reason
                    }

            # 按净买入额排序
            sorted_stocks = sorted(
                stock_institution_map.values(),
                key=lambda x: x['net_buy_amount'],
                reverse=True
            )

            return sorted_stocks[:limit]

        except Exception as e:
            logger.error(f"获取机构净买入排行榜失败: {e}")
            raise

    def get_hot_money_limit_up_stocks(
        self,
        trade_date: str,
        seat_type: str = 'top_tier',
        limit: int = 10
    ) -> List[Dict]:
        """
        获取顶级游资主导打板的个股

        Args:
            trade_date: 交易日期
            seat_type: 席位类型 (top_tier/famous)
            limit: 返回数量

        Returns:
            游资打板排行榜
            [
                {
                    'stock_code': '000001',
                    'stock_name': '平安银行',
                    'hot_money_seats': [席位列表],
                    'hot_money_count': 2,
                    'total_buy_amount': 30000000,
                    'is_limit_up': True
                }
            ]
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询龙虎榜 + 涨停板数据
            cursor.execute("""
                SELECT
                    dt.stock_code, dt.stock_name, dt.close_price, dt.price_change,
                    dt.top_buyers, dt.net_amount, dt.reason,
                    lup.limit_up_stocks
                FROM dragon_tiger_list dt
                LEFT JOIN limit_up_pool lup ON dt.trade_date = lup.trade_date
                WHERE dt.trade_date = %s
            """, (trade_date,))

            rows = cursor.fetchall()
            cursor.close()
            self.pool_manager.release_connection(conn)

            # 涨停股票代码集合
            limit_up_codes = set()
            if rows and rows[0][7]:
                limit_up_stocks = rows[0][7]
                limit_up_codes = {stock['code'] for stock in limit_up_stocks}

            # 统计游资操作
            stock_hot_money_map = {}

            for row in rows:
                stock_code, stock_name = row[0], row[1]
                close_price, price_change = row[2], row[3]
                top_buyers = row[4] or []
                net_amount = row[5] or 0.0
                reason = row[6]

                hot_money_seats = []
                hot_money_buy_amount = 0.0

                # 过滤出指定类型的游资席位
                for buyer in top_buyers:
                    seat_name = buyer.get('name', '')
                    buy_amount = buyer.get('buy_amount', 0) or buyer.get('amount', 0)

                    classified_type, seat_label = self.classify_seat(seat_name)

                    if classified_type == seat_type:
                        hot_money_seats.append({
                            'seat_name': seat_name,
                            'seat_label': seat_label,
                            'buy_amount': buy_amount,
                            'rank': buyer.get('rank', 0)
                        })
                        hot_money_buy_amount += buy_amount

                if hot_money_seats:
                    stock_hot_money_map[stock_code] = {
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'close_price': close_price,
                        'price_change': price_change,
                        'hot_money_seats': hot_money_seats,
                        'hot_money_count': len(hot_money_seats),
                        'total_buy_amount': hot_money_buy_amount,
                        'is_limit_up': stock_code in limit_up_codes,
                        'reason': reason
                    }

            # 按买入金额排序
            sorted_stocks = sorted(
                stock_hot_money_map.values(),
                key=lambda x: x['total_buy_amount'],
                reverse=True
            )

            return sorted_stocks[:limit]

        except Exception as e:
            logger.error(f"获取游资打板排行榜失败: {e}")
            raise

    def update_seat_statistics(self, trade_date: str):
        """
        更新游资席位的统计信息（上榜次数、累计买卖金额等）

        Args:
            trade_date: 交易日期
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 查询当日龙虎榜席位
            cursor.execute("""
                SELECT top_buyers, top_sellers
                FROM dragon_tiger_list
                WHERE trade_date = %s
            """, (trade_date,))

            rows = cursor.fetchall()

            # 统计席位出现次数和金额
            seat_stats = {}

            for row in rows:
                top_buyers = row[0] or []
                top_sellers = row[1] or []

                for buyer in top_buyers:
                    seat_name = buyer.get('name', '')
                    buy_amount = buyer.get('buy_amount', 0) or buyer.get('amount', 0)

                    if seat_name not in seat_stats:
                        seat_stats[seat_name] = {
                            'appearance_count': 0,
                            'total_buy_amount': 0.0,
                            'total_sell_amount': 0.0
                        }

                    seat_stats[seat_name]['appearance_count'] += 1
                    seat_stats[seat_name]['total_buy_amount'] += buy_amount

                for seller in top_sellers:
                    seat_name = seller.get('name', '')
                    sell_amount = seller.get('sell_amount', 0) or seller.get('amount', 0)

                    if seat_name not in seat_stats:
                        seat_stats[seat_name] = {
                            'appearance_count': 0,
                            'total_buy_amount': 0.0,
                            'total_sell_amount': 0.0
                        }

                    seat_stats[seat_name]['total_sell_amount'] += sell_amount

            # 更新数据库
            for seat_name, stats in seat_stats.items():
                # 自动分类席位
                seat_type, seat_label = self.classify_seat(seat_name)

                cursor.execute("""
                    INSERT INTO hot_money_seats (
                        seat_name, seat_type, seat_label,
                        appearance_count, total_buy_amount, total_sell_amount,
                        last_appearance_date, data_source
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'auto')
                    ON CONFLICT (seat_name) DO UPDATE SET
                        appearance_count = hot_money_seats.appearance_count + %s,
                        total_buy_amount = hot_money_seats.total_buy_amount + %s,
                        total_sell_amount = hot_money_seats.total_sell_amount + %s,
                        last_appearance_date = %s,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    seat_name, seat_type, seat_label,
                    stats['appearance_count'], stats['total_buy_amount'], stats['total_sell_amount'],
                    trade_date,
                    stats['appearance_count'], stats['total_buy_amount'], stats['total_sell_amount'],
                    trade_date
                ))

            conn.commit()
            cursor.close()
            self.pool_manager.release_connection(conn)

            logger.info(f"{trade_date} 席位统计信息更新完成，涉及 {len(seat_stats)} 个席位")

            # 重新加载缓存
            self._load_seat_dict()

        except Exception as e:
            logger.error(f"更新席位统计信息失败: {e}")
            raise

    def get_seat_activity_ranking(self, days: int = 30, limit: int = 20) -> List[Dict]:
        """
        获取游资活跃度排行榜

        Args:
            days: 统计最近N天
            limit: 返回数量

        Returns:
            活跃度排行榜
        """
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    seat_name, seat_type, seat_label, city, broker,
                    appearance_count, total_buy_amount, total_sell_amount,
                    net_amount, win_rate, trade_style, last_appearance_date,
                    -- 计算活跃度得分
                    (
                        appearance_count * 0.4 +
                        COALESCE(win_rate, 0) * 0.3 +
                        (CASE
                            WHEN last_appearance_date >= CURRENT_DATE - INTERVAL '%s days' THEN 30
                            WHEN last_appearance_date >= CURRENT_DATE - INTERVAL '90 days' THEN 15
                            ELSE 0
                        END)
                    ) as activity_score
                FROM hot_money_seats
                WHERE is_active = true
                ORDER BY activity_score DESC, appearance_count DESC
                LIMIT %s
            """, (days, limit))

            rows = cursor.fetchall()
            cursor.close()
            self.pool_manager.release_connection(conn)

            ranking = []
            for idx, row in enumerate(rows, start=1):
                ranking.append({
                    'rank': idx,
                    'seat_name': row[0],
                    'seat_type': row[1],
                    'seat_label': row[2],
                    'city': row[3],
                    'broker': row[4],
                    'appearance_count': row[5],
                    'total_buy_amount': float(row[6]) if row[6] else 0.0,
                    'total_sell_amount': float(row[7]) if row[7] else 0.0,
                    'net_amount': float(row[8]) if row[8] else 0.0,
                    'win_rate': float(row[9]) if row[9] else None,
                    'trade_style': row[10],
                    'last_appearance_date': row[11].strftime('%Y-%m-%d') if row[11] else None,
                    'activity_score': float(row[12])
                })

            return ranking

        except Exception as e:
            logger.error(f"获取游资活跃度排行榜失败: {e}")
            raise
