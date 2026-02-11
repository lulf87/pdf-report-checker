import React from 'react';
import type { VerificationStats } from '../types';

interface StatsCardProps {
  stats: VerificationStats;
}

const StatsCard: React.FC<StatsCardProps> = ({ stats }) => {
  const items = [
    {
      label: '总字段数',
      value: stats.totalFields,
      color: '#3B82F6',
      bgColor: '#EFF6FF',
    },
    {
      label: '一致',
      value: stats.matched,
      color: '#10B981',
      bgColor: '#D1FAE5',
    },
    {
      label: '不一致',
      value: stats.mismatched,
      color: '#EF4444',
      bgColor: '#FEE2E2',
    },
    {
      label: '缺失',
      value: stats.missing,
      color: '#F59E0B',
      bgColor: '#FEF3C7',
    },
    {
      label: '整体置信度',
      value: `${(stats.confidence * 100).toFixed(1)}%`,
      color: '#8B5CF6',
      bgColor: '#EDE9FE',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      {items.map((item) => (
        <div
          key={item.label}
          className="bg-white rounded-xl p-4 border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-200"
        >
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center mb-3"
            style={{ backgroundColor: item.bgColor }}
          >
            <span
              className="text-lg font-bold"
              style={{ color: item.color }}
            >
              {typeof item.value === 'number' && item.value > 99
                ? '99+'
                : item.value.toString().charAt(0)}
            </span>
          </div>
          <p className="text-2xl font-bold text-gray-800 mb-1">
            {item.value}
          </p>
          <p className="text-sm text-gray-500">{item.label}</p>
        </div>
      ))}
    </div>
  );
};

export default StatsCard;
