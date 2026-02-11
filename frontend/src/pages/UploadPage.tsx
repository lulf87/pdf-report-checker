import React from 'react';
import { Button, message } from 'antd';
import { FileSearchOutlined, ArrowRightOutlined } from '@ant-design/icons';
import FileUpload from '../components/FileUpload';
import ProgressBar from '../components/ProgressBar';
import { useAppStore } from '../stores/appStore';
import type { VerificationResult, FieldResult } from '../types';

interface UploadPageProps {
  onComplete: () => void;
}

const UploadPage: React.FC<UploadPageProps> = ({ onComplete }) => {
  const { files, isProcessing, setProcessing, setProgress, setResult, setError } = useAppStore();

  const handleStartVerification = async () => {
    if (files.length === 0) {
      message.warning('请先上传文件');
      return;
    }

    setProcessing(true);
    setProgress(0);
    setError(null);

    // Simulate processing steps
    const steps = [
      { progress: 20, delay: 800 },
      { progress: 50, delay: 1500 },
      { progress: 80, delay: 1200 },
      { progress: 100, delay: 800 },
    ];

    for (const step of steps) {
      await new Promise((resolve) => setTimeout(resolve, step.delay));
      setProgress(step.progress);
    }

    // Generate mock result
    const mockResult: VerificationResult = {
      id: `result_${Date.now()}`,
      fileId: files[0].id,
      fileName: files[0].name,
      completedAt: new Date().toISOString(),
      stats: {
        totalFields: 24,
        matched: 18,
        mismatched: 4,
        missing: 2,
        extra: 0,
        confidence: 0.87,
      },
      fields: generateMockFields(),
    };

    setResult(mockResult);
    setProcessing(false);
    message.success('核对完成！');
    onComplete();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary shadow-lg shadow-blue-200 mb-4">
            <FileSearchOutlined className="text-3xl text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            报告核对工具
          </h1>
          <p className="text-gray-500">
            上传PDF或DOCX文件，自动核对表格数据与OCR识别结果
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 mb-6">
          <FileUpload />
        </div>

        {/* Progress */}
        {isProcessing && (
          <div className="mb-6">
            <ProgressBar />
          </div>
        )}

        {/* Start Button */}
        {files.length > 0 && !isProcessing && (
          <div className="flex justify-center animate-fade-in">
            <Button
              type="primary"
              size="large"
              icon={<ArrowRightOutlined />}
              onClick={handleStartVerification}
              className="h-12 px-8 text-lg bg-cta hover:bg-orange-600 border-0 shadow-lg shadow-orange-200"
            >
              开始核对
            </Button>
          </div>
        )}

        {/* Features */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
          {[
            {
              title: '智能识别',
              desc: '支持PDF和DOCX格式，自动提取表格数据',
              icon: '📄',
            },
            {
              title: '精准核对',
              desc: 'OCR识别与表格数据逐字段对比',
              icon: '🔍',
            },
            {
              title: '详细报告',
              desc: '生成差异报告，支持导出PDF和Excel',
              icon: '📊',
            },
          ].map((feature) => (
            <div
              key={feature.title}
              className="bg-white rounded-xl p-6 text-center border border-gray-100 hover:shadow-md transition-shadow duration-200"
            >
              <div className="text-4xl mb-3">{feature.icon}</div>
              <h3 className="font-semibold text-gray-800 mb-1">
                {feature.title}
              </h3>
              <p className="text-sm text-gray-500">{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Generate mock field results for demo
function generateMockFields(): FieldResult[] {
  const fields: FieldResult[] = [
    { id: '1', fieldName: '报告编号', tableValue: 'RPT-2024-001', ocrValue: 'RPT-2024-001', status: 'matched', confidence: 0.98, pageNumber: 1, tableRow: 1, tableCol: 'A' },
    { id: '2', fieldName: '报告日期', tableValue: '2024-01-15', ocrValue: '2024-01-15', status: 'matched', confidence: 0.95, pageNumber: 1, tableRow: 1, tableCol: 'B' },
    { id: '3', fieldName: '客户名称', tableValue: 'ABC科技有限公司', ocrValue: 'ABC科技有限公司', status: 'matched', confidence: 0.92, pageNumber: 1, tableRow: 2, tableCol: 'A' },
    { id: '4', fieldName: '项目名称', tableValue: '产品质量检测', ocrValue: '产品质量检测', status: 'matched', confidence: 0.94, pageNumber: 1, tableRow: 2, tableCol: 'B' },
    { id: '5', fieldName: '检测数量', tableValue: '1000', ocrValue: '1000', status: 'matched', confidence: 0.99, pageNumber: 1, tableRow: 3, tableCol: 'A' },
    { id: '6', fieldName: '合格数量', tableValue: '985', ocrValue: '985', status: 'matched', confidence: 0.99, pageNumber: 1, tableRow: 3, tableCol: 'B' },
    { id: '7', fieldName: '合格率', tableValue: '98.5%', ocrValue: '98.5%', status: 'matched', confidence: 0.96, pageNumber: 1, tableRow: 3, tableCol: 'C' },
    { id: '8', fieldName: '检测标准', tableValue: 'GB/T 2828.1-2012', ocrValue: 'GB/T 2828.1-2012', status: 'matched', confidence: 0.91, pageNumber: 1, tableRow: 4, tableCol: 'A' },
    { id: '9', fieldName: '检测人员', tableValue: '张三', ocrValue: '张三', status: 'matched', confidence: 0.88, pageNumber: 1, tableRow: 5, tableCol: 'A' },
    { id: '10', fieldName: '审核人员', tableValue: '李四', ocrValue: '李四', status: 'matched', confidence: 0.89, pageNumber: 1, tableRow: 5, tableCol: 'B' },
    { id: '11', fieldName: '样品批号', tableValue: 'SP-2024-0156', ocrValue: 'SP-2024-0157', status: 'mismatched', confidence: 0.76, pageNumber: 2, tableRow: 1, tableCol: 'A' },
    { id: '12', fieldName: '生产日期', tableValue: '2024-01-10', ocrValue: '2024-01-11', status: 'mismatched', confidence: 0.72, pageNumber: 2, tableRow: 1, tableCol: 'B' },
    { id: '13', fieldName: '有效期至', tableValue: '2025-01-09', ocrValue: '2025-01-10', status: 'mismatched', confidence: 0.74, pageNumber: 2, tableRow: 1, tableCol: 'C' },
    { id: '14', fieldName: '储存条件', tableValue: '常温避光', ocrValue: '常温避光保存', status: 'mismatched', confidence: 0.68, pageNumber: 2, tableRow: 2, tableCol: 'A' },
    { id: '15', fieldName: '外观检查', tableValue: '合格', ocrValue: '合格', status: 'matched', confidence: 0.93, pageNumber: 2, tableRow: 3, tableCol: 'A' },
    { id: '16', fieldName: '尺寸检测', tableValue: '合格', ocrValue: '合格', status: 'matched', confidence: 0.94, pageNumber: 2, tableRow: 3, tableCol: 'B' },
    { id: '17', fieldName: '重量检测', tableValue: '合格', ocrValue: '合格', status: 'matched', confidence: 0.92, pageNumber: 2, tableRow: 3, tableCol: 'C' },
    { id: '18', fieldName: '性能测试', tableValue: '合格', ocrValue: '合格', status: 'matched', confidence: 0.95, pageNumber: 2, tableRow: 4, tableCol: 'A' },
    { id: '19', fieldName: '安全测试', tableValue: '合格', ocrValue: '合格', status: 'matched', confidence: 0.96, pageNumber: 2, tableRow: 4, tableCol: 'B' },
    { id: '20', fieldName: '备注', tableValue: '无', ocrValue: null, status: 'missing', confidence: 0, pageNumber: 2, tableRow: 5, tableCol: 'A' },
    { id: '21', fieldName: '检测结论', tableValue: '符合标准要求', ocrValue: '符合标准要求', status: 'matched', confidence: 0.90, pageNumber: 3, tableRow: 1, tableCol: 'A' },
    { id: '22', fieldName: '签发日期', tableValue: '2024-01-16', ocrValue: '2024-01-16', status: 'matched', confidence: 0.93, pageNumber: 3, tableRow: 2, tableCol: 'A' },
    { id: '23', fieldName: '签发人', tableValue: '王五', ocrValue: '王五', status: 'matched', confidence: 0.87, pageNumber: 3, tableRow: 2, tableCol: 'B' },
    { id: '24', fieldName: '附加说明', tableValue: null, ocrValue: '需复检项目', status: 'missing', confidence: 0, pageNumber: 3, tableRow: 3, tableCol: 'A' },
  ];

  return fields;
}

export default UploadPage;
