import React, { useState } from 'react';
import { Table, Button, Space, Typography } from 'antd';
import {
  EyeOutlined,
  EyeInvisibleOutlined,
} from '@ant-design/icons';
import ConclusionBadge from './ConclusionBadge';
import type {
  InspectionItemCheck,
  ClauseCheck,
} from '../types';

const { Text } = Typography;

interface InspectionItemTableProps {
  items: InspectionItemCheck[];
}

/**
 * 检验项目表格组件
 * 展示检验项目列表，支持展开查看标准条款详情
 */
const InspectionItemTable: React.FC<InspectionItemTableProps> = ({
  items,
}) => {
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([]);

  // 展开/折叠行
  const toggleExpand = (itemNumber: string) => {
    setExpandedRowKeys((prev) =>
      prev.includes(itemNumber)
        ? prev.filter((key) => key !== itemNumber)
        : [...prev, itemNumber]
    );
  };

  // 展开全部
  const expandAll = () => {
    setExpandedRowKeys(items.map((item) => item.item_number));
  };

  // 折叠全部
  const collapseAll = () => {
    setExpandedRowKeys([]);
  };

  // 表格列定义
  const columns = [
    {
      title: '序号',
      dataIndex: 'item_number',
      key: 'item_number',
      width: 80,
      align: 'center' as const,
    },
    {
      title: '检验项目',
      dataIndex: 'item_name',
      key: 'item_name',
      ellipsis: true,
    },
    {
      title: '标准条款数',
      key: 'clause_count',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, record: InspectionItemCheck) => record.clauses.length,
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, record: InspectionItemCheck) => {
        const errorCount = record.clauses.filter(
          (c) => !c.is_conclusion_correct
        ).length;
        return errorCount > 0 ? (
          <Text type="danger">{errorCount} 处错误</Text>
        ) : (
          <Text type="success">通过</Text>
        );
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      align: 'center' as const,
      render: (_: unknown, record: InspectionItemCheck) => (
        <Button
          type="link"
          size="small"
          icon={
            expandedRowKeys.includes(record.item_number) ? (
              <EyeInvisibleOutlined />
            ) : (
              <EyeOutlined />
            )
          }
          onClick={() => toggleExpand(record.item_number)}
        >
          {expandedRowKeys.includes(record.item_number) ? '折叠' : '详情'}
        </Button>
      ),
    },
  ];

  // 展开行内容渲染
  const expandedRowRender = (item: InspectionItemCheck) => {
    return (
      <div className="bg-gray-50 p-4 rounded">
        <Table
          dataSource={item.clauses}
          rowKey="clause_number"
          pagination={false}
          size="small"
          bordered
          columns={[
            {
              title: '标准条款',
              dataIndex: 'clause_number',
              key: 'clause_number',
              width: 120,
              align: 'center',
            },
            {
              title: '标准要求',
              key: 'requirements',
              render: (_: unknown, clause: ClauseCheck) => (
                <div className="space-y-2">
                  {clause.requirements.map((req, idx) => (
                    <div key={idx} className="text-sm">
                      <div>{req.requirement_text}</div>
                      <div className="text-gray-500 mt-1">
                        检验结果: {req.inspection_result || '-'}
                        {req.remark && (
                          <span className="ml-2 text-amber-600">
                            备注: {req.remark}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ),
            },
            {
              title: '单项结论',
              key: 'conclusion',
              width: 200,
              render: (_: unknown, clause: ClauseCheck) => (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Text type="secondary">实际:</Text>
                    <Text
                      className={
                        clause.is_conclusion_correct
                          ? 'text-green-600'
                          : 'text-red-600 line-through'
                      }
                    >
                      {clause.conclusion || '-'}
                    </Text>
                  </div>
                  {!clause.is_conclusion_correct && (
                    <div className="flex items-center gap-2">
                      <Text type="secondary">期望:</Text>
                      <Text className="text-green-600 font-medium">
                        {clause.expected_conclusion}
                      </Text>
                    </div>
                  )}
                  <div>
                    <ConclusionBadge isCorrect={clause.is_conclusion_correct} />
                  </div>
                </div>
              ),
            },
          ]}
        />
        {item.issues.length > 0 && (
          <div className="mt-3 p-3 bg-red-50 rounded border border-red-200">
            <Text type="danger" strong>
              问题:
            </Text>
            <ul className="list-disc list-inside mt-1">
              {item.issues.map((issue, idx) => (
                <li key={idx} className="text-red-600 text-sm">
                  {issue}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  };

  return (
    <div>
      {/* 工具栏 */}
      <div className="mb-4 flex justify-end">
        <Space>
          <Button size="small" onClick={expandAll}>
            展开全部
          </Button>
          <Button size="small" onClick={collapseAll}>
            折叠全部
          </Button>
        </Space>
      </div>

      {/* 表格 */}
      <Table
        dataSource={items}
        rowKey="item_number"
        columns={columns}
        pagination={false}
        expandable={{
          expandedRowRender,
          expandedRowKeys,
          onExpandedRowsChange: (keys) => setExpandedRowKeys(keys as string[]),
          expandIcon: () => null, // 隐藏默认展开图标，使用自定义操作列
        }}
        bordered
        size="middle"
      />
    </div>
  );
};

export default InspectionItemTable;
