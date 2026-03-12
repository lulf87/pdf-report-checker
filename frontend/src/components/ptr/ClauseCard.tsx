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
  const [showRawText, setShowRawText] = useState(false);
  const isMismatch = Boolean(clause.is_failure);
  const titleText = clause.title || clause.ptr_text;
  const badgeVariant = clause.display_status_variant || (clause.is_match ? 'success' : 'danger');
  const badgeLabel = clause.display_status_label || (clause.is_match ? '一致' : '不一致');
  const structuredRows = clause.structured_rows || [];

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
                {titleText}
              </h3>
              <Badge
                variant={badgeVariant}
                pulse={!clause.is_match}
              >
                {badgeLabel}
              </Badge>
            </div>
            {clause.is_match && clause.match_reason === 'table_parameter_equivalent' && (
              <p
                style={{
                  marginTop: '0.25rem',
                  fontSize: '0.75rem',
                  color: 'var(--color-warn)',
                }}
              >
                参数条款按“应符合表中数值”判定一致，展开后可查看表格参数明细。
              </p>
            )}
            {clause.display_status_explanation && clause.display_status !== 'match' && (
              <p
                style={{
                  marginTop: '0.25rem',
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  lineHeight: 1.5,
                }}
              >
                {clause.display_status_explanation}
              </p>
            )}

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
                    {clause.display_type === 'measurement_bundle' && structuredRows.length > 0 ? (
                      <StructuredTable
                        columns={['项目', '要求', '实测', '结论']}
                        rows={structuredRows.map((row) => [
                          row.item || '-',
                          row.requirement,
                          row.actual,
                          row.result || '一致',
                        ])}
                        summary={clause.structured_summary}
                      />
                    ) : clause.display_type === 'segmented_threshold_bundle' && structuredRows.length > 0 ? (
                      <StructuredTable
                        columns={['试验段', '要求', '实测', '结论']}
                        rows={structuredRows.map((row) => [
                          row.segment || '-',
                          row.requirement,
                          row.actual,
                          row.result || '一致',
                        ])}
                        summary={clause.structured_summary}
                      />
                    ) : clause.display_type === 'out_of_scope_notice' ? (
                      <NoticeBlock
                        summary={clause.structured_summary}
                        notice={clause.structured_notice}
                      />
                    ) : (
                      <DiffViewer diffs={clause.diffs} fallbackText={formatReadableText(clause.report_text)} />
                    )}
                  </div>

                  {/* Table Expansion Details */}
                  {(clause.table_expansions && clause.table_expansions.length > 0) && (
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
                        引用表参数校对
                      </p>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        {clause.table_expansions.map((table, tableIndex) => (
                          <div
                            key={`${clause.number}-table-${table.table_number}-${tableIndex}`}
                            style={{
                              border: '1px solid var(--glass-border)',
                              borderRadius: 'var(--radius-sm)',
                              padding: '0.75rem',
                              background: 'rgba(255, 255, 255, 0.02)',
                            }}
                          >
                            <div
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                marginBottom: '0.5rem',
                                gap: '0.5rem',
                                flexWrap: 'wrap',
                              }}
                            >
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)', fontWeight: 500 }}>
                                引用表{table.table_number}
                              </span>
                              <span
                                style={{
                                  fontSize: '0.75rem',
                                  color: table.found ? 'var(--text-muted)' : 'var(--color-danger)',
                                }}
                              >
                                {table.found ? `匹配参数 ${table.matches}/${table.total_parameters}` : 'PTR 中未找到该表'}
                              </span>
                            </div>

                            {(table.parameters && table.parameters.length > 0) ? (
                              <div style={{ display: 'grid', gap: '0.75rem' }}>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                                  详情只展示本条款实际命中的技术要求表参数，不再默认展开整张表的前几行。
                                </p>
                                {table.parameters.map((param, paramIndex) => {
                                  const ptrValues = param.details?.ptr_values || {};
                                  const evidenceRows = param.details?.report_evidence_rows || [];
                                  const evidenceMeta = [
                                    {
                                      label: '来源',
                                      value: param.details?.referenced_table_label || `表${table.table_number}`,
                                    },
                                    {
                                      label: '命中参数',
                                      value: param.details?.ptr_parameter_name || param.name || '',
                                    },
                                    {
                                      label: '适用范围',
                                      value: param.details?.ptr_model_scope || '',
                                    },
                                    {
                                      label: '来源页',
                                      value: typeof param.details?.ptr_source_page === 'number'
                                        ? `第${param.details.ptr_source_page}页`
                                        : '',
                                    },
                                  ].filter((item) => item.value);
                                  return (
                                    <div
                                      key={`${clause.number}-table-${table.table_number}-param-${paramIndex}`}
                                      style={{
                                        border: '1px solid rgba(255, 255, 255, 0.08)',
                                        borderRadius: 'var(--radius-sm)',
                                        padding: '0.85rem',
                                        background: 'rgba(255, 255, 255, 0.02)',
                                        display: 'grid',
                                        gap: '0.85rem',
                                      }}
                                    >
                                      <div style={{ display: 'grid', gap: '0.35rem' }}>
                                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                          技术要求证据
                                        </p>
                                        <div
                                          style={{
                                            display: 'grid',
                                            gap: '0.45rem',
                                            padding: '0.7rem 0.8rem',
                                            border: '1px solid rgba(122, 143, 181, 0.22)',
                                            borderRadius: 'var(--radius-sm)',
                                            background: 'rgba(122, 143, 181, 0.08)',
                                          }}
                                        >
                                          {param.details?.ptr_evidence_summary && (
                                            <p style={{ fontSize: '0.84rem', color: 'var(--text-primary)', fontWeight: 600, lineHeight: 1.5 }}>
                                              {param.details.ptr_evidence_summary}
                                            </p>
                                          )}
                                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem 0.75rem' }}>
                                            {evidenceMeta.map((item) => (
                                              <span
                                                key={`${clause.number}-${paramIndex}-${item.label}`}
                                                style={{
                                                  fontSize: '0.79rem',
                                                  color: 'var(--text-secondary)',
                                                  lineHeight: 1.5,
                                                  padding: '0.18rem 0.45rem',
                                                  borderRadius: '999px',
                                                  background: 'rgba(255, 255, 255, 0.05)',
                                                  border: '1px solid rgba(255, 255, 255, 0.06)',
                                                }}
                                              >
                                                <span style={{ color: 'var(--text-muted)' }}>{item.label}：</span>
                                                {item.value}
                                              </span>
                                            ))}
                                          </div>
                                        </div>
                                        <StructuredTable
                                          columns={['参数', '适用型号/范围', '常规数值', '标准设置', '允许误差', '结论']}
                                          rows={[[
                                            param.details?.ptr_parameter_name || param.name || '-',
                                            param.details?.ptr_model_scope || '未标注',
                                            ptrValues['常规数值'] || '-',
                                            ptrValues['标准设置'] || '-',
                                            ptrValues['允许误差'] || '-',
                                            param.matches ? '一致' : '不一致',
                                          ]]}
                                        />
                                      </div>

                                      <div style={{ display: 'grid', gap: '0.35rem' }}>
                                        <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                          报告证据
                                        </p>
                                        {evidenceRows.length > 0 ? (
                                          <div style={{ display: 'grid', gap: '0.65rem' }}>
                                            {evidenceRows.map((row, rowIndex) => (
                                              <div
                                                key={`${clause.number}-report-evidence-${paramIndex}-${rowIndex}`}
                                                style={{
                                                  border: '1px solid rgba(255, 255, 255, 0.08)',
                                                  borderRadius: 'var(--radius-sm)',
                                                  padding: '0.75rem 0.85rem',
                                                  background: 'rgba(255, 255, 255, 0.03)',
                                                  display: 'grid',
                                                  gap: '0.35rem',
                                                }}
                                              >
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem', flexWrap: 'wrap' }}>
                                                  <span
                                                    style={{
                                                      fontSize: '0.72rem',
                                                      color: 'var(--text-muted)',
                                                      textTransform: 'uppercase',
                                                      letterSpacing: '0.05em',
                                                    }}
                                                  >
                                                    证据段 {rowIndex + 1}
                                                  </span>
                                                  <span
                                                    style={{
                                                      fontSize: '0.83rem',
                                                      color: 'var(--text-primary)',
                                                      fontWeight: 600,
                                                      padding: '0.16rem 0.48rem',
                                                      borderRadius: '999px',
                                                      background: 'rgba(122, 143, 181, 0.14)',
                                                    }}
                                                  >
                                                    {formatReadableText(row.label)}
                                                  </span>
                                                </div>
                                                <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                                                  {formatReadableText(row.content || param.report_value || '-')}
                                                </p>
                                              </div>
                                            ))}
                                          </div>
                                        ) : (
                                          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                                            {formatReadableText(param.report_value || '-')}
                                          </p>
                                        )}
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                                未提取到可展示的参数项。
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Raw text */}
                  <div style={{ marginBottom: '1rem' }}>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation();
                        setShowRawText((value) => !value);
                      }}
                      style={{
                        border: 'none',
                        background: 'transparent',
                        color: 'var(--color-accent)',
                        cursor: 'pointer',
                        padding: 0,
                        fontSize: '0.8rem',
                        fontWeight: 500,
                      }}
                    >
                      {showRawText ? '收起原始提取文本' : '查看原始提取文本'}
                    </button>
                    {showRawText && (
                      <div
                        style={{
                          marginTop: '0.75rem',
                          display: 'grid',
                          gap: '0.75rem',
                        }}
                      >
                        <RawTextBlock label="PTR 原始文本" text={clause.ptr_text} />
                        <RawTextBlock label="报告原始文本" text={clause.report_text} />
                      </div>
                    )}
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

function StructuredTable({
  columns,
  rows,
  summary,
}: {
  columns: string[];
  rows: string[][];
  summary?: string;
}) {
  return (
    <div style={{ display: 'grid', gap: '0.75rem' }}>
      {summary && (
        <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          {summary}
        </p>
      )}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th
                  key={column}
                  style={{
                    textAlign: 'left',
                    padding: '0.6rem',
                    borderBottom: '1px solid var(--glass-border)',
                    color: 'var(--text-muted)',
                    fontWeight: 600,
                  }}
                >
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`${row[0]}-${rowIndex}`}>
                {row.map((cell, cellIndex) => (
                  <td
                    key={`${columns[cellIndex]}-${rowIndex}`}
                    style={{
                      padding: '0.6rem',
                      borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                      color: cellIndex === 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                      verticalAlign: 'top',
                      lineHeight: 1.5,
                    }}
                  >
                    {formatReadableText(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function NoticeBlock({ summary, notice }: { summary?: string; notice?: string }) {
  return (
    <div
      style={{
        border: '1px solid rgba(196, 167, 108, 0.4)',
        borderRadius: 'var(--radius-sm)',
        padding: '0.9rem',
        background: 'rgba(196, 167, 108, 0.08)',
        display: 'grid',
        gap: '0.45rem',
      }}
    >
      {summary && <p style={{ fontSize: '0.84rem', color: 'var(--text-primary)', lineHeight: 1.6 }}>{summary}</p>}
      {notice && <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{notice}</p>}
    </div>
  );
}

function RawTextBlock({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <p
        style={{
          fontSize: '0.72rem',
          fontWeight: 600,
          color: 'var(--text-muted)',
          marginBottom: '0.4rem',
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        {label}
      </p>
      <pre
        style={{
          margin: 0,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontSize: '0.78rem',
          lineHeight: 1.55,
          color: 'var(--text-secondary)',
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px solid var(--glass-border)',
          borderRadius: 'var(--radius-sm)',
          padding: '0.75rem',
          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        }}
      >
        {formatReadableText(text)}
      </pre>
    </div>
  );
}

function formatReadableText(text: string): string {
  if (!text) {
    return '';
  }
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  const merged: string[] = [];
  for (const line of lines) {
    const previous = merged[merged.length - 1];
    if (
      previous &&
      shouldMergeReadable(previous, line)
    ) {
      merged[merged.length - 1] = `${previous}${line}`;
    } else {
      merged.push(line);
    }
  }

  return merged.join('\n');
}

function shouldMergeReadable(previous: string, current: string): boolean {
  const previousCompact = previous.replace(/\s+/g, '');
  const currentCompact = current.replace(/\s+/g, '');
  if (!previousCompact || !currentCompact) {
    return false;
  }
  const shortPrevious = previousCompact.length <= 4;
  const shortCurrent = currentCompact.length <= 4;
  const endsWithConnector = /[与及和头身柄圈端管径度力段值外内大小最手连接线]$/.test(previousCompact);
  return (shortPrevious || shortCurrent || endsWithConnector) && !/[：:。；;]$/.test(previousCompact);
}
