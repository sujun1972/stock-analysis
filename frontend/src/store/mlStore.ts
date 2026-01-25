import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
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
  training_history?: {
    train_loss: number[];
    valid_loss: number[];
  };
  error_message?: string;
}

export interface MLModel {
  id: number;
  model_id: string;
  symbol: string;
  model_type: 'lightgbm' | 'gru';
  target_period: number;
  metrics?: Record<string, number>;
  feature_importance?: Record<string, number>;
  model_path: string;
  trained_at: string;
  config: MLTrainingConfig;
  source: 'auto_experiment' | 'manual_training';
  has_metrics: boolean;

  backtest_metrics?: {
    rank_score?: number | null;
    annual_return?: number | null;
    sharpe_ratio?: number | null;
    max_drawdown?: number | null;
    win_rate?: number | null;
    calmar_ratio?: number | null;
  };
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

export const useMLStore = create<MLStore>()(
  devtools(
    persist(
      (set) => ({
        config: defaultConfig,
        setConfig: (newConfig) =>
          set((state) => ({
            config: { ...state.config, ...newConfig },
          }), false, 'mlStore/setConfig'),
        resetConfig: () => set({ config: defaultConfig }, false, 'mlStore/resetConfig'),

        currentTask: null,
        setCurrentTask: (task) => set({ currentTask: task }, false, 'mlStore/setCurrentTask'),

        tasks: [],
        setTasks: (tasks) => set({ tasks }, false, 'mlStore/setTasks'),

        models: [],
        setModels: (models) => set({ models }, false, 'mlStore/setModels'),

        predictions: [],
        setPredictions: (predictions) => set({ predictions }, false, 'mlStore/setPredictions'),

        selectedModel: null,
        setSelectedModel: (model) => set({ selectedModel: model }, false, 'mlStore/setSelectedModel'),

        showConfig: true,
        setShowConfig: (show) => set({ showConfig: show }, false, 'mlStore/setShowConfig'),

        showTrainingMonitor: false,
        setShowTrainingMonitor: (show) => set({ showTrainingMonitor: show }, false, 'mlStore/setShowTrainingMonitor'),

        showFeatureImportance: false,
        setShowFeatureImportance: (show) => set({ showFeatureImportance: show }, false, 'mlStore/setShowFeatureImportance'),

        showPredictionChart: false,
        setShowPredictionChart: (show) => set({ showPredictionChart: show }, false, 'mlStore/setShowPredictionChart'),
      }),
      {
        name: 'ml-storage',
        partialize: (state) => ({
          config: state.config,
          selectedModel: state.selectedModel,
        }),
      }
    ),
    { name: 'MLStore' }
  )
);
