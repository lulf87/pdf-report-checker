import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Upload } from 'lucide-react';
import { FileUpload, type FileUploadFile } from '../../components/shared/FileUpload';
import { ProgressOverlay } from '../../components/shared/ProgressOverlay';
import { Button } from '../../components/ui/Button';
import { GlassCard } from '../../components/ui/GlassCard';
import { SPINNER_LINEAR, SPRING_GENTLE, STAGGER_DELAY } from '../../constants/motion';
import { uploadPTRFiles, pollPTRProgress } from '../../services/ptrApi';
import type {
  PTRCompareResult,
  ProgressStatus,
  ProgressResponse,
} from '../../types/ptr';

interface PTRUploadProps {
  onComplete: (result: PTRCompareResult, taskId: string) => void;
  onBack: () => void;
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: STAGGER_DELAY,
      delayChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: SPRING_GENTLE,
  },
};

/**
 * PTRUpload - File upload page for PTR comparison
 *
 * Features:
 * - Dual file upload (Report PDF + PTR PDF)
 * - PDF validation
 * - Progress polling with timeout
 * - Error handling
 */
export function PTRUpload({ onComplete, onBack }: PTRUploadProps) {
  const [files, setFiles] = useState<{ report?: FileUploadFile; ptr?: FileUploadFile }>({});
  const [progressStatus, setProgressStatus] = useState<ProgressStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isUploading, setIsUploading] = useState(false);

  const handleFilesChange = useCallback((newFiles: FileUploadFile[]) => {
    setFiles((prev) => {
      const updated = { ...prev };
      if (newFiles[0]) updated.report = newFiles[0];
      if (newFiles[1]) updated.ptr = newFiles[1];
      return updated;
    });
  }, []);

  const handleUpload = async () => {
    if (!files.report?.file || !files.ptr?.file) {
      setError('请上传检验报告和产品技术要求');
      return;
    }

    setIsUploading(true);
    setProgressStatus('processing');
    setProgress(0);
    setMessage('正在上传文件...');
    setError('');

    try {
      // Step 1: Upload files
      const uploadResponse = await uploadPTRFiles(files.report.file, files.ptr.file);
      setMessage('正在处理中...');

      // Step 2: Poll for progress
      const result = await pollPTRProgress(
        uploadResponse.task_id,
        (progressData: ProgressResponse) => {
          setProgress(progressData.progress);
          setMessage(progressData.message);
          if (progressData.status === 'error' || progressData.status === 'not_found') {
            setError(progressData.error || '处理失败');
          }
        },
        60000, // 60 second timeout
        1000, // Poll every 1 second
      );

      // Step 3: Complete
      setProgressStatus('completed');
      setProgress(100);
      setMessage('处理完成');

      setTimeout(() => {
        onComplete(result.result, result.task_id);
      }, 500);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '上传失败，请重试';
      setError(errorMessage);
      setProgressStatus('error');
    } finally {
      setIsUploading(false);
    }
  };

  const canUpload = files.report?.file && files.ptr?.file;

  return (
    <>
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        style={{
          width: '100%',
          maxWidth: '600px',
          margin: '0 auto',
          padding: '2rem',
        }}
      >
        {/* Header */}
        <motion.div variants={itemVariants} style={{ marginBottom: '2rem', textAlign: 'center' }}>
          <motion.div
            style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              background: 'var(--glass-bg-hover)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.5rem',
              color: 'var(--color-accent)',
            }}
            animate={{ rotate: [0, 360] }}
            transition={{ ...SPINNER_LINEAR, duration: 20 }}
          >
            <Upload size={40} />
          </motion.div>
          <h1
            style={{
              fontSize: '2rem',
              fontWeight: 600,
              color: 'var(--text-primary)',
              marginBottom: '0.5rem',
            }}
          >
            PTR 条款核对
          </h1>
          <p
            style={{
              fontSize: '1rem',
              color: 'var(--text-secondary)',
            }}
          >
            上传检验报告和产品技术要求，自动核对条款一致性
          </p>
        </motion.div>

        {/* Upload Area */}
        <motion.div variants={itemVariants}>
          <GlassCard>
            <div style={{ padding: '2rem' }}>
              <FileUpload
                mode="double"
                labels={{
                  primary: '上传检验报告 (PDF)',
                  secondary: '上传产品技术要求 (PDF)',
                }}
                onFilesChange={handleFilesChange}
                disabled={isUploading}
                accept=".pdf"
              />
            </div>
          </GlassCard>
        </motion.div>

        {/* Action Buttons */}
        <motion.div
          variants={itemVariants}
          style={{
            display: 'flex',
            gap: '1rem',
            justifyContent: 'center',
            marginTop: '2rem',
          }}
        >
          <Button variant="secondary" onClick={onBack} disabled={isUploading}>
            返回
          </Button>
          <Button
            variant="primary"
            onClick={handleUpload}
            disabled={!canUpload || isUploading}
          >
            {isUploading ? '处理中...' : '开始核对'}
          </Button>
        </motion.div>
      </motion.div>

      {/* Progress Overlay */}
      <ProgressOverlay
        status={progressStatus}
        progress={progress}
        message={message}
        error={error}
      />
    </>
  );
}
