/**
 * 市场情绪分析相关的 React Query Hooks
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query/keys';
import { getQueryConfig, QUERY_TIME } from '@/lib/query/config';
import { toast } from 'sonner';

// 类型定义
export interface PremarketAnalysis {
  date: string;
  overnight_data?: OvernightData;
  collision_analysis?: CollisionAnalysis;
  news_list?: PremarketNews[];
  ai_summary?: string;
  generated_at?: string;
}

export interface OvernightData {
  us_market?: {
    dow_jones?: { close: number; change_pct: number };
    nasdaq?: { close: number; change_pct: number };
    sp500?: { close: number; change_pct: number };
  };
  asia_market?: {
    nikkei?: { close: number; change_pct: number };
    hang_seng?: { close: number; change_pct: number };
  };
  futures?: {
    a50?: { close: number; change_pct: number };
    nasdaq_futures?: { close: number; change_pct: number };
  };
  commodities?: {
    gold?: { price: number; change_pct: number };
    oil?: { price: number; change_pct: number };
  };
  forex?: {
    usd_cny?: { rate: number; change_pct: number };
    eur_usd?: { rate: number; change_pct: number };
  };
}

export interface CollisionAnalysis {
  hot_sectors?: Array<{
    sector: string;
    heat_score: number;
    stock_count: number;
    avg_change_pct: number;
    leaders: string[];
  }>;
  concept_themes?: Array<{
    concept: string;
    relevance_score: number;
    related_stocks: string[];
    news_count: number;
  }>;
  sentiment_score?: number;
  risk_level?: 'low' | 'medium' | 'high';
}

export interface PremarketNews {
  id: string;
  title: string;
  source: string;
  published_at: string;
  summary?: string;
  sentiment?: 'positive' | 'negative' | 'neutral';
  impact_level?: 'high' | 'medium' | 'low';
  related_stocks?: string[];
  url?: string;
}

export interface LimitUpStock {
  code: string;
  name: string;
  price: number;
  change_pct: number;
  limit_up_time?: string;
  seal_strength?: number; // 封板强度
  open_count?: number; // 打开次数
  volume?: number;
  turnover_rate?: number;
  concept_themes?: string[];
  reason?: string;
}

export interface DragonTigerItem {
  code: string;
  name: string;
  date: string;
  buy_amount: number;
  sell_amount: number;
  net_amount: number;
  change_pct: number;
  turnover_rate: number;
  institutions?: Array<{
    name: string;
    type: 'buy' | 'sell';
    amount: number;
    rank: number;
  }>;
  reason?: string;
}

export interface SentimentCycle {
  date: string;
  phase: 'accumulation' | 'uptrend' | 'distribution' | 'downtrend';
  sentiment_index: number; // 0-100
  money_effect: number; // 赚钱效应指数
  limit_up_count: number;
  limit_down_count: number;
  avg_turnover_rate: number;
  hot_money_activity: number;
  market_temperature: number; // 市场温度
  risk_warning?: string;
}

export interface AIAnalysisParams {
  date: string;
  provider?: string;
  analysis_type?: 'premarket' | 'intraday' | 'aftermarket';
  include_overseas?: boolean;
  include_news?: boolean;
  include_technical?: boolean;
}

/**
 * 获取盘前分析数据
 */
export function usePremarketAnalysis(date: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sentiment.premarket(date),
    queryFn: async () => {
      const response = await apiClient.get(`/api/sentiment/premarket/${date}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取盘前分析失败');
      }
      return response.data as PremarketAnalysis;
    },
    enabled,
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.HOUR, // 盘前数据缓存1小时
  });
}

/**
 * 获取隔夜数据
 */
export function useOvernightData(date: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sentiment.overnightData(date),
    queryFn: async () => {
      const response = await apiClient.get(`/api/sentiment/overnight/${date}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取隔夜数据失败');
      }
      return response.data as OvernightData;
    },
    enabled,
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.HOUR * 2, // 隔夜数据缓存2小时
  });
}

/**
 * 同步隔夜数据
 */
export function useSyncOvernightData() {
  return useMutation({
    mutationFn: async (date: string) => {
      const response = await apiClient.post('/api/sentiment/overnight/sync', { date });
      if (response.code !== 200) {
        throw new Error(response.message || '同步隔夜数据失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('隔夜数据同步成功');
    },
    onError: (error: Error) => {
      console.error('同步隔夜数据失败:', error);
      toast.error(error.message || '同步隔夜数据失败');
    },
  });
}

/**
 * 获取碰撞分析
 */
export function useCollisionAnalysis(date: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sentiment.collisionAnalysis(date),
    queryFn: async () => {
      const response = await apiClient.get(`/api/sentiment/collision/${date}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取碰撞分析失败');
      }
      return response.data as CollisionAnalysis;
    },
    enabled,
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.MINUTE * 30, // 碰撞分析缓存30分钟
  });
}

/**
 * 生成AI分析
 */
export function useGenerateAIAnalysis() {
  return useMutation({
    mutationFn: async (params: AIAnalysisParams) => {
      const response = await apiClient.post('/api/ai-strategy/generate-report', params);
      if (response.code !== 200) {
        throw new Error(response.message || '生成AI分析失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('AI分析生成成功');
    },
    onError: (error: Error) => {
      console.error('生成AI分析失败:', error);
      toast.error(error.message || '生成AI分析失败');
    },
  });
}

/**
 * 获取涨停池数据
 */
export function useLimitUpPool(date: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sentiment.limitUp(date),
    queryFn: async () => {
      const response = await apiClient.getLimitUpPool({ date });
      if (response.code !== 200) {
        throw new Error(response.message || '获取涨停池失败');
      }
      return response.data as {
        stocks: LimitUpStock[];
        total: number;
        stats: {
          total_limit_up: number;
          first_limit_up: number;
          continuous_limit_up: number;
          open_limit_up: number; // 开板数
        };
      };
    },
    enabled,
    ...getQueryConfig('LIST'),
    refetchInterval: QUERY_TIME.MINUTE * 5, // 交易时间每5分钟刷新
  });
}

/**
 * 获取龙虎榜数据
 */
export function useDragonTigerList(params?: {
  date?: string;
  stock_code?: string;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: queryKeys.sentiment.dragonTiger(params),
    queryFn: async () => {
      const response = await apiClient.getDragonTigerList(params);
      if (response.code !== 200) {
        throw new Error(response.message || '获取龙虎榜失败');
      }
      return response.data as {
        items: DragonTigerItem[];
        total: number;
      };
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.HOUR, // 龙虎榜数据缓存1小时
  });
}

/**
 * 获取情绪周期数据
 */
export function useSentimentCycle(params?: {
  start_date?: string;
  end_date?: string;
  period?: 'daily' | 'weekly' | 'monthly';
}) {
  return useQuery({
    queryKey: queryKeys.sentiment.cycle(),
    queryFn: async () => {
      const response = await apiClient.get('/api/sentiment/cycle', { params });
      if (response.code !== 200) {
        throw new Error(response.message || '获取情绪周期失败');
      }
      return response.data as {
        cycles: SentimentCycle[];
        current_phase: string;
        trend: 'up' | 'down' | 'sideways';
        risk_level: 'low' | 'medium' | 'high';
      };
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.MINUTE * 30,
  });
}

/**
 * 获取AI提供商列表
 */
export function useAIProviders() {
  return useQuery({
    queryKey: queryKeys.sentiment.aiProviders(),
    queryFn: async () => {
      const response = await apiClient.get('/api/ai-strategy/providers');
      if (response.code !== 200) {
        throw new Error(response.message || '获取AI提供商失败');
      }
      return response.data as Array<{
        id: string;
        name: string;
        model: string;
        is_active: boolean;
        capabilities: string[];
      }>;
    },
    ...getQueryConfig('STATIC'), // AI提供商列表较少变化
  });
}

/**
 * 获取盘前新闻列表
 */
export function usePremarketNews(date: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.sentiment.news(date),
    queryFn: async () => {
      const response = await apiClient.get(`/api/sentiment/news/${date}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取盘前新闻失败');
      }
      return response.data as PremarketNews[];
    },
    enabled,
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.MINUTE * 30,
  });
}

/**
 * 同步市场新闻
 */
export function useSyncMarketNews() {
  return useMutation({
    mutationFn: async (params: {
      date: string;
      sources?: string[];
      keywords?: string[];
    }) => {
      const response = await apiClient.post('/api/sentiment/news/sync', params);
      if (response.code !== 200) {
        throw new Error(response.message || '同步新闻失败');
      }
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`成功同步 ${data.count || 0} 条新闻`);
    },
    onError: (error: Error) => {
      console.error('同步新闻失败:', error);
      toast.error(error.message || '同步新闻失败');
    },
  });
}

/**
 * 获取历史分析记录
 */
export function useAnalysisHistory(date: string) {
  return useQuery({
    queryKey: queryKeys.sentiment.history(date),
    queryFn: async () => {
      const response = await apiClient.get(`/api/sentiment/history/${date}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取历史分析失败');
      }
      return response.data as Array<{
        id: string;
        date: string;
        type: string;
        generated_at: string;
        provider?: string;
        content?: any;
      }>;
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 计算赚钱效应
 */
export function useMoneyEffect(date?: string) {
  return useQuery({
    queryKey: [...queryKeys.sentiment.all, 'money-effect', date],
    queryFn: async () => {
      const response = await apiClient.get('/api/sentiment/money-effect', {
        params: { date }
      });
      if (response.code !== 200) {
        throw new Error(response.message || '计算赚钱效应失败');
      }
      return response.data as {
        date: string;
        money_effect_index: number; // 0-100
        yesterday_profit_ratio: number; // 昨日买入今日盈利比例
        limit_up_success_rate: number; // 打板成功率
        avg_amplitude: number; // 平均振幅
        strong_stocks_count: number; // 强势股数量
        weak_stocks_count: number; // 弱势股数量
      };
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.MINUTE * 10,
  });
}

/**
 * 获取游资动向
 */
export function useHotMoneyFlow(params?: {
  date?: string;
  institution?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: [...queryKeys.sentiment.all, 'hot-money', params],
    queryFn: async () => {
      const response = await apiClient.get('/api/sentiment/hot-money', { params });
      if (response.code !== 200) {
        throw new Error(response.message || '获取游资动向失败');
      }
      return response.data as {
        flows: Array<{
          institution: string;
          date: string;
          stock_code: string;
          stock_name: string;
          action: 'buy' | 'sell';
          amount: number;
          ranking: number;
        }>;
        top_institutions: Array<{
          name: string;
          total_amount: number;
          trade_count: number;
          win_rate: number;
        }>;
      };
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.HOUR,
  });
}