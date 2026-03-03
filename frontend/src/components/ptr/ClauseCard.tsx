import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { SPRING_SMOOTH, EXIT_TRANSITION } from '../../constants/motion';
import { GlassCard } from '../ui/GlassCard';
import { Badge } from '../ui/Badge';
import { DiffViewer } from './DiffViewer';
import type { Clause } from '../../types/ptr';

interface ClauseCardProps {
  clause: Clause;
  index: number;
}

/**
 * ClauseCard - Expandable clause comparison card
 *
 * Features:
 * - Collapsed state: number, title, status badge
 * - Expanded state: PTR text, report text, diff highlights
 * - Smooth layout animation with layoutId
 */
export function ClauseCard({ clause, index }: ClauseCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isMismatch = !clause.is_match;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ ...SPRING_SMOOTH, delay: index * 0.03 }}
      style={{ marginBottom: '1rem' }}
    >
      <GlassCard
        hover={!isExpanded}
        style={{
          cursor: 'pointer',
          transition: 'background 150ms ease',
          background: isMismatch
            ? 'linear-gradient(135deg, rgba(192, 120, 120, 0.14), rgba(255, 255, 255, 0.03))'
            : undefined,
          border: isMismatch ? '1px solid rgba(192, 120, 120, 0.72)' : undefined,
          boxShadow: isMismatch
            ? '0 0 0 1px rgba(192, 120, 120, 0.12), 0 12px 28px rgba(192, 120, 120, 0.16)'
            : undefined,
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div
          style={{
            padding: '1.5rem',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '1rem',
          }}
        >
          {/* Expand Icon */}
          <motion.div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginTop: '0.25rem',
              color: 'var(--text-muted)',
            }}
            animate={{ rotate: isExpanded ? 90 : 0 }}
            transition={SPRING_SMOOTH}
          >
            <ChevronRight size={20} />
          </motion.div>

          {/* Content */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* Header */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                marginBottom: '0.5rem',
                flexWrap: 'wrap',
              }}
            >
              <span
                style={{
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--color-accent)',
                }}
              >
                {clause.number}
              </span>
              <h3
                style={{
                  fontSize: '1rem',
                  fontWeight: 500,
                  color: isMismatch ? 'var(--color-danger)' : 'var(--text-primary)',
                  flex: 1,
                }}
              >
                {clause.title}
              </h3>
              <Badge
                variant={clause.is_match ? 'success' : 'danger'}
                pulse={!clause.is_match}
              >
                {clause.is_match ? '一致' : '不一致'}
              </Badge>
            </div>

            {/* Expanded Content */}
            <AnimatePresence mode="wait">
              {isExpanded && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={EXIT_TRANSITION}
                  style={{
                    marginTop: '1rem',
                    paddingTop: '1rem',
                    borderTop: '1px solid var(--glass-border)',
                  }}
                >
                  {/* PTR Text */}
                  <div style={{ marginBottom: '1rem' }}>
                    <p
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                        marginBottom: '0.5rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}
                    >
                      PTR 原文
                    </p>
                    <p
                      style={{
                        fontSize: '0.875rem',
                        color: 'var(--text-secondary)',
                        lineHeight: '1.6',
                      }}
                    >
                      {clause.ptr_text}
                    </p>
                  </div>

                  {/* Report Text */}
                  <div style={{ marginBottom: '1rem' }}>
                    <p
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        color: 'var(--text-muted)',
                        marginBottom: '0.5rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                      }}
                    >
                      检验报告
                    </p>
                    <DiffViewer diffs={clause.diffs} fallbackText={clause.report_text} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </GlassCard>
    </motion.div>
  );
}
