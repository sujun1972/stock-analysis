#!/usr/bin/env python3
"""
快速测试脚本 - 验证 Stocks API 重写是否成功

无需 pytest，直接运行验证基本功能

作者: Backend Team
创建日期: 2026-02-01
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from unittest.mock import AsyncMock, patch
import pandas as pd


async def test_get_stock_list():
    """测试 GET /api/stocks/list"""
    print("测试 1: GET /api/stocks/list ... ", end="")

    from app.api.endpoints.stocks import get_stock_list

    # Mock 数据
    mock_stocks = [
        {"code": "000001", "name": "平安银行", "market": "主板"},
        {"code": "000002", "name": "万科A", "market": "主板"},
    ]

    with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
        mock_adapter.get_stock_list = AsyncMock(return_value=mock_stocks)

        response = await get_stock_list(
            market=None,
            status_filter="正常",
            search=None,
            page=1,
            page_size=20
        )

        assert response["code"] == 200, "状态码应为 200"
        assert response["data"]["total"] == 2, "总数应为 2"
        assert len(response["data"]["items"]) == 2, "返回 2 条记录"

    print("✅ 通过")


async def test_get_stock_info():
    """测试 GET /api/stocks/{code}"""
    print("测试 2: GET /api/stocks/{code} ... ", end="")

    from app.api.endpoints.stocks import get_stock_info

    mock_stock = {
        "code": "000001",
        "name": "平安银行",
        "market": "主板"
    }

    with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
        mock_adapter.get_stock_info = AsyncMock(return_value=mock_stock)

        response = await get_stock_info(code="000001")

        assert response["code"] == 200, "状态码应为 200"
        assert response["data"]["code"] == "000001", "股票代码正确"

    print("✅ 通过")


async def test_get_stock_info_not_found():
    """测试股票不存在"""
    print("测试 3: GET /api/stocks/{code} (不存在) ... ", end="")

    from app.api.endpoints.stocks import get_stock_info

    with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
        mock_adapter.get_stock_info = AsyncMock(return_value=None)

        response = await get_stock_info(code="999999")

        assert response["code"] == 404, "状态码应为 404"

    print("✅ 通过")


async def test_get_stock_daily_data():
    """测试 GET /api/stocks/{code}/daily"""
    print("测试 4: GET /api/stocks/{code}/daily ... ", end="")

    from app.api.endpoints.stocks import get_stock_daily_data

    mock_df = pd.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "close": [10.0, 10.5]
    })

    with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
        mock_adapter.get_daily_data = AsyncMock(return_value=mock_df)

        response = await get_stock_daily_data(
            code="000001",
            start_date="2024-01-01",
            end_date="2024-01-02",
            limit=100
        )

        assert response["code"] == 200, "状态码应为 200"
        assert response["data"]["record_count"] == 2, "返回 2 条记录"

    print("✅ 通过")


async def test_update_stock_list():
    """测试 POST /api/stocks/update (未实现)"""
    print("测试 5: POST /api/stocks/update (未实现) ... ", end="")

    from app.api.endpoints.stocks import update_stock_list

    response = await update_stock_list()

    assert response["code"] == 501, "状态码应为 501"

    print("✅ 通过")


async def test_get_minute_data():
    """测试 GET /api/stocks/{code}/minute"""
    print("测试 6: GET /api/stocks/{code}/minute ... ", end="")

    from app.api.endpoints.stocks import get_minute_data

    mock_df = pd.DataFrame({
        "time": ["09:31", "09:32"],
        "price": [10.0, 10.1]
    })

    with patch('app.api.endpoints.stocks.data_adapter') as mock_adapter:
        mock_adapter.is_trading_day = AsyncMock(return_value=True)
        mock_adapter.get_minute_data = AsyncMock(return_value=mock_df)

        response = await get_minute_data(
            code="000001",
            trade_date="2024-01-15",
            period="1min"
        )

        assert response["code"] == 200, "状态码应为 200"
        assert response["data"]["record_count"] == 2, "返回 2 条记录"

    print("✅ 通过")


async def main():
    """运行所有测试"""
    print("=" * 50)
    print("  快速测试 - Stocks API 重写验证")
    print("=" * 50)
    print()

    tests = [
        test_get_stock_list,
        test_get_stock_info,
        test_get_stock_info_not_found,
        test_get_stock_daily_data,
        test_update_stock_list,
        test_get_minute_data,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            await test()
            passed += 1
        except Exception as e:
            print(f"❌ 失败: {e}")
            failed += 1

    print()
    print("=" * 50)
    print(f"  测试结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    if failed == 0:
        print()
        print("🎉 所有测试通过！Stocks API 重写成功！")
        print()
        return 0
    else:
        print()
        print("⚠️ 部分测试失败，请检查代码")
        print()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
