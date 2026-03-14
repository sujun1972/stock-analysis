#!/usr/bin/env python3
"""
概念板块数据采集器

功能说明：
- 从配置的数据源获取概念板块数据（支持AkShare和Tushare）
- 保存概念板块列表到数据库
- 保存股票-概念多对多关系
- 支持按股票代码查询所属概念
- 支持获取所有概念列表

数据源说明：
- AkShare（推荐）：使用东方财富，466个概念，完整成分股数据，免费
- Tushare（需5000积分）：使用concept接口，概念数据完整

作者: Stock Analysis System
版本: 2.0.0（支持配置化数据源）
"""

import pandas as pd
from typing import Optional
from loguru import logger

try:
    from .utils.response import Response
    from .exceptions import DataProviderError
    from .database.connection_pool_manager import ConnectionPoolManager
    from .config.data_source_helper import create_provider, get_data_source_config
    from .providers.provider_factory import DataProviderFactory
except ImportError:
    from src.utils.response import Response
    from src.exceptions import DataProviderError
    from src.database.connection_pool_manager import ConnectionPoolManager
    from src.config.data_source_helper import create_provider, get_data_source_config
    from src.providers.provider_factory import DataProviderFactory


class ConceptFetcher:
    """概念板块数据采集器（支持配置化数据源）"""

    def __init__(self, pool_manager: ConnectionPoolManager):
        """
        初始化概念采集器

        Args:
            pool_manager: 数据库连接池管理器
        """
        self.pool_manager = pool_manager

        # 从配置获取数据源（使用独立的概念数据源配置）
        self.config = get_data_source_config()
        self.data_source = self.config.get("concept_data_source", self.config["data_source"])

        # 创建数据提供者（使用概念数据源类型）
        try:
            self.provider = create_provider("concept")
            logger.info(f"✓ 概念采集器初始化成功，使用概念数据源: {self.data_source}")
        except Exception as e:
            logger.warning(f"创建数据提供者失败，将在需要时重试: {e}")
            self.provider = None

    @staticmethod
    def _normalize_stock_code(stock_code: str) -> str:
        """
        标准化股票代码，添加交易所后缀

        规则：
        - 6开头：上海证券交易所（.SH）
        - 其他：深圳证券交易所（.SZ）
        - 已有后缀：保持不变

        Args:
            stock_code: 股票代码（如 '000001' 或 '000001.SZ'）

        Returns:
            标准化后的股票代码（如 '000001.SZ' 或 '600000.SH'）
        """
        if '.' not in stock_code:
            return f"{stock_code}.SH" if stock_code.startswith('6') else f"{stock_code}.SZ"
        return stock_code

    def fetch_and_save_concepts(self, source: Optional[str] = None) -> Response:
        """
        获取并保存概念板块数据

        Args:
            source: 数据源（可选）
                   - None: 使用配置的数据源
                   - 'em': 强制使用AkShare东方财富
                   - 'ths': 强制使用AkShare同花顺（不推荐，成分股API已失效）
                   - 'tushare': 强制使用Tushare（需5000积分）

        Returns:
            Response: 包含操作结果的响应对象
        """
        try:
            # 如果未指定source，使用配置的数据源
            if source is None:
                actual_source = self.data_source
            else:
                actual_source = source

            logger.info(f"开始获取概念板块数据（数据源：{actual_source}）...")

            # 初始化 tushare_provider（如果需要）
            tushare_provider = None

            # 1. 根据数据源获取概念列表
            if actual_source == "tushare":
                # 使用Tushare获取概念列表（动态创建 tushare provider）
                tushare_token = self.config.get("tushare_token", "")
                tushare_provider = DataProviderFactory.create_provider('tushare', token=tushare_token)
                concept_df = tushare_provider.api_client.query('concept')
                # 字段映射：ts_code -> 代码, name -> 名称
                concept_df = concept_df.rename(columns={'ts_code': '代码', 'name': '名称'})
                source_label = 'tushare'

            elif actual_source == "akshare" or source == 'em':
                # 使用AkShare东方财富数据源（推荐）
                import akshare as ak
                concept_df = ak.stock_board_concept_name_em()
                concept_df = concept_df.rename(columns={'板块名称': '名称', '板块代码': '代码'})
                source_label = 'em'

            elif source == 'ths':
                # 使用AkShare同花顺数据源（不推荐）
                import akshare as ak
                logger.warning("⚠️ 同花顺成分股API已失效，建议使用东方财富数据源(source='em')")
                concept_df = ak.stock_board_concept_name_ths()
                source_label = 'ths'

            else:
                return Response.error(
                    error=f"不支持的数据源: {actual_source}",
                    error_code="INVALID_DATA_SOURCE"
                )

            logger.info(f"获取到 {len(concept_df)} 个概念板块")

            # 2. 保存概念列表到数据库
            saved_concepts = self._save_concepts_to_db(concept_df, source_label)

            # 3. 获取并保存每个概念的成分股
            total_relationships = 0

            if source == 'ths':
                logger.warning("⚠️ 同花顺成分股API不可用，跳过成分股同步")
            elif actual_source == "tushare":
                # 使用Tushare获取概念成分股（使用之前创建的 tushare_provider）
                for idx, row in concept_df.iterrows():
                    try:
                        concept_code = row.get('代码') or row.get('code')
                        concept_name = row.get('名称') or row.get('name')

                        if not concept_code or not concept_name:
                            logger.warning(f"跳过无效概念（缺少代码或名称）: {row}")
                            continue

                        logger.info(f"正在获取概念 [{concept_name}] 的成分股... ({idx+1}/{len(concept_df)})")

                        # 获取概念成分股
                        stocks_df = tushare_provider.api_client.query('concept_detail', ts_code=concept_code)

                        if stocks_df is not None and not stocks_df.empty:
                            # 字段映射：ts_code -> 代码
                            stocks_df = stocks_df.rename(columns={'ts_code': '代码'})
                            count = self._save_stock_concept_relationships(
                                stocks_df, concept_code, concept_name
                            )
                            total_relationships += count
                            logger.info(f"  └─ 保存 {count} 条股票关系")

                    except Exception as e:
                        logger.error(f"获取概念 [{concept_name}] 的成分股失败: {e}")
                        continue

            else:
                # 使用AkShare东方财富获取概念成分股
                import akshare as ak
                for idx, row in concept_df.iterrows():
                    try:
                        concept_code = row.get('代码') or row.get('code')
                        concept_name = row.get('名称') or row.get('name')

                        if not concept_code or not concept_name:
                            logger.warning(f"跳过无效概念（缺少代码或名称）: {row}")
                            continue

                        logger.info(f"正在获取概念 [{concept_name}] 的成分股... ({idx+1}/{len(concept_df)})")

                        # 获取概念成分股（东方财富）
                        stocks_df = ak.stock_board_concept_cons_em(symbol=concept_name)

                        if stocks_df is not None and not stocks_df.empty:
                            count = self._save_stock_concept_relationships(
                                stocks_df, concept_code, concept_name
                            )
                            total_relationships += count
                            logger.info(f"  └─ 保存 {count} 条股票关系")

                    except Exception as e:
                        logger.error(f"获取概念 [{concept_name}] 的成分股失败: {e}")
                        continue

            logger.success(f"✅ 概念数据同步完成：{saved_concepts} 个概念，{total_relationships} 条股票关系")

            return Response.success(
                data={
                    'concepts_count': saved_concepts,
                    'relationships_count': total_relationships
                },
                message=f"成功同步 {saved_concepts} 个概念和 {total_relationships} 条股票关系"
            )

        except Exception as e:
            logger.error(f"获取概念数据失败: {e}")
            return Response.error(
                error=f"获取概念数据失败: {str(e)}",
                error_code="FETCH_CONCEPTS_FAILED",
                error_detail=str(e)
            )

    def _save_concepts_to_db(self, concept_df: pd.DataFrame, source: str) -> int:
        """
        保存概念列表到数据库

        Args:
            concept_df: 概念数据DataFrame
            source: 数据源标识

        Returns:
            int: 保存的概念数量
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for _, row in concept_df.iterrows():
                concept_code = row.get('代码') or row.get('code')
                concept_name = row.get('名称') or row.get('name')

                if not concept_code or not concept_name:
                    continue

                # 使用 UPSERT 语法（INSERT ... ON CONFLICT）
                cursor.execute("""
                    INSERT INTO concept (code, name, source, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (code)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        source = EXCLUDED.source,
                        updated_at = CURRENT_TIMESTAMP
                """, (concept_code, concept_name, source))

                saved_count += 1

            conn.commit()
            return saved_count

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"保存概念到数据库失败: {e}")
            raise

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)

    def _save_stock_concept_relationships(
        self,
        stocks_df: pd.DataFrame,
        concept_code: str,
        concept_name: str
    ) -> int:
        """
        保存股票-概念关系到数据库

        Args:
            stocks_df: 股票数据DataFrame
            concept_code: 概念代码
            concept_name: 概念名称

        Returns:
            int: 保存的关系数量
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            # 先获取concept_id
            cursor.execute("SELECT id FROM concept WHERE code = %s", (concept_code,))
            result = cursor.fetchone()
            if not result:
                logger.warning(f"未找到概念: {concept_code}")
                return 0

            concept_id = result[0]
            saved_count = 0

            for _, row in stocks_df.iterrows():
                stock_code = row.get('代码') or row.get('code')

                if not stock_code:
                    continue

                # 标准化股票代码（自动添加交易所后缀）
                stock_code = self._normalize_stock_code(stock_code)

                try:
                    cursor.execute("""
                        INSERT INTO stock_concept
                            (stock_code, concept_id, concept_code, concept_name, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (stock_code, concept_id)
                        DO UPDATE SET
                            concept_code = EXCLUDED.concept_code,
                            concept_name = EXCLUDED.concept_name,
                            updated_at = CURRENT_TIMESTAMP
                    """, (stock_code, concept_id, concept_code, concept_name))

                    saved_count += 1

                except Exception as e:
                    logger.warning(f"保存股票 {stock_code} 的概念关系失败: {e}")
                    continue

            # 更新概念表的股票数量
            cursor.execute("""
                UPDATE concept
                SET stock_count = (
                    SELECT COUNT(*) FROM stock_concept WHERE concept_id = %s
                )
                WHERE id = %s
            """, (concept_id, concept_id))

            conn.commit()
            return saved_count

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"保存股票-概念关系失败: {e}")
            raise

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)

    def get_stock_concepts(self, stock_code: str) -> Response:
        """
        获取某只股票所属的所有概念

        Args:
            stock_code: 股票代码（支持 '000001' 或 '000001.SZ' 格式）

        Returns:
            Response: 包含概念列表的响应对象
        """
        conn = None
        try:
            # 标准化股票代码（自动添加交易所后缀）
            stock_code = self._normalize_stock_code(stock_code)

            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    c.id, c.code, c.name, c.source, c.stock_count
                FROM concept c
                INNER JOIN stock_concept sc ON c.id = sc.concept_id
                WHERE sc.stock_code = %s
                ORDER BY c.name
            """, (stock_code,))

            concepts = []
            for row in cursor.fetchall():
                concepts.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2],
                    'source': row[3],
                    'stock_count': row[4]
                })

            return Response.success(
                data=concepts,
                message=f"获取到 {len(concepts)} 个概念"
            )

        except Exception as e:
            logger.error(f"获取股票概念失败: {e}")
            return Response.error(
                error=f"获取股票概念失败: {str(e)}",
                error_code="GET_STOCK_CONCEPTS_FAILED"
            )

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)

    def get_all_concepts(self, limit: Optional[int] = None) -> Response:
        """
        获取所有概念列表

        Args:
            limit: 限制返回数量

        Returns:
            Response: 包含概念列表的响应对象
        """
        conn = None
        try:
            conn = self.pool_manager.get_connection()
            cursor = conn.cursor()

            query = """
                SELECT id, code, name, source, stock_count, created_at, updated_at
                FROM concept
                ORDER BY stock_count DESC, name
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)

            concepts = []
            for row in cursor.fetchall():
                concepts.append({
                    'id': row[0],
                    'code': row[1],
                    'name': row[2],
                    'source': row[3],
                    'stock_count': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                    'updated_at': row[6].isoformat() if row[6] else None
                })

            return Response.success(
                data=concepts,
                message=f"获取到 {len(concepts)} 个概念"
            )

        except Exception as e:
            logger.error(f"获取概念列表失败: {e}")
            return Response.error(
                error=f"获取概念列表失败: {str(e)}",
                error_code="GET_CONCEPTS_FAILED"
            )

        finally:
            if conn:
                cursor.close()
                self.pool_manager.release_connection(conn)


# 使用示例
if __name__ == "__main__":
    from src.config.settings import get_settings

    settings = get_settings()
    db_settings = settings.database

    # 创建连接池
    pool_manager = ConnectionPoolManager(
        config={
            'host': db_settings.host,
            'port': db_settings.port,
            'database': db_settings.database,
            'user': db_settings.user,
            'password': db_settings.password
        },
        min_conn=2,
        max_conn=10
    )

    try:
        fetcher = ConceptFetcher(pool_manager)

        # 获取并保存概念数据（使用东方财富数据源，推荐）
        result = fetcher.fetch_and_save_concepts(source='em')

        if result.is_success():
            logger.success(f"✅ {result.message}")
            logger.info(f"数据: {result.data}")
        else:
            logger.error(f"❌ {result.error}")

    finally:
        pool_manager.close_all()
