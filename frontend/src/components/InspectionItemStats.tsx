import React from 'react';
import { Card, Statistic, Row, Col, Space } from 'antd';
import {
  FileTextOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  TableOutlined,
} from '@ant-design/icons';
import type { InspectionItemCheckResult } from '../types';

interface InspectionItemStatsProps {
  data: InspectionItemCheckResult;
}

/**
 * 检验项目核对统计卡片组件
 * 展示检验项目数、标准条款数、正确/错误结论数、跨页续表数
 */
const InspectionItemStats: React.FC<InspectionItemStatsProps> = ({ data }) => {
  const stats = [
    {
      title: '检验项目数',
      value: data.total_items,
      icon: <FileTextOutlined className="text-blue-500" />,
      valueStyle: { color: '#3B82F6' },
    },
    {
      title: '标准条款数',
      value: data.total_clauses,
      icon: <InfoCircleOutlined className="text-gray-500" />,
      valueStyle: { color: '#6B7280' },
    },
    {
      title: '结论正确',
      value: data.correct_conclusions,
      icon: <CheckCircleOutlined className="text-green-500" />,
      valueStyle: { color: '#10B981' },
    },
    {
      title: '结论错误',
      value: data.incorrect_conclusions,
      icon: <CloseCircleOutlined className="text-red-500" />,
      valueStyle: { color: '#EF4444' },
    },
  ];

  return (
    <Card className="shadow-sm">
      <Row gutter={[16, 16]}>
        {stats.map((stat, index) => (
          <Col xs={12} sm={6} key={index}>
            <Statistic
              title={
                <Space>
                  {stat.icon}
                  <span>{stat.title}</span>
                </Space>
              }
              value={stat.value}
              valueStyle={stat.valueStyle}
            />
          </Col>
        ))}
      </Row>
      {data.cross_page_continuations > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <Space>
            <TableOutlined className="text-amber-500" />
            <span className="text-amber-600">
              检测到 {data.cross_page_continuations} 处跨页续表，已自动合并
            </span>
          </Space>
        </div>
      )}
    </Card>
  );
};

export default InspectionItemStats;
