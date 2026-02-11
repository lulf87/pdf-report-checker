import React, { useMemo } from 'react';
import { Empty, Badge } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useAppStore } from '../stores/appStore';
import {
  getStatusColor,
  getStatusBgColor,
  getStatusText,
  formatConfidence,
} from '../utils/format';
import type { FieldResult } from '../types';

const FieldList: React.FC = () => {
  const {
    currentResult,
    filter,
    searchQuery,
    selectedFieldId,
    selectField,
    openImagePreview,
  } = useAppStore();

  const filteredFields = useMemo(() => {
    if (!currentResult) return [];

    let fields = currentResult.fields;

    // Apply status filter
    if (filter !== 'all') {
      fields = fields.filter((f) => f.status === filter);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      fields = fields.filter(
        (f) =>
          f.fieldName.toLowerCase().includes(query) ||
          (f.tableValue?.toLowerCase() || '').includes(query) ||
          (f.ocrValue?.toLowerCase() || '').includes(query)
      );
    }

    return fields;
  }, [currentResult, filter, searchQuery]);

  const getStatusIcon = (status: FieldResult['status']) => {
    switch (status) {
      case 'matched':
        return <CheckCircleOutlined className="text-green-500" />;
      case 'mismatched':
        return <CloseCircleOutlined className="text-red-500" />;
      case 'missing':
        return <ExclamationCircleOutlined className="text-amber-500" />;
      case 'extra':
        return <InfoCircleOutlined className="text-gray-400" />;
    }
  };

  const highlightDifference = (text1: string | null, text2: string | null) => {
    if (!text1 || !text2 || text1 === text2) {
      return {
        text1: text1 || '-',
        text2: text2 || '-',
        hasDiff: text1 !== text2,
      };
    }

    // Simple diff highlighting
    return {
      text1: text1,
      text2: text2,
      hasDiff: true,
    };
  };

  if (!currentResult) {
    return (
      <div className="flex items-center justify-center h-64">
        <Empty description="暂无核对结果" />
      </div>
    );
  }

  if (filteredFields.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Empty description="没有匹配的结果" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {filteredFields.map((field) => {
        const isSelected = selectedFieldId === field.id;
        const diff = highlightDifference(field.tableValue, field.ocrValue);

        return (
          <div
            key={field.id}
            onClick={() => selectField(isSelected ? null : field.id)}
            className={`
              bg-white rounded-xl border transition-all duration-200 cursor-pointer
              ${isSelected ? 'border-primary shadow-md ring-1 ring-primary' : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'}
            `}
          >
            <div className="p-4">
              {/* Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {getStatusIcon(field.status)}
                  <span className="font-semibold text-gray-800">
                    {field.fieldName}
                  </span>
                  <Badge
                    count={getStatusText(field.status)}
                    style={{
                      backgroundColor: getStatusBgColor(field.status),
                      color: getStatusColor(field.status),
                      fontSize: '11px',
                      fontWeight: 500,
                    }}
                  />
                </div>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <span>置信度: {formatConfidence(field.confidence)}</span>
                  {field.imagePath && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openImagePreview(field.imagePath!);
                      }}
                      className="p-1.5 text-primary hover:bg-blue-50 rounded-lg transition-colors"
                      title="查看图片"
                    >
                      <EyeOutlined />
                    </button>
                  )}
                </div>
              </div>

              {/* Values Comparison */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">表格值</p>
                  <p
                    className={`font-medium ${
                      diff.hasDiff && field.status === 'mismatched'
                        ? 'text-red-600 bg-red-50 px-2 py-0.5 rounded inline-block'
                        : 'text-gray-800'
                    }`}
                  >
                    {diff.text1}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3">
                  <p className="text-xs text-gray-500 mb-1">OCR识别值</p>
                  <p
                    className={`font-medium ${
                      diff.hasDiff && field.status === 'mismatched'
                        ? 'text-red-600 bg-red-50 px-2 py-0.5 rounded inline-block'
                        : 'text-gray-800'
                    }`}
                  >
                    {diff.text2}
                  </p>
                </div>
              </div>

              {/* Location Info */}
              <div className="mt-3 flex items-center gap-4 text-sm text-gray-500">
                <span>第 {field.pageNumber} 页</span>
                {field.tableRow && <span>第 {field.tableRow} 行</span>}
                {field.tableCol && <span>列 {field.tableCol}</span>}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default FieldList;
