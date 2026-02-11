import React from 'react';
import { Button, Input, message, Tooltip } from 'antd';
import {
  ArrowLeftOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  SearchOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import StatsCard from '../components/StatsCard';
import FilterTabs from '../components/FilterTabs';
import FieldList from '../components/FieldList';
import ImagePreview from '../components/ImagePreview';
import { useAppStore } from '../stores/appStore';
import { exportToExcel, exportToPDF } from '../utils/export';

interface ResultsPageProps {
  onBack: () => void;
}

const ResultsPage: React.FC<ResultsPageProps> = ({ onBack }) => {
  const {
    currentResult,
    searchQuery,
    setSearchQuery,
    clearFiles,
    setResult,
  } = useAppStore();

  const handleExportExcel = () => {
    if (currentResult) {
      exportToExcel(currentResult);
      message.success('Excel报告已导出');
    }
  };

  const handleExportPDF = () => {
    if (currentResult) {
      exportToPDF(currentResult);
    }
  };

  const handleNewVerification = () => {
    clearFiles();
    setResult(null);
    onBack();
  };

  if (!currentResult) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-500 mb-4">暂无核对结果</p>
          <Button type="primary" onClick={onBack}>
            返回上传
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                icon={<ArrowLeftOutlined />}
                onClick={onBack}
                className="border-gray-300"
              >
                返回
              </Button>
              <div>
                <h1 className="text-xl font-bold text-gray-800">
                  核对结果
                </h1>
                <p className="text-sm text-gray-500">
                  {currentResult.fileName}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Tooltip title="导出Excel">
                <Button
                  icon={<FileExcelOutlined />}
                  onClick={handleExportExcel}
                  className="border-gray-300"
                >
                  Excel
                </Button>
              </Tooltip>
              <Tooltip title="导出PDF">
                <Button
                  icon={<FilePdfOutlined />}
                  onClick={handleExportPDF}
                  className="border-gray-300"
                >
                  PDF
                </Button>
              </Tooltip>
              <Button
                type="primary"
                icon={<ReloadOutlined />}
                onClick={handleNewVerification}
                className="bg-primary"
              >
                新核对
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats */}
        <div className="mb-6">
          <StatsCard stats={currentResult.stats} />
        </div>

        {/* Filters and Search */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <FilterTabs result={currentResult} />

            <Input.Search
              placeholder="搜索字段名称或值..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              prefix={<SearchOutlined className="text-gray-400" />}
              allowClear
              className="w-full md:w-80"
            />
          </div>
        </div>

        {/* Results List */}
        <FieldList />
      </main>

      {/* Image Preview Modal */}
      <ImagePreview />
    </div>
  );
};

export default ResultsPage;
