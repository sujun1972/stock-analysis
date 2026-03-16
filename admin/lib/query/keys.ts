/**
 * React Query Keys 管理
 * 统一管理所有 Query Keys，确保类型安全和一致性
 */

// 用户管理相关
export const userKeys = {
  all: ['users'] as const,
  lists: () => [...userKeys.all, 'list'] as const,
  list: (params?: any) => [...userKeys.lists(), params] as const,
  details: () => [...userKeys.all, 'detail'] as const,
  detail: (id: string) => [...userKeys.details(), id] as const,
  quota: (id: string) => [...userKeys.all, 'quota', id] as const,
} as const;

// 系统设置相关
export const systemKeys = {
  all: ['system'] as const,
  settings: () => [...systemKeys.all, 'settings'] as const,
  health: () => [...systemKeys.all, 'health'] as const,
  config: () => [...systemKeys.all, 'config'] as const,
} as const;

// 数据同步相关
export const syncKeys = {
  all: ['sync'] as const,
  stockList: () => [...syncKeys.all, 'stock-list'] as const,
  stockListStatus: () => [...syncKeys.all, 'stock-list-status'] as const,
  dailyData: (params?: any) => [...syncKeys.all, 'daily-data', params] as const,
  dailyDataStatus: () => [...syncKeys.all, 'daily-data-status'] as const,
  delistedStocks: () => [...syncKeys.all, 'delisted'] as const,
  newStocks: () => [...syncKeys.all, 'new'] as const,
  realtimeData: () => [...syncKeys.all, 'realtime'] as const,
  minuteData: (params?: any) => [...syncKeys.all, 'minute-data', params] as const,
} as const;

// 市场情绪相关
export const sentimentKeys = {
  all: ['sentiment'] as const,
  premarket: (date: string) => [...sentimentKeys.all, 'premarket', date] as const,
  overnightData: (date: string) => [...sentimentKeys.all, 'overnight', date] as const,
  collisionAnalysis: (date: string) => [...sentimentKeys.all, 'collision', date] as const,
  limitUp: (date: string) => [...sentimentKeys.all, 'limit-up', date] as const,
  dragonTiger: (params?: any) => [...sentimentKeys.all, 'dragon-tiger', params] as const,
  cycle: () => [...sentimentKeys.all, 'cycle'] as const,
  aiAnalysis: (date: string) => [...sentimentKeys.all, 'ai-analysis', date] as const,
  aiProviders: () => [...sentimentKeys.all, 'ai-providers'] as const,
  news: (date: string) => [...sentimentKeys.all, 'news', date] as const,
  history: (date: string) => [...sentimentKeys.all, 'history', date] as const,
  tasks: {
    active: () => [...sentimentKeys.all, 'tasks', 'active'] as const,
  },
} as const;

// 通知渠道相关
export const notificationKeys = {
  all: ['notifications'] as const,
  channels: () => [...notificationKeys.all, 'channels'] as const,
  channel: (type: string) => [...notificationKeys.all, 'channel', type] as const,
  scheduledTasks: () => [...notificationKeys.all, 'scheduled-tasks'] as const,
  scheduledTask: (id: string) => [...notificationKeys.all, 'scheduled-task', id] as const,
} as const;

// 监控相关
export const monitorKeys = {
  all: ['monitor'] as const,
  health: () => [...monitorKeys.all, 'health'] as const,
  activeTasks: () => [...monitorKeys.all, 'active-tasks'] as const,
  metrics: () => [...monitorKeys.all, 'metrics'] as const,
} as const;

// 股票相关（扩展已有的）
export const stockKeys = {
  all: ['stocks'] as const,
  lists: () => [...stockKeys.all, 'list'] as const,
  list: (params?: any) => [...stockKeys.lists(), params] as const,
  details: () => [...stockKeys.all, 'detail'] as const,
  detail: (code: string) => [...stockKeys.details(), code] as const,
  concepts: (code: string) => [...stockKeys.all, 'concepts', code] as const,
  search: (keyword: string) => [...stockKeys.all, 'search', keyword] as const,
  industries: () => [...stockKeys.all, 'industries'] as const,
  markets: () => [...stockKeys.all, 'markets'] as const,
} as const;

// 策略相关（扩展已有的）
export const strategyKeys = {
  all: ['strategies'] as const,
  lists: () => [...strategyKeys.all, 'list'] as const,
  list: (params?: any) => [...strategyKeys.lists(), params] as const,
  details: () => [...strategyKeys.all, 'detail'] as const,
  detail: (id: number) => [...strategyKeys.details(), id] as const,
  statistics: (id: number) => [...strategyKeys.all, 'statistics', id] as const,
  types: () => [...strategyKeys.all, 'types'] as const,
  validation: (code: string) => [...strategyKeys.all, 'validation', code] as const,
} as const;

// 导出统一的 queryKeys 对象
export const queryKeys = {
  users: userKeys,
  system: systemKeys,
  sync: syncKeys,
  sentiment: sentimentKeys,
  notifications: notificationKeys,
  monitor: monitorKeys,
  stocks: stockKeys,
  strategies: strategyKeys,
} as const;

// 类型导出
export type QueryKeys = typeof queryKeys;