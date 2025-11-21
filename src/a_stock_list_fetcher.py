import tushare as ts
import pandas as pd
import os
from typing import Optional

# 尝试从config.config导入TUSHARE_TOKEN
try:
    from config.config import TUSHARE_TOKEN
except ImportError:
    # 如果直接运行此脚本时无法导入，尝试从上级目录导入
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.config import TUSHARE_TOKEN

def fetch_and_save_a_stock_list(save_path: str = "./a_stock_list.csv") -> bool:
    """
    获取Tushare全部A股股票列表并保存到本地CSV文件
    
    参数:
        save_path: 保存文件的路径，默认为当前目录下的a_stock_list.csv
        
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
        
        # 5. 保存到CSV文件
        # 确保目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        a_stocks.to_csv(save_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ 成功获取 {len(a_stocks)} 只A股股票列表")
        print(f"💾 数据已保存至: {save_path}")
        
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

def get_a_stock_list_detailed(save_dir: str = "./stock_data") -> Optional[pd.DataFrame]:
    """
    获取更详细的A股列表信息，包含更多字段
    
    参数:
        save_dir: 数据保存目录
        
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
        
        # 保存详细数据
        detailed_path = os.path.join(save_dir, "a_stock_list_detailed.csv")
        a_stocks_detailed.to_csv(detailed_path, index=False, encoding='utf-8-sig')
        
        # 保存基础数据（简化版）
        basic_path = os.path.join(save_dir, "a_stock_list_basic.csv")
        basic_fields = ['ts_code', 'symbol', 'name', 'industry', 'market', 'list_date']
        a_stocks_detailed[basic_fields].to_csv(basic_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ 详细数据已保存至: {detailed_path}")
        print(f"✅ 基础数据已保存至: {basic_path}")
        print(f"📊 总共获取 {len(a_stocks_detailed)} 只A股")
        
        return a_stocks_detailed
        
    except Exception as e:
        print(f"❌ 获取详细数据时出错: {e}")
        return None

# 使用示例
if __name__ == "__main__":
    # 方法一：获取基础A股列表
    success = fetch_and_save_a_stock_list(
        save_path="./data/a_stock_list.csv"
    )
    
    if success:
        print("\n🎉 基础A股列表获取完成！")
    else:
        print("\n💥 基础A股列表获取失败，请检查Token和网络连接")
    
    # 方法二：获取详细A股列表
    detailed_df = get_a_stock_list_detailed(
        save_dir="./data"
    )
    
    if detailed_df is not None:
        print("\n🎉 详细A股列表获取完成！")
        print("📋 数据字段包括:", ", ".join(detailed_df.columns.tolist()))