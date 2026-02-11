import React from 'react';
import { Progress, Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { useAppStore } from '../stores/appStore';

const ProgressBar: React.FC = () => {
  const { isProcessing, progress } = useAppStore();

  if (!isProcessing) return null;

  const getStatusText = () => {
    if (progress < 20) return '正在解析文件...';
    if (progress < 50) return '正在进行OCR识别...';
    if (progress < 80) return '正在核对数据...';
    if (progress < 100) return '正在生成报告...';
    return '处理完成!';
  };

  return (
    <div className="bg-white rounded-xl p-6 border border-gray-200 shadow-sm">
      <div className="flex items-center gap-4 mb-4">
        <Spin indicator={<LoadingOutlined className="text-2xl text-primary" spin />} />
        <div>
          <h3 className="font-semibold text-gray-800">正在处理文件</h3>
          <p className="text-sm text-gray-500">{getStatusText()}</p>
        </div>
      </div>

      <Progress
        percent={progress}
        status="active"
        strokeColor={{
          '0%': '#3B82F6',
          '100%': '#10B981',
        }}
        strokeWidth={8}
        showInfo={true}
      />

      <div className="mt-3 flex justify-between text-sm text-gray-500">
        <span>预计剩余时间: {Math.ceil((100 - progress) / 10)} 秒</span>
        <span>{progress}%</span>
      </div>
    </div>
  );
};

export default ProgressBar;
