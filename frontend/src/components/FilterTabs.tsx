import React from 'react';
import { Segmented, Badge } from 'antd';
import { useAppStore } from '../stores/appStore';
import type { FilterType, VerificationResult } from '../types';

interface FilterTabsProps {
  result: VerificationResult | null;
}

const FilterTabs: React.FC<FilterTabsProps> = ({ result }) => {
  const { filter, setFilter } = useAppStore();

  const getCounts = () => {
    if (!result) {
      return { all: 0, matched: 0, mismatched: 0, missing: 0, extra: 0 };
    }

    const fields = result.fields;
    return {
      all: fields.length,
      matched: fields.filter((f) => f.status === 'matched').length,
      mismatched: fields.filter((f) => f.status === 'mismatched').length,
      missing: fields.filter((f) => f.status === 'missing').length,
      extra: fields.filter((f) => f.status === 'extra').length,
    };
  };

  const counts = getCounts();

  const options = [
    {
      label: (
        <div className="flex items-center gap-1">
          <span>全部</span>
          <Badge count={counts.all} style={{ backgroundColor: '#3B82F6' }} />
        </div>
      ),
      value: 'all' as FilterType,
    },
    {
      label: (
        <div className="flex items-center gap-1">
          <span>一致</span>
          <Badge count={counts.matched} style={{ backgroundColor: '#10B981' }} />
        </div>
      ),
      value: 'matched' as FilterType,
    },
    {
      label: (
        <div className="flex items-center gap-1">
          <span>不一致</span>
          <Badge count={counts.mismatched} style={{ backgroundColor: '#EF4444' }} />
        </div>
      ),
      value: 'mismatched' as FilterType,
    },
    {
      label: (
        <div className="flex items-center gap-1">
          <span>缺失</span>
          <Badge count={counts.missing} style={{ backgroundColor: '#F59E0B' }} />
        </div>
      ),
      value: 'missing' as FilterType,
    },
  ];

  return (
    <Segmented
      value={filter}
      onChange={(value) => setFilter(value as FilterType)}
      options={options}
      className="bg-gray-100"
    />
  );
};

export default FilterTabs;
