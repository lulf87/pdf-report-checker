import React, { useState } from 'react';
import { Button, Input, message, Tooltip, Tabs } from 'antd';
import {
  ArrowLeftOutlined,
  FilePdfOutlined,
  FileExcelOutlined,
  SearchOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  TableOutlined,
  PictureOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import StatsCard from '../components/StatsCard';
import FilterTabs from '../components/FilterTabs';
import FieldList from '../components/FieldList';
import InspectionItemTab from '../components/InspectionItemTab';
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

  const [activeTab, setActiveTab] = useState('fields');

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

        {/* Tabs */}
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          type="card"
          className="results-tabs"
          items={[
            {
              key: 'fields',
              label: (
                <span>
                  <CheckCircleOutlined className="mr-1" />
                  字段核对
                </span>
              ),
              children: (
                <>
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
                </>
              ),
            },
            {
              key: 'inspection',
              label: (
                <span>
                  <TableOutlined className="mr-1" />
                  检验项目核对
                  {currentResult.inspectionItemCheck?.incorrect_conclusions > 0 && (
                    <span className="ml-1 text-red-500">
                      (
                      {currentResult.inspectionItemCheck.incorrect_conclusions}
                      )
                    </span>
                  )}
                </span>
              ),
              children: (
                <InspectionItemTab
                  data={currentResult.inspectionItemCheck}
                />
              ),
            },
            {
              key: 'photos',
              label: (
                <span>
                  <PictureOutlined className="mr-1" />
                  照片核对
                </span>
              ),
              children: (
                <div className="flex items-center justify-center h-64 bg-white rounded-xl border border-gray-200">
                  <div className="text-center text-gray-500">
                    <PictureOutlined className="text-4xl mb-4" />
                    <p>照片核对功能开发中</p>
                  </div>
                </div>
              ),
            },
            {
              key: 'issues',
              label: (
                <span>
                  <WarningOutlined className="mr-1" />
                  问题汇总
                </span>
              ),
              children: (
                <div className="flex items-center justify-center h-64 bg-white rounded-xl border border-gray-200">
                  <div className="text-center text-gray-500">
                    <WarningOutlined className="text-4xl mb-4" />
                    <p>问题汇总功能开发中</p>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </main>

      {/* Image Preview Modal */}
      <ImagePreview />
    </div>
  );
};

export default ResultsPage;
