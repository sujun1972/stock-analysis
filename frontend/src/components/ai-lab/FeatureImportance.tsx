/**
 * 特征重要性可视化
 * 使用柱状图显示模型的特征重要性排名
 */

'use client';

import { useEffect, useRef } from 'react';
import { useMLStore } from '@/store/mlStore';
import * as echarts from 'echarts';

export default function FeatureImportance() {
  const { currentTask } = useMLStore();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || !currentTask?.feature_importance) return;

    // 初始化图表
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // 准备数据
    const importance = currentTask.feature_importance;
    const data = Object.entries(importance)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20); // Top 20

    const option: echarts.EChartsOption = {
      title: {
        text: '特征重要性 Top 20',
        textStyle: {
          fontSize: 14,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: 'Gain',
      },
      yAxis: {
        type: 'category',
        data: data.map((d) => d[0]),
        inverse: true,
        axisLabel: {
          fontSize: 11,
        },
      },
      series: [
        {
          name: 'Importance',
          type: 'bar',
          data: data.map((d) => d[1]),
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: '#4F46E5' },
              { offset: 1, color: '#818CF8' },
            ]),
          },
          label: {
            show: true,
            position: 'right',
            formatter: '{c}',
            fontSize: 10,
          },
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
  }, [currentTask?.feature_importance]);

  if (!currentTask?.feature_importance) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div ref={chartRef} style={{ width: '100%', height: '500px' }} />
    </div>
  );
}
