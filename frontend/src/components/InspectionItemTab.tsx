import React, { useState, useMemo } from 'react';
import {
  Card,
  Button,
  Space,
  Segmented,
  Alert,
  Empty,
  Badge,
} from 'antd';
import {
  DownloadOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import InspectionItemStats from './InspectionItemStats';
import InspectionItemTable from './InspectionItemTable';
import type {
  InspectionItemCheckResult,
  InspectionItemCheck,
} from '../types';
import { exportInspectionItemsToExcel } from '../utils/export';

type FilterType = 'all' | 'correct' | 'incorrect';

interface InspectionItemTabProps {
  data: InspectionItemCheckResult | null | undefined;
}

/**
 * 检验项目核对页签组件
 * 整合统计卡片、筛选功能、表格展示、导出功能
 */
const InspectionItemTab: React.FC<InspectionItemTabProps> = ({ data }) => {
  const [filter, setFilter] = useState<FilterType>('all');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  // 根据筛选条件过滤项目
  const filteredItems = useMemo(() => {
    if (!data?.item_checks) return [];

    switch (filter) {
      case 'correct':
        return data.item_checks.filter((item) => item.status === 'pass');
      case 'incorrect':
        return data.item_checks.filter(
          (item) => item.status === 'fail' || item.status === 'warning'
        );
      default:
        return data.item_checks;
    }
  }, [data, filter]);

  // 展开全部
  const expandAll = () => {
    if (filteredItems.length > 0) {
      setExpandedItems(new Set(filteredItems.map((item) => item.item_number)));
    }
  };

  // 折叠全部
  const collapseAll = () => {
    setExpandedItems(new Set());
  };

  // 导出检验项目核对明细
  const handleExport = () => {
    if (!data) return;
    exportInspectionItemsToExcel(data, `report_${new Date().toISOString().slice(0, 10)}`);
  };

  // 如果没有数据
  if (!data || !data.has_table) {
    return (
      <Empty
        description="未检测到检验项目表格"
        image={Empty.PRESENTED_IMAGE_SIMPLE}
      />
    );
  }

  // 筛选选项
  const filterOptions = [
    {
      label: (
        <div className="flex items-center gap-1">
          <span>全部</span>
          <Badge count={data.total_items} style={{ backgroundColor: '#3B82F6' }} />
        </div>
      ),
      value: 'all' as FilterType,
    },
    {
      label: (
        <div className="flex items-center gap-1">
          <span>仅正确</span>
          <Badge
            count={data.correct_conclusions}
            style={{ backgroundColor: '#10B981' }}
          />
        </div>
      ),
      value: 'correct' as FilterType,
    },
    {
      label: (
        <div className="flex items-center gap-1">
          <span>仅错误</span>
          <Badge
            count={data.incorrect_conclusions}
            style={{ backgroundColor: '#EF4444' }}
          />
        </div>
      ),
      value: 'incorrect' as FilterType,
    },
  ];

  return (
    <div className="space-y-4">
      {/* 统计卡片 */}
      <InspectionItemStats data={data} />

      {/* 跨页续表提示 */}
      {data.cross_page_continuations > 0 && (
        <Alert
          message={`检测到 ${data.cross_page_continuations} 处跨页续表`}
          description="系统已自动合并跨页表格数据"
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
        />
      )}

      {/* 错误汇总 */}
      {data.errors.length > 0 && (
        <Alert
          message={`发现 ${data.errors.length} 处错误`}
          description={
            <ul className="list-disc list-inside mt-2">
              {data.errors.slice(0, 5).map((error, index) => (
                <li key={index}>
                  {error.item_number && `序号 ${error.item_number}: `}
                  {error.message}
                </li>
              ))}
              {data.errors.length > 5 && (
                <li>...还有 {data.errors.length - 5} 项错误</li>
              )}
            </ul>
          }
          type="error"
          showIcon
        />
      )}

      {/* 工具栏 */}
      <Card className="shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <Space>
            <Segmented
              value={filter}
              onChange={(value) => setFilter(value as FilterType)}
              options={filterOptions}
              className="bg-gray-100"
            />
          </Space>

          <Space>
            <Button
              icon={<EyeOutlined />}
              onClick={expandAll}
              disabled={filteredItems.length === 0}
            >
              展开全部
            </Button>
            <Button
              icon={<EyeInvisibleOutlined />}
              onClick={collapseAll}
              disabled={filteredItems.length === 0}
            >
              折叠全部
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={handleExport}
            >
              导出明细
            </Button>
          </Space>
        </div>
      </Card>

      {/* 检验项目表格 */}
      <InspectionItemTable items={filteredItems} />
    </div>
  );
};

export default InspectionItemTab;
