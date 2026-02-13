/**
 * CheckListPanel 使用示例
 * 展示如何使用 CheckListPanel、CheckGroupCard 和 CheckItemCard 组件
 */

import React from 'react'
import {
  FileTextOutlined,
  PictureOutlined,
  ExperimentOutlined,
  NumberOutlined
} from '@ant-design/icons'
import { CheckListPanel } from './'

// 示例数据：包含各种状态的核对项
const exampleCheckGroups = [
  {
    id: 'basic',
    name: '报告基础核对',
    icon: <FileTextOutlined />,
    items: [
      {
        code: 'C01',
        name: '首页与第三页一致性',
        status: 'pass',
        description: '委托方、样品名称、型号规格一致性核对'
      },
      {
        code: 'C02',
        name: '第三页扩展字段',
        status: 'pass',
        description: '型号规格、生产日期、产品编号/批号、商标、生产单位一致性核对'
      },
      {
        code: 'C03',
        name: '生产日期格式',
        status: 'fail',
        errorCount: 2,
        description: '表格与标签格式不一致',
        details: (
          <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px', color: '#f87171' }}>错误详情</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#d1d5db' }}>
              <li>表格日期格式: 2024-01-15</li>
              <li>标签日期格式: 2024年01月15日</li>
              <li>建议统一使用 YYYY-MM-DD 格式</li>
            </ul>
          </div>
        )
      },
      {
        code: 'C04',
        name: '样品描述表格',
        status: 'warning',
        warningCount: 1,
        description: '部分部件描述与标签存在差异',
        details: (
          <div style={{ padding: '12px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px', color: '#fbbf24' }}>警告详情</h4>
            <p style={{ margin: 0, color: '#d1d5db' }}>电源适配器描述中的型号与标签不完全一致，建议人工复核。</p>
          </div>
        )
      }
    ]
  },
  {
    id: 'photo',
    name: '样品照片核对',
    icon: <PictureOutlined />,
    items: [
      {
        code: 'C05',
        name: '样品照片数量',
        status: 'pass',
        description: '首页照片数量与实物照片数量核对'
      },
      {
        code: 'C06',
        name: '样品照片一致性',
        status: 'pass',
        description: '照片内容与描述一致性核对'
      }
    ]
  },
  {
    id: 'inspection',
    name: '检验项目核对',
    icon: <ExperimentOutlined />,
    items: [
      {
        code: 'C07',
        name: '单项结论核对',
        status: 'fail',
        errorCount: 1,
        description: '单项结论与综合结论一致性核对',
        details: (
          <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px', color: '#f87171' }}>结论不一致</h4>
            <p style={{ margin: 0, color: '#d1d5db' }}>第3项检验结论为"不合格"，但综合结论标记为"合格"。</p>
          </div>
        )
      },
      {
        code: 'C08',
        name: '非空字段核对',
        status: 'pass',
        description: '标准要求、检验结果、单项结论非空核对'
      },
      {
        code: 'C09',
        name: '产品编号/批号',
        status: 'pass',
        description: '检验项目与首页产品编号/批号一致性核对'
      },
      {
        code: 'C10',
        name: '续检标记核对',
        status: 'warning',
        warningCount: 1,
        description: '续检项目标记与结论一致性核对',
        details: (
          <div style={{ padding: '12px', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '8px' }}>
            <h4 style={{ margin: '0 0 8px', color: '#fbbf24' }}>标记缺失</h4>
            <p style={{ margin: 0, color: '#d1d5db' }}>第5项为续检项目，但缺少续检标记。</p>
          </div>
        )
      }
    ]
  },
  {
    id: 'page',
    name: '页码校验',
    icon: <NumberOutlined />,
    items: [
      {
        code: 'C11',
        name: '页码连续性',
        status: 'pass',
        description: '报告页码连续性与总页数核对'
      }
    ]
  }
]

/**
 * 示例组件
 */
export default function CheckListPanelExample() {
  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <h2 style={{ color: '#f9fafb', marginBottom: '20px' }}>核对内容清单示例</h2>
      <CheckListPanel checkGroups={exampleCheckGroups} />
    </div>
  )
}

/**
 * 使用说明：
 *
 * 1. CheckListPanel - 总容器组件
 *    - 接收 checkGroups 属性，包含所有核对分组数据
 *    - 内置筛选功能：全部/仅错误/仅警告
 *    - 自动计算统计数据并显示
 *
 * 2. CheckGroupCard - 分组卡片组件
 *    - 显示分组名称、图标、通过进度
 *    - 自动计算分组内各状态数量
 *    - 包含多个 CheckItemCard 子组件
 *
 * 3. CheckItemCard - 单项核对卡片组件
 *    - 显示编号(C01-C11)、名称、状态图标
 *    - 显示错误/警告计数徽章
 *    - 支持可折叠的详情区域（使用 framer-motion 动画）
 *    - 错误状态带红色发光边框，警告状态带橙色边框
 *
 * 数据结构：
 * {
 *   id: 'group-id',
 *   name: '分组名称',
 *   icon: <IconComponent />,
 *   items: [
 *     {
 *       code: 'C01',
 *       name: '核对项名称',
 *       status: 'pass' | 'fail' | 'warning' | 'skip',
 *       description: '描述文本',
 *       errorCount: 0,
 *       warningCount: 0,
 *       details: <ReactNode> // 可选，详情内容
 *     }
 *   ]
 * }
 */
