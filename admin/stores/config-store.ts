/**
 * 系统配置Store (Zustand)
 * 用于缓存数据源配置,避免重复请求
 */

import { create } from 'zustand';
import { apiClient } from '@/lib/api-client';

export interface DataSourceConfig {
  data_source: string;
  minute_data_source: string;
  realtime_data_source: string;
  tushare_token: string;
}

interface ConfigState {
  dataSource: DataSourceConfig | null;
  isLoading: boolean;
  error: string | null;
  lastFetchTime: number | null;
}

interface ConfigActions {
  fetchDataSourceConfig: (forceRefresh?: boolean) => Promise<void>;
  updateDataSourceConfig: (config: Partial<DataSourceConfig>) => void;
  clearConfig: () => void;
}

export type ConfigStore = ConfigState & ConfigActions;

// 缓存有效期: 5分钟
const CACHE_DURATION = 5 * 60 * 1000;

export const useConfigStore = create<ConfigStore>((set, get) => ({
  // 状态
  dataSource: null,
  isLoading: false,
  error: null,
  lastFetchTime: null,

  // 获取数据源配置
  fetchDataSourceConfig: async (forceRefresh = false) => {
    const { dataSource, lastFetchTime, isLoading } = get();

    // 如果正在加载,直接返回
    if (isLoading) {
      return;
    }

    // 如果有缓存且未过期,且不是强制刷新,直接返回
    if (!forceRefresh && dataSource && lastFetchTime) {
      const now = Date.now();
      if (now - lastFetchTime < CACHE_DURATION) {
        return;
      }
    }

    set({ isLoading: true, error: null });

    try {
      const response = await apiClient.getDataSourceConfig();

      if (response.data) {
        set({
          dataSource: response.data,
          isLoading: false,
          error: null,
          lastFetchTime: Date.now(),
        });
      } else {
        throw new Error('获取配置失败');
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || '加载配置失败';
      set({
        isLoading: false,
        error: errorMessage,
      });
      console.error('Failed to fetch data source config:', error);
      throw error;
    }
  },

  // 更新本地缓存的配置(不调用API)
  updateDataSourceConfig: (config: Partial<DataSourceConfig>) => {
    const { dataSource } = get();
    if (dataSource) {
      set({
        dataSource: { ...dataSource, ...config },
        lastFetchTime: Date.now(),
      });
    }
  },

  // 清除配置缓存
  clearConfig: () => {
    set({
      dataSource: null,
      isLoading: false,
      error: null,
      lastFetchTime: null,
    });
  },
}));
