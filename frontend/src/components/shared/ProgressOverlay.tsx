import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { EXIT_TRANSITION, PULSE_FAST, SPINNER_LINEAR, SPRING_GENTLE, SPRING_SMOOTH } from '../../constants/motion';
import { GlassCard } from '../ui/GlassCard';

type ProgressStatus = 'idle' | 'processing' | 'completed' | 'error';

interface ProgressOverlayProps {
  status: ProgressStatus;
  progress?: number;
  message?: string;
  error?: string;
}

/**
 * ProgressOverlay - Processing progress overlay with glassmorphism
 *
 * Features:
 * - Animated progress bar
 * - Status indicators (processing, completed, error)
 * - Smooth enter/exit animations
 * - Non-blocking overlay UI
 */
export function ProgressOverlay({
  status,
  progress = 0,
  message,
  error,
}: ProgressOverlayProps) {
  const isVisible = status !== 'idle';

  const getStatusIcon = () => {
    if (status === 'processing') return <Loader2 size={32} />;
    if (status === 'completed') return <CheckCircle size={32} />;
    if (status === 'error') return <AlertCircle size={32} />;
    return null;
  };

  const getBackgroundStyle = () => {
    if (status === 'processing') return 'var(--glass-bg-hover)';
    if (status === 'completed') return 'rgba(107, 158, 138, 0.2)';
    if (status === 'error') return 'rgba(192, 120, 120, 0.2)';
    return 'var(--glass-bg-hover)';
  };

  const getColorStyle = () => {
    if (status === 'processing') return 'var(--color-accent)';
    if (status === 'completed') return 'var(--color-success)';
    if (status === 'error') return 'var(--color-danger)';
    return 'var(--color-accent)';
  };

  return (
    <AnimatePresence mode="wait">
      {isVisible && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={EXIT_TRANSITION}
          style={{
            position: 'fixed',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(15, 17, 23, 0.8)',
            backdropFilter: 'blur(8px)',
            zIndex: 1000,
          }}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={SPRING_GENTLE}
            style={{ width: '100%', maxWidth: '400px', padding: '1rem' }}
          >
            <GlassCard>
              <div
                style={{
                  padding: '2rem',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '1.5rem',
                  textAlign: 'center',
                }}
              >
                {/* Status Icon */}
                <motion.div
                  style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '50%',
                    background: getBackgroundStyle(),
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: getColorStyle(),
                  }}
                  animate={
                    status === 'processing'
                      ? { rotate: 360 }
                      : status === 'completed'
                      ? { scale: [1, 1.1, 1] }
                      : { scale: [1, 1.05, 1] }
                  }
                  transition={
                    status === 'processing'
                      ? SPINNER_LINEAR
                      : { ...PULSE_FAST, repeat: 0 }
                  }
                >
                  {getStatusIcon()}
                </motion.div>

                {/* Message */}
                <div>
                  <p
                    style={{
                      fontSize: '1.125rem',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                      marginBottom: '0.5rem',
                    }}
                  >
                    {status === 'processing' && '处理中...'}
                    {status === 'completed' && '处理完成'}
                    {status === 'error' && '处理失败'}
                  </p>
                  {message && status !== 'error' && (
                    <p
                      style={{
                        fontSize: '0.875rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {message}
                    </p>
                  )}
                  {error && status === 'error' && (
                    <p
                      style={{
                        fontSize: '0.875rem',
                        color: 'var(--color-danger)',
                      }}
                    >
                      {error}
                    </p>
                  )}
                </div>

                {/* Progress Bar */}
                {status === 'processing' && (
                  <div style={{ width: '100%' }}>
                    <div
                      style={{
                        width: '100%',
                        height: '4px',
                        borderRadius: 'var(--radius-full)',
                        background: 'var(--glass-bg-hover)',
                        overflow: 'hidden',
                      }}
                    >
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={SPRING_SMOOTH}
                        style={{
                          height: '100%',
                          background: 'var(--color-accent)',
                          borderRadius: 'var(--radius-full)',
                        }}
                      />
                    </div>
                    <p
                      style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-muted)',
                        marginTop: '0.5rem',
                        textAlign: 'right',
                      }}
                    >
                      {Math.round(progress)}%
                    </p>
                  </div>
                )}
              </div>
            </GlassCard>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
