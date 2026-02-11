import React from 'react'
import {
  Card,
  Button,
  Spin,
  Result,
  Tabs,
  Table,
  Tag,
  Descriptions,
  Alert,
  Statistic,
  Row,
  Col,
  Space,
  Typography,
  List,
  Switch,
  Tooltip,
  message,
  Dropdown
} from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  FileTextOutlined,
  WarningOutlined,
  InfoCircleOutlined,
  DownloadOutlined,
  FilePdfOutlined,
  FileExcelOutlined
} from '@ant-design/icons'

const { Title, Text } = Typography
const { TabPane } = Tabs

function CheckResult({ fileInfo, result, loading, onCheck, onReset, llmEnabled, onLlmToggle, apiBaseUrl }) {
  // 导出报告
  const handleExport = async (format) => {
    try {
      const response = await fetch(`${apiBaseUrl}/api/export/${fileInfo.file_id}?format=${format}`)

      if (!response.ok) {
        throw new Error('导出失败')
      }

      // 获取文件名
      const contentDisposition = response.headers.get('content-disposition')
      let filename = `核对报告.${format === 'excel' ? 'xlsx' : format}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/)
        if (match) {
          filename = match[1]
        }
      }

      // 下载文件
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      message.success(`报告已导出: ${filename}`)
    } catch (error) {
      message.error(`导出失败: ${error.message}`)
    }
  }

  // 文件信息卡片
  const renderFileInfo = () => (
    <Card size="small" style={{ marginBottom: 16 }}>
      <Space>
        <FileTextOutlined style={{ fontSize: 24, color: '#1890ff' }} />
        <div>
          <div style={{ fontWeight: 500 }}>{fileInfo.filename}</div>
          <Text type="secondary" style={{ fontSize: 12 }}>
            类型: {fileInfo.file_type.toUpperCase()}
          </Text>
        </div>
      </Space>
    </Card>
  )

  // 统计卡片
  const renderStatistics = () => {
    if (!result) return null

    return (
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="总部件数"
              value={result.total_components}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="通过"
              value={result.passed_components}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="失败"
              value={result.failed_components}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>
    )
  }

  // 首页与第三页比对表格
  const renderHomeThirdComparison = () => {
    if (!result || !result.home_third_comparison) return null

    const columns = [
      {
        title: '字段名',
        dataIndex: 'field_name',
        key: 'field_name',
      },
      {
        title: '首页值',
        dataIndex: 'table_value',
        key: 'table_value',
        render: (text) => text || <Text type="secondary">/</Text>,
      },
      {
        title: '第三页值',
        dataIndex: 'ocr_value',
        key: 'ocr_value',
        render: (text) => text || <Text type="secondary">/</Text>,
      },
      {
        title: '状态',
        dataIndex: 'is_match',
        key: 'is_match',
        render: (isMatch) => (
          isMatch ? (
            <Tag color="success" icon={<CheckCircleOutlined />}>一致</Tag>
          ) : (
            <Tag color="error" icon={<CloseCircleOutlined />}>不一致</Tag>
          )
        ),
      },
    ]

    return (
      <Table
        dataSource={result.home_third_comparison}
        columns={columns}
        rowKey="field_name"
        pagination={false}
        size="small"
      />
    )
  }

  // 样品描述表格
  const renderSampleTable = () => {
    if (!result || !result.sample_description_table) {
      return <Alert message="未找到样品描述表格" type="warning" />
    }

    const table = result.sample_description_table
    const columns = table.headers.map((header, index) => ({
      title: header,
      dataIndex: index,
      key: index,
      render: (text) => text || <Text type="secondary">/</Text>,
    }))

    const dataSource = table.rows.map((row, index) => ({
      key: index,
      ...row.reduce((acc, cell, i) => ({ ...acc, [i]: cell }), {}),
    }))

    return (
      <Table
        dataSource={dataSource}
        columns={columns}
        pagination={{ pageSize: 10 }}
        size="small"
        scroll={{ x: 'max-content' }}
      />
    )
  }

  // 部件核对结果
  const renderComponentChecks = () => {
    if (!result || !result.component_checks) return null

    return (
      <List
        grid={{ gutter: 16, column: 1 }}
        dataSource={result.component_checks}
        renderItem={(item) => (
          <List.Item>
            <Card
              size="small"
              title={item.component_name}
              extra={
                <Tag color={
                  item.status === 'pass' ? 'success' :
                  item.status === 'fail' ? 'error' : 'warning'
                }>
                  {item.status === 'pass' ? '通过' :
                   item.status === 'fail' ? '失败' : '警告'}
                </Tag>
              }
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {/* 基本信息 */}
                <Row gutter={16}>
                  <Col span={12}>
                    <Space>
                      <Text strong>照片覆盖:</Text>
                      {item.has_photo ? (
                        <Tag color="success" icon={<CheckCircleOutlined />}>有</Tag>
                      ) : (
                        <Tag color="error" icon={<CloseCircleOutlined />}>无</Tag>
                      )}
                    </Space>
                  </Col>
                  <Col span={12}>
                    <Space>
                      <Text strong>中文标签:</Text>
                      {item.has_chinese_label ? (
                        <Tag color="success" icon={<CheckCircleOutlined />}>有</Tag>
                      ) : (
                        <Tag color="error" icon={<CloseCircleOutlined />}>无</Tag>
                      )}
                    </Space>
                  </Col>
                </Row>

                {/* 匹配的照片信息 */}
                {item.matched_photos && item.matched_photos.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text strong style={{ display: 'block', marginBottom: 4 }}>
                      匹配的照片 ({item.matched_photos.length}张):
                    </Text>
                    <Space size={[0, 4]} wrap>
                      {item.matched_photos.map((photo, idx) => (
                        <Tag key={idx} color="blue" style={{ marginBottom: 4 }}>
                          第{photo.page_num}页: {photo.caption || '无标题'}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}

                {/* 匹配的标签信息 */}
                {item.matched_labels && item.matched_labels.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text strong style={{ display: 'block', marginBottom: 4 }}>
                      匹配的中文标签 ({item.matched_labels.length}个):
                    </Text>
                    <Space size={[0, 4]} wrap>
                      {item.matched_labels.map((label, idx) => (
                        <Tag key={idx} color="cyan" style={{ marginBottom: 4 }}>
                          第{label.page_num}页: {label.caption || '无标题'}
                        </Tag>
                      ))}
                    </Space>
                  </div>
                )}

                {/* 字段比对详情 */}
                {item.field_comparisons && item.field_comparisons.length > 0 && (
                  <div style={{ marginTop: 12 }}>
                    <Text strong style={{ display: 'block', marginBottom: 8 }}>
                      字段比对详情:
                    </Text>
                    <Table
                      size="small"
                      pagination={false}
                      dataSource={item.field_comparisons}
                      rowKey="field_name"
                      columns={[
                        {
                          title: '字段名',
                          dataIndex: 'field_name',
                          key: 'field_name',
                          width: 100,
                        },
                        {
                          title: '表格值',
                          dataIndex: 'table_value',
                          key: 'table_value',
                          render: (text) => text || <Text type="secondary">/</Text>,
                        },
                        {
                          title: 'OCR识别值',
                          dataIndex: 'ocr_value',
                          key: 'ocr_value',
                          render: (text) => text || <Text type="secondary">/</Text>,
                        },
                        {
                          title: '状态',
                          dataIndex: 'is_match',
                          key: 'is_match',
                          width: 80,
                          render: (isMatch) => (
                            isMatch ? (
                              <Tag color="success" icon={<CheckCircleOutlined />}>一致</Tag>
                            ) : (
                              <Tag color="error" icon={<CloseCircleOutlined />}>不一致</Tag>
                            )
                          ),
                        },
                      ]}
                    />
                  </div>
                )}

                {/* 匹配原因说明 */}
                {item.match_reason && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      <InfoCircleOutlined style={{ marginRight: 4 }} />
                      {item.match_reason}
                    </Text>
                  </div>
                )}

                {/* 问题列表 */}
                {item.issues.length > 0 && (
                  <Alert
                    message="问题"
                    description={
                      <ul style={{ margin: 0, paddingLeft: 16 }}>
                        {item.issues.map((issue, idx) => (
                          <li key={idx}>{issue}</li>
                        ))}
                      </ul>
                    }
                    type={item.status === 'fail' ? 'error' : 'warning'}
                    showIcon
                    style={{ marginTop: 12 }}
                  />
                )}
              </Space>
            </Card>
          </List.Item>
        )}
      />
    )
  }

  // 错误和警告列表
  const renderIssues = () => {
    if (!result) return null

    const allIssues = [
      ...(result.errors || []),
      ...(result.warnings || []),
      ...(result.info || []),
    ]

    if (allIssues.length === 0) {
      return <Alert message="未发现任何问题" type="success" showIcon />
    }

    return (
      <List
        dataSource={allIssues}
        renderItem={(item) => (
          <List.Item>
            <Alert
              message={item.message}
              description={
                item.page_num && (
                  <Text type="secondary">页码: {item.page_num}</Text>
                )
              }
              type={
                item.level === 'ERROR' ? 'error' :
                item.level === 'WARN' ? 'warning' : 'info'
              }
              showIcon
            />
          </List.Item>
        )}
      />
    )
  }

  // 未开始核对状态
  if (!result && !loading) {
    return (
      <div>
        {renderFileInfo()}
        <Result
          icon={<FileTextOutlined style={{ color: '#1890ff' }} />}
          title="文件已上传"
          subTitle={`${fileInfo.filename} 准备就绪，点击下方按钮开始核对`}
          extra={[
            <div key="llm-toggle" style={{ marginBottom: 16, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
              <Tooltip title="启用后，当OCR识别失败时会调用大模型(LLM)进行辅助识别，可提高识别准确率但会增加处理时间">
                <InfoCircleOutlined style={{ color: '#1890ff' }} />
              </Tooltip>
              <span>LLM 增强识别:</span>
              <Switch
                checked={llmEnabled}
                onChange={onLlmToggle}
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
            </div>,
            <Button type="primary" key="check" onClick={onCheck}>
              开始核对
            </Button>,
            <Button key="reset" onClick={onReset}>
              重新选择
            </Button>,
          ]}
        />
      </div>
    )
  }

  // 加载中状态
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 0' }}>
        <Spin size="large" />
        <div style={{ marginTop: 16 }}>
          <Text>正在核对报告，请稍候...</Text>
        </div>
        <div style={{ marginTop: 8 }}>
          <Text type="secondary">包括：PDF解析、OCR识别、字段比对等步骤</Text>
        </div>
      </div>
    )
  }

  // 核对结果展示
  return (
    <div>
      {renderFileInfo()}
      {renderStatistics()}

      <Tabs defaultActiveKey="1">
        <TabPane tab="首页与第三页比对" key="1">
          {renderHomeThirdComparison()}
        </TabPane>
        <TabPane tab="样品描述表格" key="2">
          {renderSampleTable()}
        </TabPane>
        <TabPane tab={`部件核对 (${result?.component_checks?.length || 0})`} key="3">
          {renderComponentChecks()}
        </TabPane>
        <TabPane tab="问题汇总" key="4">
          {renderIssues()}
        </TabPane>
      </Tabs>

      <div style={{ marginTop: 24, textAlign: 'center' }}>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={onCheck}>
            重新核对
          </Button>
          <Dropdown
            menu={{
              items: [
                {
                  key: 'pdf',
                  icon: <FilePdfOutlined />,
                  label: '导出 PDF 报告',
                  onClick: () => handleExport('pdf'),
                },
                {
                  key: 'excel',
                  icon: <FileExcelOutlined />,
                  label: '导出 Excel 表格',
                  onClick: () => handleExport('excel'),
                },
              ],
            }}
          >
            <Button icon={<DownloadOutlined />} type="primary">
              导出报告
            </Button>
          </Dropdown>
          <Button onClick={onReset}>
            上传新文件
          </Button>
        </Space>
      </div>
    </div>
  )
}

export default CheckResult
