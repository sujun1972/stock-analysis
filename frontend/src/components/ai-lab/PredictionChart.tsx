/**
 * 预测值 VS 实际值对齐图
 * 在 K 线图下方显示模型预测曲线，红色=上涨预测，蓝色=下跌预测
 */

'use client';

import { useEffect, useRef } from 'react';
import { useMLStore } from '@/stores/ml-store';
import * as echarts from 'echarts';
import { useEChartsTheme } from '@/hooks/useEChartsTheme';

export default function PredictionChart() {
  const { predictions, selectedModel } = useMLStore();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const { theme, echartsTheme } = useEChartsTheme();

  // 主题切换：dispose 旧 instance，让下一轮 effect 以新主题重新 init
  useEffect(() => {
    if (chartInstance.current) {
      chartInstance.current.dispose();
      chartInstance.current = null;
    }
  }, [theme]);

  useEffect(() => {
    if (!chartRef.current || !predictions || predictions.length === 0) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current, echartsTheme);
    }

    // 数据下采样：如果数据点超过 500，进行下采样
    const downsample = (data: any[], maxPoints: number) => {
      if (data.length <= maxPoints) return data;
      const step = Math.ceil(data.length / maxPoints);
      return data.filter((_, i) => i % step === 0);
    };

    const sampledData = downsample(predictions, 500);

    // 准备数据
    const dates = sampledData.map((d) => d.date);
    const actualValues = sampledData.map((d) => d.actual);
    const predictedValues = sampledData.map((d) => d.prediction);

    // 将预测值按涨跌分离，用于不同颜色渲染
    const upPredictions = predictedValues.map((val, idx) =>
      val > 0 ? val : null
    );
    const downPredictions = predictedValues.map((val, idx) =>
      val <= 0 ? val : null
    );

    const option: echarts.EChartsOption = {
      title: {
        text: '预测值 VS 实际值对齐图',
        subtext: selectedModel ? `模型: ${selectedModel.model_type} | 目标周期: ${selectedModel.target_period}天` : '',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
        formatter: (params: any) => {
          const dataIndex = params[0].dataIndex;
          const date = dates[dataIndex];
          const actual = actualValues[dataIndex];
          const predicted = predictedValues[dataIndex];

          return `
            <div style="font-size: 12px;">
              <div style="font-weight: bold; margin-bottom: 4px;">${date}</div>
              <div style="color: #666;">
                实际收益率: <span style="font-weight: bold; color: ${actual > 0 ? '#ef4444' : '#3b82f6'}">${actual?.toFixed(2)}%</span>
              </div>
              <div style="color: #666;">
                预测收益率: <span style="font-weight: bold; color: ${predicted > 0 ? '#f87171' : '#60a5fa'}">${predicted?.toFixed(2)}%</span>
              </div>
              <div style="color: #999; margin-top: 4px; font-size: 11px;">
                预测方向: ${predicted > 0 ? '↑ 上涨' : '↓ 下跌'}
              </div>
            </div>
          `;
        },
      },
      legend: {
        data: ['实际收益率', '预测上涨', '预测下跌'],
        top: 35,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '10%',
        top: '15%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: {
          fontSize: 11,
          rotate: 45,
          formatter: (value: string) => {
            // 简化日期显示
            return value.replace(/(\d{4})(\d{2})(\d{2})/, '$2-$3');
          },
        },
      },
      yAxis: {
        type: 'value',
        name: '收益率 (%)',
        axisLabel: {
          formatter: '{value}%',
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
          },
        },
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
        },
        {
          type: 'slider',
          start: 0,
          end: 100,
          height: 20,
          bottom: '5%',
        },
      ],
      series: [
        // 实际收益率
        {
          name: '实际收益率',
          type: 'line',
          data: actualValues,
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#9ca3af',
          },
          itemStyle: {
            color: '#9ca3af',
          },
          symbol: 'circle',
          symbolSize: 4,
          emphasis: {
            focus: 'series',
          },
        },
        // 预测上涨（红色）
        {
          name: '预测上涨',
          type: 'line',
          data: upPredictions,
          smooth: true,
          lineStyle: {
            width: 3,
            color: '#ef4444',
          },
          itemStyle: {
            color: '#ef4444',
          },
          symbol: 'circle',
          symbolSize: 6,
          emphasis: {
            focus: 'series',
          },
          connectNulls: false,
        },
        // 预测下跌（蓝色）
        {
          name: '预测下跌',
          type: 'line',
          data: downPredictions,
          smooth: true,
          lineStyle: {
            width: 3,
            color: '#3b82f6',
          },
          itemStyle: {
            color: '#3b82f6',
          },
          symbol: 'circle',
          symbolSize: 6,
          emphasis: {
            focus: 'series',
          },
          connectNulls: false,
        },
      ],
    };

    chartInstance.current.setOption(option);

    // 响应式
    const handleResize = () => {
      chartInstance.current?.resize();
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [predictions, selectedModel, theme, echartsTheme]);

  // 清理图表实例
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
        chartInstance.current = null;
      }
    };
  }, []);

  if (!predictions || predictions.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="text-center text-gray-500 dark:text-gray-400">
          暂无预测数据，请先选择模型并运行预测
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 min-w-0 max-w-full overflow-hidden">
      <div ref={chartRef} className="min-w-0 max-w-full" style={{ width: '100%', height: '450px' }} />

      {/* 图表说明 */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="grid grid-cols-3 gap-4 text-xs text-gray-600 dark:text-gray-400">
          <div>
            <span className="inline-block w-3 h-3 bg-gray-400 rounded-full mr-2"></span>
            灰色线：实际收益率（历史数据）
          </div>
          <div>
            <span className="inline-block w-3 h-3 bg-red-500 rounded-full mr-2"></span>
            红色线：预测上涨（预测值 &gt; 0）
          </div>
          <div>
            <span className="inline-block w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
            蓝色线：预测下跌（预测值 ≤ 0）
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500 dark:text-gray-500">
          💡 提示：使用鼠标滚轮缩放，拖动滑块查看不同时间段。点击图例可隐藏/显示对应曲线。
        </div>
      </div>
    </div>
  );
}
