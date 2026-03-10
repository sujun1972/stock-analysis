"""
情绪周期量化计算模块 - 配置文件

定义赚钱效应模型的阈值、游资字典和其他配置参数。
"""

from typing import Dict, List
from dataclasses import dataclass


# ==================== 情绪周期阶段阈值配置 ====================

@dataclass
class CycleThresholds:
    """情绪周期阶段判断阈值"""

    # 冰点期 (Freezing) - 市场情绪极度低迷
    FREEZING = {
        'limit_down_count_min': 50,  # 跌停家数 ≥ 50
        'limit_ratio_max': 0.5,      # 涨停/跌停比 < 0.5
        'blast_rate_min': 0.6,       # 炸板率 > 60%
        'money_making_index_max': 30,  # 赚钱效应指数 < 30
        'continuous_decline': True,   # 连板高度持续下降
        'description': '市场情绪冰点，跌停家数多，赚钱效应差'
    }

    # 启动期 (Starting) - 市场情绪开始回暖
    STARTING = {
        'limit_up_count_min': 20,    # 涨停家数 ≥ 20
        'limit_down_count_max': 30,  # 跌停家数 < 30
        'limit_ratio_min': 1.5,      # 涨停/跌停比 > 1.5
        'blast_rate_max': 0.4,       # 炸板率 < 40%
        'money_making_index_min': 30,  # 赚钱效应指数 30-60
        'money_making_index_max': 60,
        'continuous_growth': True,   # 连板高度开始增长
        'description': '市场情绪启动，涨停数增加，连板高度开始提升'
    }

    # 发酵期 (Fermenting) - 市场情绪高涨
    FERMENTING = {
        'limit_up_count_min': 40,    # 涨停家数 ≥ 40
        'limit_ratio_min': 3.0,      # 涨停/跌停比 > 3
        'max_continuous_days_min': 5,  # 最高连板 ≥ 5天
        'blast_rate_max': 0.3,       # 炸板率 < 30%
        'money_making_index_min': 70,  # 赚钱效应指数 > 70
        'continuous_high': True,     # 连板高度保持高位
        'description': '市场情绪火热，涨停潮，连板高度创新高'
    }

    # 退潮期 (Retreating) - 市场情绪开始降温
    RETREATING = {
        'blast_rate_min': 0.5,       # 炸板率 > 50%
        'continuous_decline': True,  # 连板高度下降
        'limit_ratio_decline': True,  # 涨跌比开始下降
        'money_making_index_min': 40,  # 赚钱效应指数 40-70
        'money_making_index_max': 70,
        'volume_shrink': True,       # 成交额萎缩
        'description': '市场情绪退潮，炸板增多，连板高度下降'
    }


# ==================== 赚钱效应指数权重配置 ====================

MONEY_MAKING_INDEX_WEIGHTS = {
    'limit_up_count': 0.30,      # 涨停数权重 30%
    'limit_ratio': 0.25,         # 涨跌比权重 25%
    'continuous_height': 0.25,   # 连板高度权重 25%
    'blast_rate': 0.20,          # 炸板率权重 20%
}

# 归一化参数
NORMALIZATION_PARAMS = {
    'limit_up_count_max': 100,   # 涨停数满分参考值
    'limit_ratio_max': 5.0,      # 涨跌比满分参考值
    'continuous_days_max': 10,   # 连板天数满分参考值
}


# ==================== 游资席位分类配置 ====================

class HotMoneyDict:
    """游资字典 - 席位分类规则"""

    # 席位类型定义
    SEAT_TYPES = {
        'top_tier': '[一线顶级游资]',      # 市场风向标
        'famous': '[知名游资]',            # 二线知名游资
        'retail_base': '[散户大本营]',     # 散户集中地
        'institution': '[机构]',           # 机构专用
        'unknown': '[未知席位]'            # 未分类
    }

    # 一线顶级游资 - 关键词匹配
    TOP_TIER_KEYWORDS = [
        # 上海系
        '溧阳路', '中信上海溧阳', '东方路', '中信东方',
        # 广东系
        '顺德大良', '国泰顺德', '荣超商务', '益田路荣超', '江苏大厦', '益田路江苏',
        '蛇口工业', '招商蛇口',
        # 西南系
        '成都北一环', '国泰成都', '天府二街', '申万成都', '重庆民权', '申万重庆',
        # 浙江系
        '银河绍兴', '绍兴', '上塘路', '财通上塘', '台州解放', '财通台州',
        '庆春路', '中信建投杭州',
    ]

    # 散户大本营 - 关键词匹配
    RETAIL_BASE_KEYWORDS = [
        '拉萨', '西藏', '东财拉萨',
        '拉萨团结路', '拉萨东环路', '拉萨金珠',
        '深圳福田', '华泰福田',
    ]

    # 知名游资 - 券商匹配
    FAMOUS_BROKERS = [
        '中信证券', '国泰君安', '华泰证券', '海通证券',
        '招商证券', '申万宏源', '光大证券', '银河证券',
        '中信建投', '财通证券', '国信证券', '广发证券',
    ]

    # 机构 - 关键词匹配
    INSTITUTION_KEYWORDS = [
        '机构专用', '机构', '基金', '社保', 'QFII', 'RQFII',
        '保险', '信托', '资管', '专户',
    ]

    # 城市到地区映射
    CITY_TO_REGION = {
        '上海': '华东', '杭州': '华东', '宁波': '华东', '苏州': '华东',
        '南京': '华东', '绍兴': '华东', '台州': '华东',
        '深圳': '华南', '广州': '华南', '佛山': '华南', '东莞': '华南',
        '成都': '西南', '重庆': '西南', '昆明': '西南',
        '北京': '华北', '天津': '华北',
        '西安': '西北', '拉萨': '西南',
    }

    # 交易风格定义
    TRADE_STYLES = {
        'aggressive': '激进',    # 打板、追涨
        'steady': '稳健',        # 低吸、波段
        'short_term': '短线',    # T+1/T+2
        'swing': '波段',         # 持仓3-10天
        'mid_term': '中长线',    # 持仓10天以上
    }


# ==================== 统计分析配置 ====================

class AnalysisConfig:
    """统计分析配置"""

    # 机构净买入榜单配置
    INSTITUTION_TOP_COUNT = 3  # 默认显示前3名

    # 游资打板榜单配置
    HOT_MONEY_TOP_COUNT = 10  # 默认显示前10名

    # 活跃度判断标准 (最近N天出现次数)
    ACTIVITY_PERIOD_DAYS = 30  # 统计最近30天
    ACTIVITY_THRESHOLD_HIGH = 10  # 高活跃: ≥10次
    ACTIVITY_THRESHOLD_MEDIUM = 5  # 中等活跃: 5-9次
    # 低活跃: <5次

    # 胜率计算参数
    WIN_RATE_HOLD_DAYS = 3  # 持仓3天后计算收益
    WIN_RATE_THRESHOLD = 0.05  # 盈利阈值 (5%)

    # 龙头股判断标准
    LEADING_STOCK_CRITERIA = {
        'continuous_days_min': 3,  # 至少3连板
        'turnover_rate_min': 10,   # 换手率 ≥ 10%
        'is_first_limit_up': True,  # 首板优先
    }


# ==================== 数据质量配置 ====================

class DataQualityConfig:
    """数据质量和异常值处理配置"""

    # 异常值过滤
    MAX_LIMIT_UP_COUNT = 200  # 涨停数最大值 (超过视为异常)
    MAX_LIMIT_DOWN_COUNT = 200  # 跌停数最大值
    MAX_BLAST_RATE = 1.0  # 炸板率最大值 (100%)
    MIN_BLAST_RATE = 0.0  # 炸板率最小值

    # 数据完整性检查
    REQUIRED_FIELDS = [
        'limit_up_count', 'limit_down_count', 'blast_count',
        'max_continuous_days', 'total_amount'
    ]

    # ST股票处理
    EXCLUDE_ST_STOCKS = True  # 是否排除ST股票
    ST_PATTERNS = ['ST', '*ST', 'S*ST', 'SST']


# ==================== 缓存配置 ====================

class CacheConfig:
    """缓存配置"""

    # 启用缓存
    ENABLE_CACHE = True

    # 缓存过期时间 (秒)
    CACHE_EXPIRE_SECONDS = {
        'sentiment_cycle': 3600,      # 情绪周期数据 1小时
        'hot_money_ranking': 1800,    # 游资排行 30分钟
        'dragon_tiger_analysis': 1800,  # 龙虎榜分析 30分钟
    }


# ==================== 日志配置 ====================

class LogConfig:
    """日志配置"""

    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>'


# ==================== 导出配置对象 ====================

# 创建配置实例
cycle_thresholds = CycleThresholds()
hot_money_dict = HotMoneyDict()
analysis_config = AnalysisConfig()
data_quality_config = DataQualityConfig()
cache_config = CacheConfig()
log_config = LogConfig()


# ==================== 辅助函数 ====================

def get_seat_type_label(seat_type: str) -> str:
    """
    获取席位类型的中文标签

    Args:
        seat_type: 席位类型英文 (top_tier/famous/retail_base/institution/unknown)

    Returns:
        中文标签
    """
    return HotMoneyDict.SEAT_TYPES.get(seat_type, '[未知席位]')


def get_cycle_stage_cn(cycle_stage: str) -> str:
    """
    获取情绪周期阶段的中文名称

    Args:
        cycle_stage: 阶段英文名 (freezing/starting/fermenting/retreating)

    Returns:
        中文阶段名
    """
    mapping = {
        'freezing': '冰点',
        'starting': '启动',
        'fermenting': '发酵',
        'retreating': '退潮'
    }
    return mapping.get(cycle_stage, '未知')


def get_trade_style_cn(style_en: str) -> str:
    """
    获取交易风格的中文名称

    Args:
        style_en: 英文交易风格

    Returns:
        中文交易风格
    """
    mapping = {
        'aggressive': '激进',
        'steady': '稳健',
        'short_term': '短线',
        'swing': '波段',
        'mid_term': '中长线'
    }
    return mapping.get(style_en, '未知')


# ==================== 配置验证 ====================

def validate_config():
    """验证配置的合法性"""
    errors = []

    # 验证权重总和
    weight_sum = sum(MONEY_MAKING_INDEX_WEIGHTS.values())
    if abs(weight_sum - 1.0) > 0.01:
        errors.append(f"赚钱效应指数权重总和应为1.0，当前为{weight_sum}")

    # 验证归一化参数
    for key, value in NORMALIZATION_PARAMS.items():
        if value <= 0:
            errors.append(f"归一化参数 {key} 必须大于0")

    if errors:
        raise ValueError(f"配置验证失败:\n" + "\n".join(errors))


# 启动时验证配置
validate_config()
