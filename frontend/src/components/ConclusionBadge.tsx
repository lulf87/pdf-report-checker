import React from 'react';
import { Badge, Tag } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
} from '@ant-design/icons';

interface ConclusionBadgeProps {
  isCorrect: boolean;
  showText?: boolean;
  size?: 'small' | 'default';
}

/**
 * 单项结论核对状态标记组件
 * 显示 ✅ 正确 或 ❌ 错误
 */
const ConclusionBadge: React.FC<ConclusionBadgeProps> = ({
  isCorrect,
  showText = true,
  size = 'default',
}) => {
  if (showText) {
    return isCorrect ? (
      <Badge
        status="success"
        text={
          <span className="text-green-600 font-medium">
            <CheckCircleOutlined className="mr-1" />
            正确
          </span>
        }
      />
    ) : (
      <Badge
        status="error"
        text={
          <span className="text-red-600 font-medium">
            <CloseCircleOutlined className="mr-1" />
            错误
          </span>
        }
      />
    );
  }

  // 仅显示图标模式
  return isCorrect ? (
    <Tag
      color="success"
      icon={<CheckCircleOutlined />}
      className={size === 'small' ? 'text-xs' : ''}
    >
      {showText && '正确'}
    </Tag>
  ) : (
    <Tag
      color="error"
      icon={<CloseCircleOutlined />}
      className={size === 'small' ? 'text-xs' : ''}
    >
      {showText && '错误'}
    </Tag>
  );
};

export default ConclusionBadge;
