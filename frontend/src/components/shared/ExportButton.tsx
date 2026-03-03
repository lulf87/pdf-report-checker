import { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '../ui/Button';
import { SPINNER_LINEAR, SPRING_SNAPPY } from '../../constants/motion';

type ExportStatus = 'idle' | 'loading' | 'success' | 'error';
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ExportButtonProps {
  /** API endpoint for export (e.g., '/api/ptr/task-id/export') */
  exportUrl: string;
  /** Default filename for download */
  filename?: string;
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'ghost';
  /** Custom button text */
  buttonText?: string;
  /** Loading text */
  loadingText?: string;
  /** Success callback */
  onSuccess?: () => void;
  /** Error callback */
  onError?: (error: string) => void;
  /** Disabled state */
  disabled?: boolean;
  /** Additional className */
  className?: string;
}

/**
 * ExportButton - Reusable button for PDF export
 *
 * Features:
 * - Loading state with spinner animation
 * - Success/error feedback
 * - Automatic file download
 * - Accessible design
 */
export function ExportButton({
  exportUrl,
  filename = 'report.pdf',
  variant = 'secondary',
  buttonText = '导出 PDF',
  loadingText = '正在生成...',
  onSuccess,
  onError,
  disabled = false,
  className,
}: ExportButtonProps) {
  const [status, setStatus] = useState<ExportStatus>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleExport = async () => {
    setStatus('loading');
    setErrorMessage('');

    try {
      const requestUrl = exportUrl.startsWith('http') ? exportUrl : `${API_BASE_URL}${exportUrl}`;
      const response = await fetch(requestUrl);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: '导出失败' }));
        throw new Error(errorData.detail || `导出失败: ${response.status}`);
      }

      // Get the blob
      const blob = await response.blob();

      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers.get('Content-Disposition');
      let downloadFilename = filename;

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          downloadFilename = filenameMatch[1].replace(/['"]/g, '');
        }
      }

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = downloadFilename;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setStatus('success');
      onSuccess?.();

      // Reset to idle after 2 seconds
      setTimeout(() => {
        setStatus('idle');
      }, 2000);
    } catch (error) {
      const message = error instanceof Error ? error.message : '导出失败，请重试';
      setErrorMessage(message);
      setStatus('error');
      onError?.(message);

      // Reset to idle after 3 seconds
      setTimeout(() => {
        setStatus('idle');
        setErrorMessage('');
      }, 3000);
    }
  };

  const getIcon = () => {
    switch (status) {
      case 'loading':
        return (
          <motion.div
            animate={{ rotate: 360 }}
            transition={SPINNER_LINEAR}
          >
            <Loader2 size={18} />
          </motion.div>
        );
      case 'success':
        return <CheckCircle size={18} style={{ color: 'var(--color-success)' }} />;
      case 'error':
        return <XCircle size={18} style={{ color: 'var(--color-danger)' }} />;
      default:
        return <Download size={18} />;
    }
  };

  const getButtonText = () => {
    switch (status) {
      case 'loading':
        return loadingText;
      case 'success':
        return '导出成功';
      case 'error':
        return '导出失败';
      default:
        return buttonText;
    }
  };

  return (
    <div className={className} style={{ display: 'inline-flex', flexDirection: 'column', gap: '0.5rem' }}>
      <motion.div
        whileHover={status === 'idle' && !disabled ? { scale: 1.02 } : {}}
        whileTap={status === 'idle' && !disabled ? { scale: 0.98 } : {}}
        transition={SPRING_SNAPPY}
      >
        <Button
          variant={variant}
          onClick={handleExport}
          disabled={disabled || status === 'loading'}
          style={{
            opacity: disabled ? 0.5 : 1,
            cursor: disabled || status === 'loading' ? 'not-allowed' : 'pointer',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            {getIcon()}
            {getButtonText()}
          </span>
        </Button>
      </motion.div>

      {status === 'error' && errorMessage && (
        <motion.span
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          style={{
            fontSize: '0.75rem',
            color: 'var(--color-danger)',
            textAlign: 'center',
          }}
        >
          {errorMessage}
        </motion.span>
      )}
    </div>
  );
}

/**
 * ExportButtonGroup - Group of export buttons for both PTR and Report
 */
interface ExportButtonGroupProps {
  /** Task ID for the current operation */
  taskId: string;
  /** Export type: 'ptr' or 'report' */
  type: 'ptr' | 'report';
  /** Position layout */
  layout?: 'horizontal' | 'vertical';
  /** Success callback */
  onSuccess?: () => void;
  /** Error callback */
  onError?: (error: string) => void;
  /** Disabled state */
  disabled?: boolean;
}

export function ExportButtonGroup({
  taskId,
  type,
  layout = 'horizontal',
  onSuccess,
  onError,
  disabled = false,
}: ExportButtonGroupProps) {
  const exportUrl = type === 'ptr'
    ? `/api/ptr/${taskId}/export`
    : `/api/report/${taskId}/export`;

  const defaultFilename = type === 'ptr'
    ? `ptr_comparison_${taskId.slice(0, 8)}.pdf`
    : `report_check_${taskId.slice(0, 8)}.pdf`;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: layout === 'horizontal' ? 'row' : 'column',
        gap: '0.75rem',
      }}
    >
      <ExportButton
        exportUrl={exportUrl}
        filename={defaultFilename}
        variant="secondary"
        buttonText="导出 PDF"
        onSuccess={onSuccess}
        onError={onError}
        disabled={disabled}
      />
    </div>
  );
}

export default ExportButton;
