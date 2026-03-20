"""
数据验证服务

职责：
- 数据完整性验证
- 数据质量检查
- 数据修复建议
"""

import asyncio
from typing import Dict, List, Optional

from loguru import logger

from app.repositories.stock_data_repository import StockDataRepository
from app.services.stock.stock_list_service import StockListService


class DataValidationService:
    """
    数据验证服务

    职责：
    - 验证股票数据完整性
    - 生成数据质量报告
    - 识别缺失和异常数据
    - 提供修复建议

    重构说明：
    - 从 DataDownloadService 提取验证相关功能
    - 使用 Repository 访问数据
    - 专注于数据质量分析
    """

    def __init__(
        self,
        stock_repo: Optional[StockDataRepository] = None,
        stock_list_service: Optional[StockListService] = None
    ):
        """
        初始化数据验证服务

        Args:
            stock_repo: 股票数据 Repository（可选，用于依赖注入）
            stock_list_service: 股票列表服务（可选，用于依赖注入）
        """
        self.stock_repo = stock_repo or StockDataRepository()
        self.stock_list_service = stock_list_service or StockListService()
        logger.debug("✓ DataValidationService initialized")

    # ==================== 单只股票验证 ====================

    async def validate_stock_data(self, code: str) -> Dict:
        """
        验证单只股票数据完整性

        Args:
            code: 股票代码

        Returns:
            验证结果字典 {
                is_valid: bool,
                record_count: int,
                date_range: (start, end) or None,
                missing_dates: int,
                issues: List[str]
            }

        Examples:
            >>> service = DataValidationService()
            >>> result = await service.validate_stock_data('000001')
            >>> if not result['is_valid']:
            ...     print(f"数据问题: {', '.join(result['issues'])}")
        """
        return await asyncio.to_thread(self.stock_repo.validate_stock_data, code)

    # ==================== 批量验证 ====================

    async def validate_batch(
        self,
        codes: Optional[List[str]] = None,
        max_concurrent: int = 10
    ) -> List[Dict]:
        """
        批量验证股票数据

        Args:
            codes: 股票代码列表（None 表示验证所有股票）
            max_concurrent: 最大并发数（默认10）

        Returns:
            验证结果列表

        Examples:
            >>> service = DataValidationService()
            >>> results = await service.validate_batch(['000001', '600000'])
            >>> invalid_count = sum(1 for r in results if not r['is_valid'])
        """
        # 获取股票列表
        if codes is None:
            codes = await self.stock_list_service.get_codes_list()

        logger.info(f"开始批量验证: {len(codes)} 只股票")

        # 信号量控制并发
        semaphore = asyncio.Semaphore(max_concurrent)

        async def validate_with_semaphore(code: str) -> Dict:
            """带信号量控制的验证"""
            async with semaphore:
                result = await self.validate_stock_data(code)
                result['code'] = code
                return result

        # 并发验证
        tasks = [validate_with_semaphore(code) for code in codes]
        results = await asyncio.gather(*tasks)

        # 统计
        invalid_count = sum(1 for r in results if not r['is_valid'])
        logger.info(f"✓ 批量验证完成: {invalid_count}/{len(codes)} 只股票有问题")

        return results

    # ==================== 数据质量报告 ====================

    async def get_data_quality_report(self) -> Dict:
        """
        获取数据质量报告

        Returns:
            质量报告字典 {
                total_stocks: int,
                stocks_with_data: int,
                stocks_without_data: int,
                total_records: int,
                avg_records_per_stock: float,
                quality_score: float,
                recommendations: List[str]
            }

        Examples:
            >>> service = DataValidationService()
            >>> report = await service.get_data_quality_report()
            >>> print(f"数据质量分数: {report['quality_score']}/100")
        """
        # 获取基础统计
        stats = await asyncio.to_thread(self.stock_repo.get_data_statistics)

        # 计算质量分数
        quality_score = self._calculate_quality_score(stats)

        # 生成建议
        recommendations = self._generate_recommendations(stats)

        return {
            **stats,
            "quality_score": quality_score,
            "recommendations": recommendations
        }

    # ==================== 缺失数据识别 ====================

    async def get_stocks_without_data(self) -> List[Dict]:
        """
        获取没有日线数据的股票列表

        Returns:
            股票信息列表 [{code, name, market}, ...]

        Examples:
            >>> service = DataValidationService()
            >>> stocks = await service.get_stocks_without_data()
            >>> for stock in stocks:
            ...     print(f"{stock['name']} ({stock['code']}) 缺少数据")
        """
        return await asyncio.to_thread(self.stock_repo.get_stocks_without_data)

    async def get_stocks_with_data(self) -> List[str]:
        """
        获取有日线数据的股票代码列表

        Returns:
            股票代码列表

        Examples:
            >>> service = DataValidationService()
            >>> codes = await service.get_stocks_with_data()
            >>> print(f"共有 {len(codes)} 只股票有数据")
        """
        return await asyncio.to_thread(self.stock_repo.get_stocks_with_data)

    async def get_data_coverage_rate(self) -> float:
        """
        获取数据覆盖率

        Returns:
            覆盖率（0.0 - 1.0）

        Examples:
            >>> service = DataValidationService()
            >>> rate = await service.get_data_coverage_rate()
            >>> print(f"数据覆盖率: {rate * 100:.2f}%")
        """
        stats = await asyncio.to_thread(self.stock_repo.get_data_statistics)

        total = stats.get('total_stocks', 0)
        with_data = stats.get('stocks_with_data', 0)

        if total == 0:
            return 0.0

        return with_data / total

    # ==================== 数据异常检测 ====================

    async def find_outdated_stocks(self, days: int = 7) -> List[Dict]:
        """
        查找数据过期的股票

        Args:
            days: 过期天数阈值（默认7天）

        Returns:
            过期股票列表 [{code, name, latest_date, days_ago}, ...]

        Examples:
            >>> service = DataValidationService()
            >>> outdated = await service.find_outdated_stocks(days=7)
            >>> print(f"发现 {len(outdated)} 只股票数据过期")
        """
        from datetime import datetime, timedelta

        # 获取所有有数据的股票
        codes = await self.get_stocks_with_data()

        # 计算过期日期阈值
        threshold = datetime.now() - timedelta(days=days)

        outdated = []

        for code in codes:
            latest = await asyncio.to_thread(self.stock_repo.get_latest_date, code)

            if latest and latest < threshold:
                stock_info = await self.stock_list_service.get_stock_by_code(code)
                days_ago = (datetime.now() - latest).days

                outdated.append({
                    "code": code,
                    "name": stock_info.get('name', '') if stock_info else '',
                    "latest_date": latest.strftime('%Y-%m-%d'),
                    "days_ago": days_ago
                })

        logger.info(f"发现 {len(outdated)} 只股票数据过期（>{days}天）")
        return outdated

    async def find_stocks_with_insufficient_data(self, min_records: int = 100) -> List[Dict]:
        """
        查找数据量不足的股票

        Args:
            min_records: 最小记录数阈值（默认100）

        Returns:
            数据量不足的股票列表 [{code, name, record_count}, ...]

        Examples:
            >>> service = DataValidationService()
            >>> insufficient = await service.find_stocks_with_insufficient_data(min_records=100)
        """
        # 获取所有有数据的股票
        codes = await self.get_stocks_with_data()

        insufficient = []

        for code in codes:
            validation = await self.validate_stock_data(code)

            if validation['record_count'] < min_records:
                stock_info = await self.stock_list_service.get_stock_by_code(code)

                insufficient.append({
                    "code": code,
                    "name": stock_info.get('name', '') if stock_info else '',
                    "record_count": validation['record_count']
                })

        logger.info(f"发现 {len(insufficient)} 只股票数据量不足（<{min_records}条）")
        return insufficient

    # ==================== 辅助方法 ====================

    def _calculate_quality_score(self, stats: Dict) -> float:
        """
        计算数据质量分数（0-100）

        评分标准：
        - 数据覆盖率: 40分
        - 平均记录数: 30分
        - 完整性: 30分

        Args:
            stats: 数据统计字典

        Returns:
            质量分数（0-100）
        """
        score = 0.0

        total_stocks = stats.get('total_stocks', 0)
        stocks_with_data = stats.get('stocks_with_data', 0)
        avg_records = stats.get('avg_records_per_stock', 0)

        # 1. 数据覆盖率（40分）
        if total_stocks > 0:
            coverage_rate = stocks_with_data / total_stocks
            score += coverage_rate * 40

        # 2. 平均记录数（30分）
        # 假设500条记录为满分
        if avg_records > 0:
            record_score = min(avg_records / 500, 1.0) * 30
            score += record_score

        # 3. 完整性（30分）
        # 假设无缺失数据为满分
        stocks_without_data = stats.get('stocks_without_data', 0)
        if total_stocks > 0:
            completeness = 1 - (stocks_without_data / total_stocks)
            score += completeness * 30

        return round(score, 2)

    def _generate_recommendations(self, stats: Dict) -> List[str]:
        """
        根据统计数据生成改进建议

        Args:
            stats: 数据统计字典

        Returns:
            建议列表
        """
        recommendations = []

        total_stocks = stats.get('total_stocks', 0)
        stocks_with_data = stats.get('stocks_with_data', 0)
        stocks_without_data = stats.get('stocks_without_data', 0)
        avg_records = stats.get('avg_records_per_stock', 0)

        # 覆盖率建议
        if total_stocks > 0:
            coverage_rate = stocks_with_data / total_stocks

            if coverage_rate < 0.5:
                recommendations.append(
                    f"数据覆盖率较低 ({coverage_rate * 100:.1f}%)，建议下载缺失股票数据"
                )
            elif coverage_rate < 0.8:
                recommendations.append(
                    f"数据覆盖率中等 ({coverage_rate * 100:.1f}%)，建议补充缺失股票"
                )

        # 缺失数据建议
        if stocks_without_data > 0:
            recommendations.append(
                f"有 {stocks_without_data} 只股票缺少日线数据，建议批量下载"
            )

        # 记录数建议
        if avg_records < 100:
            recommendations.append(
                f"平均记录数较少 ({avg_records:.1f} 条)，建议增加下载年数"
            )
        elif avg_records < 250:
            recommendations.append(
                f"平均记录数中等 ({avg_records:.1f} 条)，可考虑增加历史数据"
            )

        # 默认建议
        if not recommendations:
            recommendations.append("数据质量良好，建议定期增量更新")

        return recommendations
