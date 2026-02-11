import React, { useState, useRef, useCallback } from 'react';
import { Modal, Slider, Button, Space } from 'antd';
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  DownloadOutlined,
  RotateLeftOutlined,
  RotateRightOutlined,
  CloseOutlined,
} from '@ant-design/icons';
import { useAppStore } from '../stores/appStore';

const ImagePreview: React.FC = () => {
  const { imagePreviewOpen, previewImagePath, closeImagePreview } = useAppStore();
  const [scale, setScale] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  const handleZoomIn = () => setScale((s) => Math.min(s + 0.25, 5));
  const handleZoomOut = () => setScale((s) => Math.max(s - 0.25, 0.25));
  const handleRotateLeft = () => setRotation((r) => r - 90);
  const handleRotateRight = () => setRotation((r) => r + 90);
  const handleReset = () => {
    setScale(1);
    setRotation(0);
    setPosition({ x: 0, y: 0 });
  };

  const handleDownload = () => {
    if (previewImagePath) {
      const link = document.createElement('a');
      link.href = previewImagePath;
      link.download = `image_${Date.now()}.png`;
      link.click();
    }
  };

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (scale > 1) {
      setIsDragging(true);
      dragStart.current = { x: e.clientX - position.x, y: e.clientY - position.y };
    }
  }, [scale, position]);

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (isDragging && scale > 1) {
      setPosition({
        x: e.clientX - dragStart.current.x,
        y: e.clientY - dragStart.current.y,
      });
    }
  }, [isDragging, scale]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale((s) => Math.max(0.25, Math.min(5, s + delta)));
  }, []);

  return (
    <Modal
      open={imagePreviewOpen}
      onCancel={() => {
        closeImagePreview();
        handleReset();
      }}
      footer={null}
      width="90vw"
      style={{ maxWidth: 1200 }}
      closeIcon={<CloseOutlined />}
      destroyOnClose
    >
      <div className="flex flex-col h-[80vh]">
        {/* Toolbar */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-t-lg border-b">
          <Space>
            <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} />
            <Slider
              value={scale}
              min={0.25}
              max={5}
              step={0.25}
              onChange={setScale}
              style={{ width: 120 }}
            />
            <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} />
            <span className="text-sm text-gray-600 ml-2">
              {Math.round(scale * 100)}%
            </span>
          </Space>
          <Space>
            <Button icon={<RotateLeftOutlined />} onClick={handleRotateLeft}>
              左旋
            </Button>
            <Button icon={<RotateRightOutlined />} onClick={handleRotateRight}>
              右旋
            </Button>
            <Button icon={<DownloadOutlined />} onClick={handleDownload}>
              下载
            </Button>
            <Button onClick={handleReset}>重置</Button>
          </Space>
        </div>

        {/* Image Container */}
        <div
          ref={containerRef}
          className="flex-1 bg-gray-100 overflow-hidden flex items-center justify-center cursor-move"
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        >
          {previewImagePath && (
            <img
              src={previewImagePath}
              alt="Preview"
              className="max-w-full max-h-full object-contain transition-transform duration-100"
              style={{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale}) rotate(${rotation}deg)`,
                cursor: isDragging ? 'grabbing' : scale > 1 ? 'grab' : 'default',
              }}
              draggable={false}
            />
          )}
        </div>

        {/* Info Bar */}
        <div className="p-3 bg-gray-50 rounded-b-lg border-t text-sm text-gray-500 text-center">
          滚轮缩放 • 拖拽移动 • 双击重置
        </div>
      </div>
    </Modal>
  );
};

export default ImagePreview;
