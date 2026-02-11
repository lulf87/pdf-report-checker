import React, { useCallback, useState } from 'react';
import { Upload, message } from 'antd';
import {
  InboxOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useAppStore } from '../stores/appStore';
import { formatFileSize, generateId } from '../utils/format';
import type { UploadedFile } from '../types';

const { Dragger } = Upload;

const FileUpload: React.FC = () => {
  const { files, addFile, removeFile, isProcessing } = useAppStore();
  const [isDragging] = useState(false);

  const handleFileChange = useCallback(
    (info: any) => {
      const { file } = info;

      if (file.status === 'done' || file.status === 'uploading') {
        // Check if file already exists
        const exists = files.some(
          (f) => f.name === file.name && f.size === file.size
        );
        if (exists) {
          message.warning(`文件 "${file.name}" 已存在`);
          return;
        }

        const newFile: UploadedFile = {
          id: generateId(),
          name: file.name,
          type: file.name.toLowerCase().endsWith('.pdf') ? 'pdf' : 'docx',
          size: file.size,
          path: file.originFileObj?.path || URL.createObjectURL(file.originFileObj),
          status: 'pending',
        };

        addFile(newFile);
        message.success(`已添加文件: ${file.name}`);
      }
    },
    [files, addFile]
  );

  const handleRemove = useCallback(
    (id: string, name: string) => {
      removeFile(id);
      message.success(`已删除: ${name}`);
    },
    [removeFile]
  );

  const getFileIcon = (type: string, status: UploadedFile['status']) => {
    if (status === 'processing') {
      return <LoadingOutlined className="text-xl text-primary" spin />;
    }
    if (status === 'completed') {
      return <CheckCircleOutlined className="text-xl text-green-500" />;
    }
    if (status === 'error') {
      return <CloseCircleOutlined className="text-xl text-red-500" />;
    }
    return type === 'pdf' ? (
      <FilePdfOutlined className="text-xl text-red-500" />
    ) : (
      <FileWordOutlined className="text-xl text-blue-500" />
    );
  };

  const getStatusText = (status: UploadedFile['status']) => {
    const statusMap = {
      pending: '待处理',
      processing: '处理中...',
      completed: '已完成',
      error: '错误',
    };
    return statusMap[status];
  };

  return (
    <div className="w-full max-w-3xl mx-auto">
      <Dragger
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        multiple={true}
        showUploadList={false}
        customRequest={({ onSuccess }) => {
          setTimeout(() => onSuccess?.('ok'), 0);
        }}
        onChange={handleFileChange}
        disabled={isProcessing}
        className={`
          border-2 border-dashed rounded-xl transition-all duration-200
          ${isDragging ? 'border-primary bg-blue-50' : 'border-gray-300 bg-white'}
          ${isProcessing ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary hover:bg-blue-50'}
        `}
      >
        <div className="py-12 px-6 text-center">
          <div className="mb-4">
            <div className="w-16 h-16 mx-auto rounded-full bg-blue-50 flex items-center justify-center">
              <InboxOutlined className="text-3xl text-primary" />
            </div>
          </div>
          <p className="text-lg font-medium text-gray-700 mb-2">
            点击或拖拽文件到此处上传
          </p>
          <p className="text-sm text-gray-500">
            支持 PDF、DOCX 格式文件
          </p>
        </div>
      </Dragger>

      {files.length > 0 && (
        <div className="mt-6 animate-fade-in">
          <h3 className="text-sm font-medium text-gray-700 mb-3">
            已上传文件 ({files.length})
          </h3>
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 hover:border-primary hover:shadow-sm transition-all duration-200"
              >
                <div className="flex items-center gap-3">
                  {getFileIcon(file.type, file.status)}
                  <div>
                    <p className="font-medium text-gray-800 truncate max-w-xs">
                      {file.name}
                    </p>
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <span>{formatFileSize(file.size)}</span>
                      <span>•</span>
                      <span
                        className={`
                          ${file.status === 'completed' ? 'text-green-600' : ''}
                          ${file.status === 'error' ? 'text-red-600' : ''}
                          ${file.status === 'processing' ? 'text-primary' : ''}
                        `}
                      >
                        {getStatusText(file.status)}
                      </span>
                    </div>
                    {file.errorMessage && (
                      <p className="text-xs text-red-500 mt-1">
                        {file.errorMessage}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleRemove(file.id, file.name)}
                  disabled={isProcessing}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="删除"
                >
                  <DeleteOutlined />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
