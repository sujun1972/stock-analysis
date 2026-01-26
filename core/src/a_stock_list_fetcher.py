import tushare as ts
import akshare as ak
import pandas as pd
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 导入新配置系统
try:
    from .config.settings import get_settings
except ImportError:
    from src.config.settings import get_settings

# 获取配置实例
settings = get_settings()
TUSHARE_TOKEN = settings.TUSHARE_TOKEN or ""
DATABASE_CONFIG = {
    'host': settings.DATABASE_HOST,
    'port': settings.DATABASE_PORT,
    'database': settings.DATABASE_NAME,
    'user': settings.DATABASE_USER,
    'password': settings.DATABASE_PASSWORD
}

def fetch_akshare_stock_list(save_path: str = "./a_stock_list.csv",
                             save_to_db: bool = False) -> bool:
    """
    使用AkShare获取全部A股股票列表并保存到本地CSV文件和/或数据库（推荐，免费无限制）

    参数:
        save_path: 保存CSV文件的路径，默认为当前目录下的a_stock_list.csv
        save_to_db: 是否保存到数据库，默认为False

    返回:
        bool: 操作是否成功
    """
    try:
        print("正在使用AkShare获取A股列表数据...")

        # 使用AkShare获取A股实时行情数据（包含所有上市股票）
        stock_zh_a_spot_em_df = ak.stock_zh_a_spot_em()

        # 选择需要的列并重命名以匹配原有格式
        # AkShare返回的列名：代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, 市盈率-动态, 市净率
        column_mapping = {
            '代码': 'symbol',
            '名称': 'name',
            '市盈率-动态': 'pe',
            '市净率': 'pb',
            '总市值': 'total_mv',
            '流通市值': 'circ_mv'
        }

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
        print(f"✅ 成功使用AkShare获取 {len(a_stocks)} 只A股股票列表")
        print(f"💾 CSV数据已保存至: {save_path}")

        # 如果选择保存到数据库
        if save_to_db:
            db_success = save_stock_list_to_database(a_stocks)
            if not db_success:
                print("⚠️ CSV文件保存成功，但数据库保存失败")

        # 显示前几行数据预览
        print("\n📊 数据预览:")
        print(a_stocks.head(10))

        # 显示各市场分布
        print("\n📈 各市场股票数量分布:")
        market_distribution = a_stocks['market'].value_counts()
        print(market_distribution)

        return True

    except Exception as e:
        print(f"❌ 使用AkShare获取或保存数据时出错: {e}")
        return False

def fetch_and_save_a_stock_list(save_path: str = "./a_stock_list.csv",
                               save_to_db: bool = False,
                               data_source: str = 'akshare') -> bool:
    """
    获取全部A股股票列表并保存到本地CSV文件和/或数据库（智能选择数据源）

    参数:
        save_path: 保存CSV文件的路径，默认为当前目录下的a_stock_list.csv
        save_to_db: 是否保存到数据库，默认为False
        data_source: 数据源选择，'akshare'(推荐) 或 'tushare'

    返回:
        bool: 操作是否成功
    """
    if data_source == 'akshare':
        return fetch_akshare_stock_list(save_path, save_to_db)
    elif data_source == 'tushare':
        return fetch_tushare_stock_list(save_path, save_to_db)
    else:
        print(f"未知的数据源: {data_source}，默认使用AkShare")
        return fetch_akshare_stock_list(save_path, save_to_db)

def fetch_tushare_stock_list(save_path: str = "./a_stock_list.csv",
                             save_to_db: bool = False) -> bool:
    """
    使用Tushare获取全部A股股票列表并保存到本地CSV文件和/或数据库（备用方法）

    参数:
        save_path: 保存CSV文件的路径，默认为当前目录下的a_stock_list.csv
        save_to_db: 是否保存到数据库，默认为False

    返回:
        bool: 操作是否成功
    """
    try:
        # 检查TUSHARE_TOKEN是否已配置
        if not TUSHARE_TOKEN:
            print("❌ 错误: 请在 config/config.py 中配置 TUSHARE_TOKEN")
            return False
            
        # 1. 设置Token并初始化Pro接口
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        # 2. 获取股票列表基本信息
        print("正在从Tushare获取A股列表数据...")
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
        print(f"✅ 成功获取 {len(a_stocks)} 只A股股票列表")
        print(f"💾 CSV数据已保存至: {save_path}")
        
        # 6. 如果选择保存到数据库
        if save_to_db:
            db_success = save_stock_list_to_database(a_stocks)
            if not db_success:
                print("⚠️ CSV文件保存成功，但数据库保存失败")
        
        # 显示前几行数据预览
        print("\n📊 数据预览:")
        print(a_stocks.head(10))
        
        # 显示各市场分布
        print("\n📈 各市场股票数量分布:")
        market_distribution = a_stocks['market'].value_counts()
        print(market_distribution)
        
        return True
        
    except Exception as e:
        print(f"❌ 获取或保存数据时出错: {e}")
        return False

def save_stock_list_to_database(stock_df: pd.DataFrame) -> bool:
    """
    将股票列表数据保存到数据库
    
    参数:
        stock_df: 包含股票数据的DataFrame
        
    返回:
        bool: 操作是否成功
    """
    try:
        # 检查数据库配置是否存在
        if not DATABASE_CONFIG:
            print("❌ 错误: 请在 config/config.py 中配置 DATABASE_CONFIG")
            return False
            
        # 创建数据库连接
        db_url = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(db_url)
        
        # 测试数据库连接
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print("🔄 正在保存股票列表到数据库...")
        
        # 准备数据 - 确保列名和数据类型匹配数据库表结构
        # 添加创建时间和更新时间
        stock_df = stock_df.copy()
        stock_df['created_at'] = pd.Timestamp.now()
        stock_df['updated_at'] = pd.Timestamp.now()
        
        # 保存到数据库
        # 使用 if_exists='replace' 会先清空表再插入，适合全量更新
        # 使用 if_exists='append' 会追加数据，但可能导致重复
        stock_df.to_sql(
            'stocks', 
            engine, 
            if_exists='replace',  # 替换原有数据
            index=False,
            method='multi'  # 批量插入
        )
        
        print(f"✅ 成功保存 {len(stock_df)} 只股票到数据库")
        return True
        
    except SQLAlchemyError as e:
        print(f"❌ 数据库操作失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 保存到数据库时出错: {e}")
        return False

def get_a_stock_list_detailed(save_dir: str = "./stock_data", 
                             save_to_db: bool = False) -> Optional[pd.DataFrame]:
    """
    获取更详细的A股列表信息，包含更多字段
    
    参数:
        save_dir: 数据保存目录
        save_to_db: 是否保存到数据库，默认为False
        
    返回:
        pd.DataFrame: 包含详细信息的DataFrame，失败时返回None
    """
    try:
        # 检查TUSHARE_TOKEN是否已配置
        if not TUSHARE_TOKEN:
            print("❌ 错误: 请在 config/config.py 中配置 TUSHARE_TOKEN")
            return None
            
        ts.set_token(TUSHARE_TOKEN)
        pro = ts.pro_api()
        
        # 创建保存目录
        os.makedirs(save_dir, exist_ok=True)
        
        # 获取更详细的字段
        print("正在获取详细的A股列表数据...")
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
        
        print(f"✅ 详细数据已保存至: {detailed_path}")
        print(f"✅ 基础数据已保存至: {basic_path}")
        print(f"📊 总共获取 {len(a_stocks_detailed)} 只A股")
        
        # 如果选择保存到数据库
        if save_to_db:
            db_success = save_stock_list_to_database(a_stocks_detailed[basic_fields])
            if not db_success:
                print("⚠️ CSV文件保存成功，但数据库保存失败")
        
        return a_stocks_detailed
        
    except Exception as e:
        print(f"❌ 获取详细数据时出错: {e}")
        return None

def update_stock_list_from_database() -> Optional[pd.DataFrame]:
    """
    从数据库获取股票列表
    
    返回:
        pd.DataFrame: 包含股票数据的DataFrame，失败时返回None
    """
    try:
        if not DATABASE_CONFIG:
            print("❌ 错误: 请在 config/config.py 中配置 DATABASE_CONFIG")
            return None
            
        # 创建数据库连接
        db_url = f"postgresql://{DATABASE_CONFIG['user']}:{DATABASE_CONFIG['password']}@{DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}/{DATABASE_CONFIG['database']}"
        engine = create_engine(db_url)
        
        print("🔄 正在从数据库读取股票列表...")
        
        # 从数据库读取数据
        stock_df = pd.read_sql('stocks', engine)
        
        print(f"✅ 从数据库成功读取 {len(stock_df)} 只股票")
        return stock_df
        
    except Exception as e:
        print(f"❌ 从数据库读取数据时出错: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--db-only":
        print("🚀 模式: 只保存到数据库")
        
        # 使用临时文件路径，保存后立即删除
        temp_csv_path = "./data/temp_stock_list.csv"
        success = fetch_and_save_a_stock_list(
            save_path=temp_csv_path,
            save_to_db=True
        )
        
        # 删除临时CSV文件
        if os.path.exists(temp_csv_path):
            os.remove(temp_csv_path)
            print(f"🗑️  已删除临时CSV文件")
            
    else:
        # 默认：两者都保存
        print("📊 模式: 同时保存到CSV和数据库")
        success = fetch_and_save_a_stock_list(
            save_path="./data/a_stock_list.csv",
            save_to_db=True
        )
    
    if success:
        print("\n🎉 A股列表获取完成！")
    else:
        print("\n💥 A股列表获取失败，请检查配置和网络连接")
