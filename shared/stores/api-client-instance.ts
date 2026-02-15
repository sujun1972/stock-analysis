/**
 * API客户端实例
 * 从window对象获取项目特定的apiClient实例
 * - Admin项目: 在 admin/stores/auth-store.ts 中设置
 * - Frontend项目: 在 frontend/src/stores/auth-store.ts 中设置
 */

import axios from 'axios';

// 获取项目特定的API客户端实例
const getApiClient = () => {
  if (typeof window !== 'undefined' && (window as any).__apiClientInstance) {
    return (window as any).__apiClientInstance;
  }

  // 降级：返回默认axios实例
  console.warn('No API client instance found, using default axios instance');
  return axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
    headers: {
      'Content-Type': 'application/json',
    },
  });
};

export const apiClient = getApiClient();

// 导出类型
export type { AxiosInstance } from 'axios';
