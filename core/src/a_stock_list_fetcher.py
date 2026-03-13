import pandas as pd
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

# 导入配置系统
try:
    from .config.settings import get_settings
    from .config.data_source_helper import create_provider, get_data_source_config
except ImportError:
    from src.config.settings import get_settings
    from src.config.data_source_helper import create_provider, get_data_source_config

# 导入Response和异常类
try:
    from .utils.response import Response
    from .exceptions import DataProviderError, DatabaseError, NetworkError
except ImportError:
    from src.utils.response import Response
    from src.exceptions import DataProviderError, DatabaseError, NetworkError

# 获取配置实例
settings = get_settings()
DATABASE_CONFIG = {
    'host': settings.DATABASE_HOST,
    'port': settings.DATABASE_PORT,
    'database': settings.DATABASE_NAME,
    'user': settings.DATABASE_USER,
    'password': settings.DATABASE_PASSWORD
}

# 获取数据源配置
_data_source_config = get_data_source_config()
DATA_SOURCE = _data_source_config["data_source"]
TUSHARE_TOKEN = _data_source_config["tushare_token"]

def fetch_stock_list(save_path: str = "./a_stock_list.csv",
                    save_to_db: bool = False,
                    source: Optional[str] = None) -> Response:
    """
    获取全部A股股票列表并保存到本地CSV文件和/或数据库

    支持从配置的数据源获取（akshare/tushare）

    参数:
        save_path: 保存CSV文件的路径，默认为当前目录下的a_stock_list.csv
        save_to_db: 是否保存到数据库，默认为False
        source: 强制指定数据源（None=使用配置的数据源）

    返回:
        Response: 成功返回股票列表，失败返回错误信息
    """
    try:
        actual_source = source or DATA_SOURCE
        logger.info(f"正在获取A股列表数据（数据源：{actual_source}）...")

        # 根据数据源获取股票列表
        if actual_source == "tushare":
            provider = create_provider("data")
            df = provider.get_stock_list()
            # Tushare已经返回标准格式，直接使用
            a_stocks = df
        else:
            # 使用AkShare获取
            import akshare as ak
            stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

        # 创建标准化的DataFrame
        a_stocks = pd.DataFrame()
        a_stocks['symbol'] = stock_zh_a_spot_em_df['代码']
        a_stocks['name'] = stock_zh_a_spot_em_df['名称']

        # 生成ts_code（股票代码.交易所）
        # 6开头的是上海，0/3开头的是深圳
        a_stocks['ts_code'] = a_stocks['symbol'].apply(
            lambda x: f"{x}.SH" if x.startswith('6') else f"{x}.SZ"
        )

        # 添加市场类型
        def get_market_type(code):
            if code.startswith('688'):
                return '科创板'
            elif code.startswith('689'):
                return '科创板'
            elif code.startswith('300'):
                return '创业板'
            elif code.startswith('000') or code.startswith('001'):
                return '主板'
            elif code.startswith('002'):
                return '中小板'
            elif code.startswith('600') or code.startswith('601') or code.startswith('603'):
                return '主板'
            else:
                return '其他'

        a_stocks['market'] = a_stocks['symbol'].apply(get_market_type)

        # 添加交易所信息
        a_stocks['exchange'] = a_stocks['symbol'].apply(
            lambda x: 'SSE' if x.startswith('6') else 'SZSE'
        )

        # 重新排列列顺序
        a_stocks = a_stocks[['ts_code', 'symbol', 'name', 'market', 'exchange']]

        # 按股票代码排序
        a_stocks = a_stocks.sort_values('ts_code').reset_index(drop=True)

        # 保存到CSV文件
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
        a_stocks.to_csv(save_path, index=False, encoding='utf-8-sig')
        logger.success(f"✅ 成功使用AkShare获取 {len(a_stocks)} 只A股股票列表")
        logger.info(f"💾 CSV数据已保存至: {save_path}")

        # 如果选择保存到数据库
        db_result = None
        if save_to_db:
            db_result = save_stock_list_to_database(a_stocks)
            if db_result.is_error():
                logger.error(f"⚠️ CSV文件保存成功，但数据库保存失败: {db_result.error}")

        # 显示前几行数据预览
        logger.info("\n📊 数据预览:")
        logger.info(a_stocks.head(10))

        # 显示各市场分布
        logger.info("\n📈 各市场股票数量分布:")
        market_distribution = a_stocks['market'].value_counts()
        logger.info(f"{market_distribution}")

        return Response.success(
            data=a_stocks,
            message=f"成功获取并保存{len(a_stocks)}只股票",
            n_stocks=len(a_stocks),
            save_path=save_path,
            db_saved=db_result.is_success() if db_result else False
        )

    except KeyError as e:
        # 数据格式错误（AkShare返回的数据列名不匹配）
        logger.error(f"数据格式错误: {e}")
        return Response.error(
            error=f"AkShare数据格式错误: {str(e)}",
            error_code="AKSHARE_DATA_FORMAT_ERROR",
            error_detail=str(e)
        )

    except (IOError, OSError) as e:
        # 文件保存错误
        logger.error(f"文件保存失败: {e}")
        return Response.error(
            error=f"CSV文件保存失败: {str(e)}",
            error_code="FILE_SAVE_ERROR",
            save_path=save_path,
            error_detail=str(e)
        )

    except DataProviderError as e:
        # 已知的数据源异常
        logger.error(f"数据源异常: {e.message}")
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            **e.context
        )

    except Exception as e:
        # 未预期的异常
        logger.error(f"使用AkShare获取股票列表失败(未预期异常): {e}")
        return Response.error(
            error=f"获取股票列表失败: {str(e)}",
            error_code="FETCH_STOCK_LIST_FAILED",
            data_source="akshare",
            error_detail=str(e)
        )

def fetch_and_save_a_stock_list(save_path: str = "./a_stock_list.csv",
                               save_to_db: bool = False,
                               data_source: str = 'akshare') -> Response:
    """
    获取全部A股股票列表并保存到本地CSV文件和/或数据库（智能选择数据源）

    参数:
        save_path: 保存CSV文件的路径，默认为当前目录下的a_stock_list.csv
        save_to_db: 是否保存到数据库，默认为False
        data_source: 数据源选择，'akshare'(推荐) 或 'tushare'

    返回:
        Response: 成功返回股票列表，失败返回错误信息
    """
    if data_source == 'akshare':
        return fetch_akshare_stock_list(save_path, save_to_db)
    elif data_source == 'tushare':
        return fetch_tushare_stock_list(save_path, save_to_db)
    else:
        logger.warning(f"未知的数据源: {data_source}，默认使用AkShare")
        return fetch_akshare_stock_list(save_path, save_to_db)

def fetch_tushare_stock_list(save_path: str = "./a_stock_list.csv",
                             save_to_db: bool = False) -> Response:
    """
    使用Tushare获取全部A股股票列表并保存到本地CSV文件和/或数据库（备用方法）

    参数:
        save_path: 保存CSV文件的路径，默认为当前目录下的a_stock_list.csv
        save_to_db: 是否保存到数据库，默认为False

    返回:
        Response: 成功返回股票列表，失败返回错误信息
    """
    try:
        # 检查TUSHARE_TOKEN是否已配置
        if not TUSHARE_TOKEN:
            logger.error("❌ 错误: 请在 config/config.py 中配置 TUSHARE_TOKEN")
            return Response.error(
                error="Tushare Token未配置",
                error_code="TUSHARE_TOKEN_NOT_CONFIGURED",
                message="请在 config/config.py 中配置 TUSHARE_TOKEN"
            )

        # 1. 设置Token并初始化Pro接口
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()

        # 2. 获取股票列表基本信息
        logger.info("正在从Tushare获取A股列表数据...")
        stock_basic = pro.stock_basic(
            exchange='',  # 空字符串获取所有交易所
            list_status='L',  # L-上市，D-退市，P-暂停上市
            fields='ts_code,symbol,name,area,industry,market,list_date,is_hs'
        )

        # 3. 筛选A股（剔除科创板、北交所等，根据需求调整）
        # 主要A股市场：主板、中小板、创业板
        a_share_markets = ['主板', '中小板', '创业板']
        a_stocks = stock_basic[stock_basic['market'].isin(a_share_markets)]

        # 4. 按股票代码排序
        a_stocks = a_stocks.sort_values('ts_code').reset_index(drop=True)

        # 5. 保存到CSV文件（原有功能保持不变）
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        a_stocks.to_csv(save_path, index=False, encoding='utf-8-sig')
        logger.success(f"✅ 成功获取 {len(a_stocks)} 只A股股票列表")
        logger.info(f"💾 CSV数据已保存至: {save_path}")

        # 6. 如果选择保存到数据库
        db_result = None
        if save_to_db:
            db_result = save_stock_list_to_database(a_stocks)
            if db_result.is_error():
                logger.error(f"⚠️ CSV文件保存成功，但数据库保存失败: {db_result.error}")

        # 显示前几行数据预览
        logger.info("\n📊 数据预览:")
        logger.info(a_stocks.head(10))

        # 显示各市场分布
        logger.info("\n📈 各市场股票数量分布:")
        market_distribution = a_stocks['market'].value_counts()
        logger.info(f"{market_distribution}")

        return Response.success(
            data=a_stocks,
            message=f"成功获取并保存{len(a_stocks)}只股票",
            n_stocks=len(a_stocks),
            save_path=save_path,
            db_saved=db_result.is_success() if db_result else False
        )

    except KeyError as e:
        # 数据格式错误（Tushare返回的数据列名不匹配）
        logger.error(f"数据格式错误: {e}")
        return Response.error(
            error=f"Tushare数据格式错误: {str(e)}",
            error_code="TUSHARE_DATA_FORMAT_ERROR",
            error_detail=str(e)
        )

    except (IOError, OSError) as e:
        # 文件保存错误
        logger.error(f"文件保存失败: {e}")
        return Response.error(
            error=f"CSV文件保存失败: {str(e)}",
            error_code="FILE_SAVE_ERROR",
            save_path=save_path,
            error_detail=str(e)
        )

    except DataProviderError as e:
        # 已知的数据源异常
        logger.error(f"数据源异常: {e.message}")
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            **e.context
        )

    except Exception as e:
        # 未预期的异常
        logger.error(f"使用Tushare获取股票列表失败(未预期异常): {e}")
        return Response.error(
            error=f"获取股票列表失败: {str(e)}",
            error_code="FETCH_STOCK_LIST_FAILED",
            data_source="tushare",
            error_detail=str(e)
        )

def save_stock_list_to_database(stock_df: pd.DataFrame) -> Response:
    """
    将股票列表数据保存到数据库

    参数:
        stock_df: 包含股票数据的DataFrame

    返回:
        Response: 成功返回保存结果，失败返回错误信息
    """
    try:
        # 检查数据库配置是否存在
        if not DATABASE_CONFIG:
            logger.error("❌ 错误: 请在 config/config.py 中配置 DATABASE_CONFIG")
            return Response.error(
                error="数据库配置未设置",
                error_code="DATABASE_CONFIG_NOT_SET",
                message="请在 config/config.py 中配置 DATABASE_CONFIG"
            )

        # 创建数据库连接
        db_url = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(db_url)

        # 测试数据库连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        logger.info("🔄 正在保存股票列表到数据库...")

        # 准备数据 - 确保列名和数据类型匹配数据库表结构
        # 添加创建时间和更新时间
        stock_df = stock_df.copy()
        stock_df['created_at'] = pd.Timestamp.now()
        stock_df['updated_at'] = pd.Timestamp.now()

        # 保存到数据库
        # 使用 if_exists='replace' 会先清空表再插入，适合全量更新
        # 使用 if_exists='append' 会追加数据，但可能导致重复
        # 抑制 pandas 关于 DBAPI2 连接的警告
        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='pandas only supports SQLAlchemy')
            stock_df.to_sql(
                'stocks',
                engine,
                if_exists='replace',  # 替换原有数据
                index=False,
                method='multi'  # 批量插入
            )

        logger.success(f"✅ 成功保存 {len(stock_df)} 只股票到数据库")
        return Response.success(
            message=f"成功保存{len(stock_df)}只股票到数据库",
            n_saved=len(stock_df)
        )

    except SQLAlchemyError as e:
        # 数据库操作异常
        logger.error(f"❌ 数据库操作失败: {e}")
        return Response.error(
            error=f"数据库操作失败: {str(e)}",
            error_code="DATABASE_OPERATION_ERROR",
            error_detail=str(e)
        )

    except DatabaseError as e:
        # 已知的数据库异常
        logger.error(f"数据库异常: {e.message}")
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            **e.context
        )

    except Exception as e:
        # 未预期的异常
        logger.error(f"❌ 保存到数据库时出错(未预期异常): {e}")
        return Response.error(
            error=f"保存到数据库失败: {str(e)}",
            error_code="DATABASE_SAVE_FAILED",
            error_detail=str(e)
        )

def get_a_stock_list_detailed(save_dir: str = "./stock_data",
                             save_to_db: bool = False) -> Response:
    """
    获取更详细的A股列表信息，包含更多字段

    参数:
        save_dir: 数据保存目录
        save_to_db: 是否保存到数据库，默认为False

    返回:
        Response: 成功返回详细股票列表，失败返回错误信息
    """
    try:
        # 检查TUSHARE_TOKEN是否已配置
        if not TUSHARE_TOKEN:
            logger.error("❌ 错误: 请在 config/config.py 中配置 TUSHARE_TOKEN")
            return Response.error(
                error="Tushare Token未配置",
                error_code="TUSHARE_TOKEN_NOT_CONFIGURED",
                message="请在 config/config.py 中配置 TUSHARE_TOKEN"
            )

        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()

        # 创建保存目录
        os.makedirs(save_dir, exist_ok=True)

        # 获取更详细的字段
        logger.info("正在获取详细的A股列表数据...")
        stock_detailed = pro.stock_basic(
            exchange='',
            list_status='L',
            fields='''
                ts_code,symbol,name,area,industry,fullname,enname,market,
                exchange,curr_type,list_status,list_date,delist_date,is_hs
            '''
        )

        # 筛选主要A股
        a_share_markets = ['主板', '中小板', '创业板']
        a_stocks_detailed = stock_detailed[stock_detailed['market'].isin(a_share_markets)]

        # 保存详细数据到CSV
        detailed_path = os.path.join(save_dir, "a_stock_list_detailed.csv")
        a_stocks_detailed.to_csv(detailed_path, index=False, encoding='utf-8-sig')

        # 保存基础数据到CSV（简化版）
        basic_path = os.path.join(save_dir, "a_stock_list_basic.csv")
        basic_fields = ['ts_code', 'symbol', 'name', 'industry', 'market', 'list_date']
        a_stocks_detailed[basic_fields].to_csv(basic_path, index=False, encoding='utf-8-sig')

        logger.success(f"✅ 详细数据已保存至: {detailed_path}")
        logger.success(f"✅ 基础数据已保存至: {basic_path}")
        logger.info(f"📊 总共获取 {len(a_stocks_detailed)} 只A股")

        # 如果选择保存到数据库
        db_result = None
        if save_to_db:
            db_result = save_stock_list_to_database(a_stocks_detailed[basic_fields])
            if db_result.is_error():
                logger.error(f"⚠️ CSV文件保存成功，但数据库保存失败: {db_result.error}")

        return Response.success(
            data=a_stocks_detailed,
            message=f"成功获取{len(a_stocks_detailed)}只股票的详细信息",
            n_stocks=len(a_stocks_detailed),
            detailed_path=detailed_path,
            basic_path=basic_path,
            db_saved=db_result.is_success() if db_result else False
        )

    except KeyError as e:
        # 数据格式错误
        logger.error(f"数据格式错误: {e}")
        return Response.error(
            error=f"Tushare数据格式错误: {str(e)}",
            error_code="TUSHARE_DATA_FORMAT_ERROR",
            error_detail=str(e)
        )

    except (IOError, OSError) as e:
        # 文件保存错误
        logger.error(f"文件保存失败: {e}")
        return Response.error(
            error=f"CSV文件保存失败: {str(e)}",
            error_code="FILE_SAVE_ERROR",
            save_dir=save_dir,
            error_detail=str(e)
        )

    except DataProviderError as e:
        # 已知的数据源异常
        logger.error(f"数据源异常: {e.message}")
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            **e.context
        )

    except Exception as e:
        # 未预期的异常
        logger.error(f"获取详细股票列表失败(未预期异常): {e}")
        return Response.error(
            error=f"获取详细数据失败: {str(e)}",
            error_code="FETCH_DETAILED_LIST_FAILED",
            error_detail=str(e)
        )

def update_stock_list_from_database() -> Response:
    """
    从数据库获取股票列表

    返回:
        Response: 成功返回股票列表，失败返回错误信息
    """
    try:
        if not DATABASE_CONFIG:
            logger.error("❌ 错误: 请在 config/config.py 中配置 DATABASE_CONFIG")
            return Response.error(
                error="数据库配置未设置",
                error_code="DATABASE_CONFIG_NOT_SET",
                message="请在 config/config.py 中配置 DATABASE_CONFIG"
            )

        # 创建数据库连接
        db_url = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(db_url)

        logger.info("🔄 正在从数据库读取股票列表...")

        # 从数据库读取数据
        stock_df = pd.read_sql('stocks', engine)

        logger.success(f"✅ 从数据库成功读取 {len(stock_df)} 只股票")
        return Response.success(
            data=stock_df,
            message=f"成功从数据库读取{len(stock_df)}只股票",
            n_stocks=len(stock_df)
        )

    except SQLAlchemyError as e:
        # 数据库操作异常
        logger.error(f"❌ 数据库操作失败: {e}")
        return Response.error(
            error=f"数据库操作失败: {str(e)}",
            error_code="DATABASE_OPERATION_ERROR",
            error_detail=str(e)
        )

    except DatabaseError as e:
        # 已知的数据库异常
        logger.error(f"数据库异常: {e.message}")
        return Response.error(
            error=e.message,
            error_code=e.error_code,
            **e.context
        )

    except Exception as e:
        # 未预期的异常
        logger.error(f"❌ 从数据库读取数据时出错(未预期异常): {e}")
        return Response.error(
            error=f"从数据库读取失败: {str(e)}",
            error_code="DATABASE_READ_FAILED",
            error_detail=str(e)
        )

# 使用示例
if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--db-only":
        logger.info("🚀 模式: 只保存到数据库")

        # 使用临时文件路径，保存后立即删除
        temp_csv_path = "./data/temp_stock_list.csv"
        result = fetch_and_save_a_stock_list(
            save_path=temp_csv_path,
            save_to_db=True
        )

        # 删除临时CSV文件
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
            logger.info(f"🗑️  已删除临时CSV文件")

    else:
        # 默认：两者都保存
        logger.info("📊 模式: 同时保存到CSV和数据库")
        result = fetch_and_save_a_stock_list(
            save_path="./data/a_stock_list.csv",
            save_to_db=True
        )

    if result.is_success():
        logger.info("\n🎉 A股列表获取完成！")
    else:
        logger.error(f"\n💥 A股列表获取失败: {result.error}")
        logger.error(f"错误码: {result.error_code}")
