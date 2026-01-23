/**
 * 训练历史曲线可视化
 * 用于显示GRU等深度学习模型的训练/验证损失曲线
 */

'use client';

import { useEffect, useRef } from 'react';
import { useMLStore } from '@/store/mlStore';
import * as echarts from 'echarts';

export default function TrainingHistory() {
  const { currentTask } = useMLStore();
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current || !currentTask?.training_history) return;

    // 初始化图表
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // 准备数据
    const history = currentTask.training_history;
    const epochs = Array.from({ length: history.train_loss.length }, (_, i) => i + 1);

    const option: echarts.EChartsOption = {
      title: {
        text: '训练历史曲线',
        textStyle: {
          fontSize: 14,
          fontWeight: 'bold',
        },
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
        },
      },
      legend: {
        data: ['训练损失', '验证损失'],
        top: 30,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 60,
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: epochs,
        name: 'Epoch',
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        name: 'Loss',
        scale: true,
      },
      series: [
        {
          name: '训练损失',
          type: 'line' as const,
          data: history.train_loss,
          smooth: true,
          itemStyle: {
            color: '#4F46E5',
          },
          lineStyle: {
            width: 2,
          },
        },
        ...(history.valid_loss && history.valid_loss.length > 0
          ? [
              {
                name: '验证损失',
                type: 'line' as const,
                data: history.valid_loss,
                smooth: true,
                itemStyle: {
                  color: '#F59E0B',
                },
                lineStyle: {
                  width: 2,
                },
              },
            ]
          : []),
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
  }, [currentTask?.training_history]);

  if (!currentTask?.training_history) return null;

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div ref={chartRef} style={{ width: '100%', height: '400px' }} />
    </div>
  );
}
