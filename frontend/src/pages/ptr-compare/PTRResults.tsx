import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, RotateCcw, Home, Filter, TriangleAlert } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { GlassCard } from '../../components/ui/GlassCard';
import { AnimatedCounter } from '../../components/ui/AnimatedCounter';
import { ClauseList } from '../../components/ptr';
import { ExportButton } from '../../components/shared';
import { SPRING_GENTLE, STAGGER_DELAY } from '../../constants/motion';
import type { PTRCompareResult, Clause } from '../../types/ptr';

interface PTRResultsProps {
  result: PTRCompareResult;
  taskId: string;
  generatedAtMs: number;
  onBack: () => void;
  onReupload: () => void;
  onDashboard: () => void;
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

type FilterType = 'all' | 'mismatched';

/**
 * PTRResults - Display PTR comparison results
 *
 * Features:
 * - Overview stats with animated counters
 * - Filter buttons (all / mismatched)
 * - Clause list with expandable cards
 * - Navigation buttons
 */
export function PTRResults({ result, taskId, generatedAtMs, onBack, onReupload, onDashboard }: PTRResultsProps) {
  const [filter, setFilter] = useState<FilterType>('all');
  const generatedAtText = new Date(generatedAtMs).toLocaleString('zh-CN', {
    hour12: false,
  });

  // Extract data from backend response structure
  const summary = result.summary || {
    total_clauses: 0,
    evaluated_clauses: 0,
    matches: 0,
    differs: 0,
    missing: 0,
    excluded: 0,
    match_rate: 0,
  };

  const evaluatedClauseCount = summary.evaluated_clauses ?? Math.max(summary.total_clauses - summary.excluded, 0);
  const matchPercentage = evaluatedClauseCount > 0
    ? Math.round((summary.matches / evaluatedClauseCount) * 100)
    : 0;
  const mismatchedCount = summary.differs + summary.missing;
  const outOfScopeWarning = result.warnings?.out_of_scope;
  const missingInScopeWarning = result.warnings?.missing_in_scope;

  // Transform clauses to match ClauseList component expectations
  const transformedClauses: Clause[] = (result.clauses || [])
    .filter(clause => clause.result !== 'excluded')
    .map((clause, index) => ({
      id: String(index),
      number: clause.ptr_number || '',
      title: clause.display_title || clause.ptr_text?.substring(0, 50) || '',
      ptr_text: clause.ptr_text || '',
      report_text: clause.report_text || '',
      is_match: clause.result === 'match',
      status: clause.status,
      match_reason: clause.match_reason,
      display_type: clause.display_type,
      raw_text_collapsed: clause.raw_text_collapsed,
      structured_summary: clause.structured_summary,
      structured_notice: clause.structured_notice,
      structured_rows: clause.structured_rows || [],
      table_expansions: clause.table_expansions || [],
      diffs: (clause.differences || []).map(d => ({
        type: (d.type || 'replace') as 'insert' | 'delete' | 'replace' | 'equal',
        value: d.text || '',
      })),
    }));

  const visibleClauseCount = transformedClauses.length;

  // Filter clauses
  const filteredClauses = filter === 'mismatched'
    ? transformedClauses.filter(c => !c.is_match)
    : transformedClauses;

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      style={{
        width: '100%',
        maxWidth: '900px',
        margin: '0 auto',
        padding: '2rem',
      }}
    >
      {/* Navigation */}
      <motion.div variants={itemVariants} style={{ marginBottom: '2rem' }}>
        <Button variant="ghost" onClick={onBack} style={{ gap: '0.5rem' }}>
          <ArrowLeft size={18} />
          返回
        </Button>
      </motion.div>

      {/* Header */}
      <motion.div variants={itemVariants} style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1
          style={{
            fontSize: '2rem',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: '0.5rem',
          }}
        >
          PTR 条款核对结果
        </h1>
        <p style={{ fontSize: '1rem', color: 'var(--text-secondary)' }}>
          共核对 {visibleClauseCount} 条款（范围外 {summary.excluded} 条以警告展示）
        </p>
      </motion.div>

      <motion.div variants={itemVariants} style={{ marginBottom: '1.25rem' }}>
        <GlassCard>
          <div
            style={{
              padding: '0.9rem 1.1rem',
              border: '1px solid rgba(196, 167, 108, 0.4)',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(196, 167, 108, 0.07)',
            }}
          >
            <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '0.35rem' }}>
              当前页面展示的是一次任务快照结果。后端重启、规则变更或文件变更后，需要点击“重新上传”生成新任务。
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              任务ID:
              {' '}
              <span style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace', color: 'var(--text-primary)' }}>
                {taskId}
              </span>
              {' '}· 生成时间: {generatedAtText}
            </p>
          </div>
        </GlassCard>
      </motion.div>

      {/* Stats Overview */}
      <motion.div variants={itemVariants} style={{ marginBottom: '2rem' }}>
        <GlassCard>
          <div
            style={{
              padding: '2rem',
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '2rem',
            }}
          >
            {/* Match Rate */}
            <div style={{ textAlign: 'center' }}>
              <p
                style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-muted)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                一致率
              </p>
              <div
                style={{
                  fontSize: '3rem',
                  fontWeight: 600,
                  color:
                    matchPercentage >= 90
                      ? 'var(--color-success)'
                      : matchPercentage >= 70
                      ? 'var(--color-warn)'
                      : 'var(--color-danger)',
                }}
              >
                <AnimatedCounter value={matchPercentage} formatValue={(v) => `${v}%`} />
              </div>
            </div>

            {/* Matched */}
            <div style={{ textAlign: 'center' }}>
              <p
                style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-muted)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                一致
              </p>
              <div
                style={{
                  fontSize: '2rem',
                  fontWeight: 600,
                  color: 'var(--color-success)',
                }}
              >
                <AnimatedCounter value={summary.matches} />
              </div>
            </div>

            {/* Mismatched */}
            <div style={{ textAlign: 'center' }}>
              <p
                style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-muted)',
                  marginBottom: '0.5rem',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                不一致
              </p>
              <div
                style={{
                  fontSize: '2rem',
                  fontWeight: 600,
                  color: 'var(--color-danger)',
                }}
              >
                <AnimatedCounter value={mismatchedCount} />
              </div>
            </div>
          </div>
        </GlassCard>
      </motion.div>

      {(outOfScopeWarning?.count || missingInScopeWarning?.count) ? (
        <motion.div variants={itemVariants} style={{ marginBottom: '1.5rem' }}>
          <GlassCard>
            <div
              style={{
                padding: '1rem 1.25rem',
                border: '1px solid rgba(196, 167, 108, 0.55)',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(196, 167, 108, 0.08)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                <TriangleAlert size={16} color="var(--color-warn)" />
                <span style={{ fontSize: '0.875rem', color: 'var(--color-warn)', fontWeight: 600 }}>
                  范围与缺失告警
                </span>
              </div>
              {outOfScopeWarning?.count ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: '0.5rem' }}>
                  {outOfScopeWarning.message}
                  {' '}({outOfScopeWarning.count} 条)：{outOfScopeWarning.clauses.join('、')}
                </p>
              ) : null}
              {missingInScopeWarning?.count ? (
                <p style={{ fontSize: '0.85rem', color: 'var(--color-danger)', lineHeight: 1.6 }}>
                  {missingInScopeWarning.message}
                  {' '}({missingInScopeWarning.count} 条)：{missingInScopeWarning.clauses.join('、')}
                </p>
              ) : null}
            </div>
          </GlassCard>
        </motion.div>
      ) : null}

      {/* Filter Buttons */}
      <motion.div variants={itemVariants} style={{ marginBottom: '1.5rem' }}>
        <div
          style={{
            display: 'flex',
            gap: '0.75rem',
            justifyContent: 'center',
            flexWrap: 'wrap',
          }}
        >
          <Button
            variant={filter === 'all' ? 'primary' : 'secondary'}
            onClick={() => setFilter('all')}
            style={{ gap: '0.5rem' }}
          >
            <Filter size={16} />
            全部 ({visibleClauseCount})
          </Button>
          <Button
            variant={filter === 'mismatched' ? 'primary' : 'secondary'}
            onClick={() => setFilter('mismatched')}
          >
            仅不一致 ({mismatchedCount})
          </Button>
        </div>
      </motion.div>

      {/* Clause List */}
      <motion.div variants={itemVariants}>
        <ClauseList clauses={filteredClauses} filter={filter} />
      </motion.div>

      {/* Action Buttons */}
      <motion.div
        variants={itemVariants}
        style={{
          display: 'flex',
          gap: '1rem',
          justifyContent: 'center',
          marginTop: '2rem',
          flexWrap: 'wrap',
        }}
      >
        <ExportButton
          exportUrl={`/api/ptr/${taskId}/export`}
          filename={`ptr_comparison_${taskId.slice(0, 8)}.pdf`}
          buttonText="导出 PDF"
        />
        <Button variant="secondary" onClick={onDashboard} style={{ gap: '0.5rem' }}>
          <Home size={18} />
          返回首页
        </Button>
        <Button variant="primary" onClick={onReupload} style={{ gap: '0.5rem' }}>
          <RotateCcw size={18} />
          重新上传
        </Button>
      </motion.div>
    </motion.div>
  );
}
