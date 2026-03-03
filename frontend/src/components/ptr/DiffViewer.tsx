import { motion } from 'framer-motion';
import { SPRING_GENTLE } from '../../constants/motion';
import type { DiffItem } from '../../types/ptr';

interface DiffViewerProps {
  diffs: DiffItem[];
  fallbackText?: string;
}

const diffStyles = {
  insert: {
    background: 'rgba(107, 158, 138, 0.2)',
    color: 'var(--color-success)',
    textDecoration: 'underline' as const,
  },
  delete: {
    background: 'rgba(192, 120, 120, 0.2)',
    color: 'var(--color-danger)',
    textDecoration: 'line-through' as const,
  },
  replace: {
    background: 'rgba(196, 167, 108, 0.2)',
    color: 'var(--color-warn)',
  },
  equal: {
    background: 'transparent',
    color: 'var(--text-primary)',
  },
};

/**
 * DiffViewer - Display text differences with highlighting
 *
 * Shows insertions, deletions, replacements, and equal text
 * with appropriate styling.
 */
export function DiffViewer({ diffs, fallbackText }: DiffViewerProps) {
  if (!diffs || diffs.length === 0) {
    return (
      <div
        style={{
          fontSize: '0.875rem',
          color: 'var(--text-secondary)',
          lineHeight: '1.6',
          whiteSpace: 'pre-wrap',
        }}
      >
        {fallbackText?.trim() || '（无可显示内容）'}
      </div>
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '0.25rem',
        lineHeight: '1.7',
      }}
    >
      {diffs.map((diff, index) => (
        <motion.span
          key={index}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={SPRING_GENTLE}
          style={{
            padding: '0.125rem 0.25rem',
            borderRadius: '4px',
            whiteSpace: 'pre-wrap',
            ...diffStyles[diff.type],
          }}
        >
          {diff.value}
        </motion.span>
      ))}
    </div>
  );
}
