import { useState } from 'react';
import { motion } from 'framer-motion';
import { FileText } from 'lucide-react';
import { GlassCard } from '../../components/ui/GlassCard';
import { Button } from '../../components/ui/Button';
import { FileUpload, type FileUploadFile } from '../../components/shared/FileUpload';
import { ProgressOverlay } from '../../components/shared/ProgressOverlay';
import { SPRING_GENTLE } from '../../constants/motion';
import type { CheckResult, CheckStatus, ErrorLevel, ReportCheckResult } from '../../types/report';

interface ReportUploadProps {
  onResults: (result: ReportCheckResult) => void;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface BackendReportResultResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  result?: {
    summary?: {
      total_checks?: number;
      passed?: number;
      errors?: number;
      warnings?: number;
    };
    checks?: Record<string, { name?: string; status?: string; message?: string }>;
  };
  error?: string;
}

const toFrontendStatus = (status: string | undefined): CheckStatus => {
  if (status === 'pass') return 'PASS';
  if (status === 'warning') return 'WARN';
  if (status === 'skipped') return 'SKIP';
  return 'FAIL';
};

const toErrorLevel = (status: CheckStatus): ErrorLevel => {
  if (status === 'PASS' || status === 'SKIP') return 'INFO';
  if (status === 'WARN') return 'WARN';
  return 'ERROR';
};

const mapBackendResult = (payload: BackendReportResultResponse): ReportCheckResult => {
  const summary = payload.result?.summary ?? {};
  const checksMap = payload.result?.checks ?? {};
  const checks: CheckResult[] = Object.entries(checksMap).map(([code, value]) => {
    const status = toFrontendStatus(value.status);
    return {
      code,
      name: value.name || code,
      status,
      level: toErrorLevel(status),
      message: value.message,
      details: value as unknown as Record<string, unknown>,
    };
  });

  return {
    task_id: payload.task_id,
    status:
      payload.status === 'completed' || payload.status === 'error' || payload.status === 'processing'
        ? payload.status
        : 'processing',
    statistics: {
      total: summary.total_checks ?? checks.length,
      passed: summary.passed ?? 0,
      failed: summary.errors ?? 0,
      warnings: summary.warnings ?? 0,
    },
    checks,
    error: payload.error,
  };
};

/**
 * ReportUpload - Upload component for report self-check
 *
 * Features:
 * - Single file upload (report PDF)
 * - LLM enhancement toggle (optional)
 * - Progress tracking
 */
export function ReportUpload({ onResults }: ReportUploadProps) {
  const [files, setFiles] = useState<FileUploadFile[]>([]);
  const [progressStatus, setProgressStatus] = useState<'idle' | 'processing' | 'completed' | 'error'>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [enableLlm, setEnableLlm] = useState(false);

  const handleFilesChange = (newFiles: FileUploadFile[]) => {
    setFiles(newFiles);
    setError(null);
  };

  const handleUpload = async () => {
    if (files.length === 0 || !files[0]) {
      setError('请先上传检验报告');
      return;
    }

    setProgressStatus('processing');
    setProgress(0);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('report_file', files[0].file);

      const uploadResponse = await fetch(`${API_BASE_URL}/api/report/upload?enable_llm=${String(enableLlm)}`, {
        method: 'POST',
        body: formData,
      });

      if (!uploadResponse.ok) {
        throw new Error(`上传失败: ${uploadResponse.status}`);
      }

      const uploadResult = await uploadResponse.json();
      const taskId = uploadResult.task_id;

      // Start polling for progress
      await pollProgress(taskId);
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败');
      setProgressStatus('idle');
    }
  };

  const pollProgress = async (taskId: string) => {
    const maxAttempts = 120; // 60 seconds with 500ms interval
    let attempts = 0;

    const poll = async (): Promise<void> => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/report/${taskId}/progress`);
        if (!response.ok) {
          if (response.status === 404) {
            setError('任务未找到');
            setProgressStatus('error');
            return;
          }
          throw new Error(`查询进度失败: ${response.status}`);
        }

        const data = (await response.json()) as {
          status?: string;
          progress?: number;
          message?: string;
          error?: string;
        };

        setProgress(data.progress || 0);

        if (data.status === 'completed') {
          const resultResponse = await fetch(`${API_BASE_URL}/api/report/${taskId}/result`);
          if (!resultResponse.ok) {
            throw new Error(`获取结果失败: ${resultResponse.status}`);
          }
          const resultData = (await resultResponse.json()) as BackendReportResultResponse;
          setProgressStatus('completed');
          onResults(mapBackendResult(resultData));
          return;
        }

        if (data.status === 'error') {
          setError(data.error || data.message || '核对过程出错');
          setProgressStatus('error');
          return;
        }

        if (data.status === 'not_found') {
          setError('任务未找到');
          setProgressStatus('error');
          return;
        }

        attempts++;
        if (attempts >= maxAttempts) {
          setError('核对超时');
          setProgressStatus('error');
          return;
        }

        await new Promise((resolve) => setTimeout(resolve, 500));
        await poll();
      } catch (err) {
        setError(err instanceof Error ? err.message : '查询进度失败');
        setProgressStatus('error');
      }
    };

    await poll();
  };

  const handleBack = () => {
    window.location.hash = '#/';
  };

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={SPRING_GENTLE}
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: 'calc(100vh - 160px)',
          padding: '2rem',
          gap: '2rem',
        }}
      >
        <GlassCard style={{ width: '100%', maxWidth: '600px' }}>
          <div style={{ padding: '2rem', textAlign: 'center' }}>
            <motion.div
              style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                background: 'var(--glass-bg)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 1.5rem',
                color: 'var(--color-accent)',
              }}
              whileHover={{ scale: 1.1, rotate: 5 }}
              transition={SPRING_GENTLE}
            >
              <FileText size={40} />
            </motion.div>

            <h1 style={{ fontSize: '1.75rem', fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-primary)' }}>
              报告自身核对
            </h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>
              上传检验报告，自动核对字段一致性、照片覆盖、标签匹配等
            </p>

            <FileUpload
              mode="single"
              accept=".pdf"
              onFilesChange={handleFilesChange}
              disabled={progressStatus === 'processing'}
            />

            {/* LLM Enhancement Toggle */}
            <div
              style={{
                marginTop: '1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
              }}
            >
              <input
                type="checkbox"
                id="enable-llm"
                checked={enableLlm}
                onChange={(e) => setEnableLlm(e.target.checked)}
                disabled={progressStatus === 'processing'}
                style={{ cursor: 'pointer' }}
              />
              <label
                htmlFor="enable-llm"
                style={{
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  fontSize: '0.9rem',
                }}
              >
                启用 LLM 增强识别（可选）
              </label>
            </div>

            {error && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                style={{
                  marginTop: '1rem',
                  padding: '0.75rem 1rem',
                  background: 'rgba(192, 120, 120, 0.2)',
                  borderRadius: '8px',
                  color: 'var(--color-danger)',
                  fontSize: '0.9rem',
                }}
              >
                {error}
              </motion.div>
            )}

            <div
              style={{
                display: 'flex',
                gap: '1rem',
                marginTop: '2rem',
                justifyContent: 'center',
              }}
            >
              <Button variant="secondary" onClick={handleBack} disabled={progressStatus === 'processing'}>
                返回
              </Button>
              <Button
                variant="primary"
                onClick={handleUpload}
                disabled={files.length === 0 || progressStatus === 'processing'}
              >
                {progressStatus === 'processing' ? '核对中...' : '开始核对'}
              </Button>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      <ProgressOverlay
        status={progressStatus}
        progress={progress}
        message="正在核对报告..."
        error={error || undefined}
      />
    </>
  );
}
