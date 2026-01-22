/**
 * 机器学习训练 Store
 * 使用 Zustand 管理状态
 */

import { create } from 'zustand';
import { format, subYears } from 'date-fns';

export interface MLTrainingConfig {
  symbol: string;
  start_date: string;
  end_date: string;
  model_type: 'lightgbm' | 'gru';
  target_period: number;
  train_ratio: number;
  valid_ratio: number;

  // 特征选择
  use_technical_indicators: boolean;
  use_alpha_factors: boolean;
  selected_features?: string[];

  // 数据处理
  scaler_type: 'standard' | 'robust' | 'minmax';
  balance_samples: boolean;
  balance_method: 'oversample' | 'undersample' | 'smote';

  // 模型参数
  model_params?: Record<string, any>;

  // GRU参数
  seq_length: number;
  batch_size: number;
  epochs: number;

  // LightGBM参数
  early_stopping_rounds: number;
}

export interface MLTrainingTask {
  task_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  created_at: string;
  started_at?: string;
  completed_at?: string;

  config: MLTrainingConfig;

  progress: number;
  current_step: string;

  metrics?: {
    rmse: number;
    r2: number;
    ic: number;
    rank_ic: number;
    [key: string]: number;
  };

  model_path?: string;
  feature_importance?: Record<string, number>;
  error_message?: string;
}

export interface MLModel {
  model_id: string;
  symbol: string;
  model_type: 'lightgbm' | 'gru';
  target_period: number;
  metrics: Record<string, number>;
  feature_importance?: Record<string, number>;
  model_path: string;
  trained_at: string;
  config: MLTrainingConfig;
}

export interface PredictionResult {
  date: string;
  prediction: number;
  actual: number;
}

interface MLStore {
  // 当前配置
  config: MLTrainingConfig;
  setConfig: (config: Partial<MLTrainingConfig>) => void;
  resetConfig: () => void;

  // 训练任务
  currentTask: MLTrainingTask | null;
  setCurrentTask: (task: MLTrainingTask | null) => void;

  tasks: MLTrainingTask[];
  setTasks: (tasks: MLTrainingTask[]) => void;

  // 模型列表
  models: MLModel[];
  setModels: (models: MLModel[]) => void;

  // 预测结果
  predictions: PredictionResult[];
  setPredictions: (predictions: PredictionResult[]) => void;

  // 选中的模型
  selectedModel: MLModel | null;
  setSelectedModel: (model: MLModel | null) => void;

  // UI 状态
  showConfig: boolean;
  setShowConfig: (show: boolean) => void;

  showTrainingMonitor: boolean;
  setShowTrainingMonitor: (show: boolean) => void;

  showFeatureImportance: boolean;
  setShowFeatureImportance: (show: boolean) => void;

  showPredictionChart: boolean;
  setShowPredictionChart: (show: boolean) => void;
}

// 计算默认日期：开始日期为5年前，结束日期为今天（与策略回测页面保持一致）
const getDefaultDates = () => {
  const today = new Date();
  const fiveYearsAgo = subYears(today, 5);

  return {
    start_date: format(fiveYearsAgo, 'yyyyMMdd'),
    end_date: format(today, 'yyyyMMdd'),
  };
};

const defaultConfig: MLTrainingConfig = {
  symbol: '000001',
  ...getDefaultDates(),
  model_type: 'lightgbm',
  target_period: 5,
  train_ratio: 0.7,
  valid_ratio: 0.15,

  use_technical_indicators: true,
  use_alpha_factors: true,

  scaler_type: 'robust',
  balance_samples: false,
  balance_method: 'undersample',

  seq_length: 20,
  batch_size: 64,
  epochs: 100,

  early_stopping_rounds: 50,
};

export const useMLStore = create<MLStore>((set) => ({
  // 配置
  config: defaultConfig,
  setConfig: (newConfig) =>
    set((state) => ({
      config: { ...state.config, ...newConfig },
    })),
  resetConfig: () => set({ config: defaultConfig }),

  // 训练任务
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),

  tasks: [],
  setTasks: (tasks) => set({ tasks }),

  // 模型
  models: [],
  setModels: (models) => set({ models }),

  // 预测
  predictions: [],
  setPredictions: (predictions) => set({ predictions }),

  selectedModel: null,
  setSelectedModel: (model) => set({ selectedModel: model }),

  // UI
  showConfig: true,
  setShowConfig: (show) => set({ showConfig: show }),

  showTrainingMonitor: false,
  setShowTrainingMonitor: (show) => set({ showTrainingMonitor: show }),

  showFeatureImportance: false,
  setShowFeatureImportance: (show) => set({ showFeatureImportance: show }),

  showPredictionChart: false,
  setShowPredictionChart: (show) => set({ showPredictionChart: show }),
}));
