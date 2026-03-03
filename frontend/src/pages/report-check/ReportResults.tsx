import { useState } from 'react';
import { motion } from 'framer-motion';
import { CheckCircle, ChevronDown, ChevronUp, AlertTriangle, ArrowLeft, RotateCcw, XCircle } from 'lucide-react';
import { GlassCard } from '../../components/ui/GlassCard';
import { Button } from '../../components/ui/Button';
import { AnimatedCounter } from '../../components/ui/AnimatedCounter';
import { Badge } from '../../components/ui/Badge';
import { ExportButton } from '../../components/shared';
import { SPRING_GENTLE, STAGGER_DELAY } from '../../constants/motion';
import type { CheckResult, ReportCheckResult } from '../../types/report';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ReportResultsProps {
  result: ReportCheckResult;
  onReupload: () => void;
  onDashboard: () => void;
}

export function ReportResults({ result, onReupload, onDashboard }: ReportResultsProps) {
  const stats = result.statistics || { total: 0, passed: 0, failed: 0, warnings: 0 };
  const checks = result.checks || [];

  const fieldChecks = checks.filter((c) => ['C01', 'C02', 'C03'].includes(c.code));
  const sampleChecks = checks.filter((c) => ['C04', 'C05', 'C06'].includes(c.code));
  const inspectionChecks = checks.filter((c) => ['C07', 'C08', 'C09', 'C10'].includes(c.code));
  const pageChecks = checks.filter((c) => c.code === 'C11');

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={SPRING_GENTLE}
      style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, color: 'var(--text-primary)' }}>核对结果</h1>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <ExportButton
            exportUrl={`${API_BASE_URL}/api/report/${result.task_id}/export`}
            filename={`report_check_${result.task_id.slice(0, 8)}.pdf`}
            buttonText="导出 PDF"
          />
          <Button variant="secondary" onClick={onDashboard}>
            <ArrowLeft size={16} style={{ marginRight: '0.5rem' }} />
            返回首页
          </Button>
          <Button variant="primary" onClick={onReupload}>
            <RotateCcw size={16} style={{ marginRight: '0.5rem' }} />
            重新上传
          </Button>
        </div>
      </div>

      <GlassCard style={{ marginBottom: '2rem' }}>
        <div style={{ padding: '1.5rem', display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          <StatItem label="总项目" value={stats.total} color="var(--color-info)" />
          <StatItem label="通过" value={stats.passed} color="var(--color-success)" />
          <StatItem label="失败" value={stats.failed} color="var(--color-danger)" />
          <StatItem label="警告" value={stats.warnings} color="var(--color-warn)" />
        </div>
      </GlassCard>

      {fieldChecks.length > 0 && <CheckCategory title="字段核对 (C01-C03)" description="首页/第三页字段一致性核对" checks={fieldChecks} />}
      {sampleChecks.length > 0 && <CheckCategory title="样品描述核对 (C04-C06)" description="样品描述表格、照片覆盖、标签覆盖核对" checks={sampleChecks} />}
      {inspectionChecks.length > 0 && <CheckCategory title="检验项目核对 (C07-C10)" description="单项结论、非空字段、序号连续性、续表标记核对" checks={inspectionChecks} />}
      {pageChecks.length > 0 && <CheckCategory title="页码核对 (C11)" description="页码连续性核对" checks={pageChecks} />}
    </motion.div>
  );
}

function StatItem({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <span style={{ fontSize: '2rem', fontWeight: 700, color, fontVariantNumeric: 'tabular-nums' }}>
        <AnimatedCounter value={value} />
      </span>
      <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginTop: '0.25rem' }}>{label}</div>
    </div>
  );
}

function CheckCategory({
  title,
  description,
  checks,
}: {
  title: string;
  description: string;
  checks: CheckResult[];
}) {
  return (
    <GlassCard style={{ marginBottom: '1.5rem' }}>
      <div style={{ padding: '1.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>{title}</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1rem' }}>{description}</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {checks.map((check, index) => (
            <CheckRow key={check.code} check={check} delay={index * STAGGER_DELAY} />
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

function CheckRow({ check, delay }: { check: CheckResult; delay: number }) {
  const [expanded, setExpanded] = useState(false);
  const rowTone = getStatusTone(check.status);
  const isFail = rowTone === 'fail';
  const isWarn = rowTone === 'warn';

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, ...SPRING_GENTLE }}
      style={{
        padding: '1rem',
        background: isFail
          ? 'linear-gradient(135deg, rgba(192, 120, 120, 0.16), rgba(255, 255, 255, 0.02))'
          : isWarn
          ? 'linear-gradient(135deg, rgba(196, 167, 108, 0.14), rgba(255, 255, 255, 0.02))'
          : 'var(--glass-bg)',
        borderRadius: '8px',
        border: isFail
          ? '1px solid rgba(192, 120, 120, 0.75)'
          : isWarn
          ? '1px solid rgba(196, 167, 108, 0.7)'
          : '1px solid var(--glass-border)',
        boxShadow: isFail
          ? '0 0 0 1px rgba(192, 120, 120, 0.15), 0 12px 28px rgba(192, 120, 120, 0.18)'
          : undefined,
      }}
    >
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {check.status === 'PASS' ? (
            <CheckCircle size={20} style={{ color: 'var(--color-success)' }} />
          ) : check.status === 'WARN' ? (
            <AlertTriangle size={20} style={{ color: 'var(--color-warn)' }} />
          ) : (
            <XCircle size={20} style={{ color: 'var(--color-danger)' }} />
          )}
          <div>
            <div style={{ fontWeight: 500, color: isFail ? 'var(--color-danger)' : 'var(--text-primary)' }}>
              {check.code}: {check.name}
            </div>
            {check.message && (
              <div
                style={{
                  fontSize: '0.85rem',
                  color: isFail ? 'rgba(255, 175, 175, 0.95)' : 'var(--text-secondary)',
                  marginTop: '0.25rem',
                }}
              >
                {check.message}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Badge variant={check.status === 'PASS' ? 'success' : check.status === 'WARN' ? 'warn' : 'danger'} pulse={check.status !== 'PASS'}>
            {check.status === 'PASS' ? '通过' : check.status === 'WARN' ? '警告' : '失败'}
          </Badge>
          {expanded ? <ChevronUp size={18} color="var(--text-secondary)" /> : <ChevronDown size={18} color="var(--text-secondary)" />}
        </div>
      </div>

      {expanded && check.details && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            borderRadius: '8px',
            background: isFail ? 'rgba(192, 120, 120, 0.08)' : 'rgba(255,255,255,0.02)',
            border: isFail ? '1px solid rgba(192, 120, 120, 0.5)' : '1px solid var(--glass-border)',
          }}
        >
          <CheckDetailsView code={check.code} details={check.details} />
        </div>
      )}
    </motion.div>
  );
}

function CheckDetailsView({ code, details }: { code: string; details: Record<string, unknown> }) {
  const rows = [...toRecordArray(details.results), ...toRecordArray(details.field_results)];
  const nestedDetails = isRecord(details.details) ? details.details : null;

  const summaryEntries = toEntries(details, ['name', 'status', 'message', 'error_count', 'results', 'field_results', 'details']);
  const nestedEntries = nestedDetails ? toEntries(nestedDetails) : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {summaryEntries.length > 0 && <KeyValueList title="摘要" entries={summaryEntries} />}
      {nestedEntries.length > 0 && <KeyValueList title="详情" entries={nestedEntries} />}
      {rows.length > 0 && <ResultRows title={`${code} 明细`} rows={rows} />}
      {summaryEntries.length === 0 && nestedEntries.length === 0 && rows.length === 0 && (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>暂无可展示明细</div>
      )}
    </div>
  );
}

function KeyValueList({ title, entries }: { title: string; entries: Array<{ key: string; value: string }> }) {
  return (
    <div>
      <div
        style={{
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          marginBottom: '0.5rem',
        }}
      >
        {title}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '0.5rem 0.75rem' }}>
        {entries.map((entry) => (
          <div key={`${title}-${entry.key}`} style={{ display: 'contents' }}>
            <div
              style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}
            >
              {toDisplayLabel(entry.key)}
            </div>
            <div
              style={{
                color: getValueColor(entry.key, entry.value),
                fontSize: '0.85rem',
                wordBreak: 'break-word',
                fontWeight: isFailureValue(entry.key, entry.value) ? 600 : 400,
              }}
            >
              {entry.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultRows({ title, rows }: { title: string; rows: Array<Record<string, unknown>> }) {
  const maxRows = 20;
  const previewRows = rows.slice(0, maxRows);
  const columns = [
    'sequence_number',
    'inspection_project',
    'component_name',
    'field_name',
    'status',
    'message',
    'expected_conclusion',
    'actual_conclusion',
    'empty_fields',
  ].filter((key) => previewRows.some((row) => row[key] !== undefined));

  if (columns.length === 0) {
    return <KeyValueList title={title} entries={[{ key: 'rows', value: `共 ${rows.length} 条` }]} />;
  }

  return (
    <div>
      <div
        style={{
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.04em',
          marginBottom: '0.5rem',
        }}
      >
        {title}（共 {rows.length} 条）
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: '340px', overflowY: 'auto' }}>
        {previewRows.map((row, index) => (
          (() => {
            const tone = getRecordTone(row);
            const isFailRow = tone === 'fail';
            const isWarnRow = tone === 'warn';
            return (
          <div
            key={`${title}-${index}`}
            style={{
              padding: '0.625rem',
              borderRadius: '6px',
              background: isFailRow
                ? 'rgba(192, 120, 120, 0.16)'
                : isWarnRow
                ? 'rgba(196, 167, 108, 0.14)'
                : 'rgba(255,255,255,0.02)',
              border: isFailRow
                ? '1px solid rgba(192, 120, 120, 0.75)'
                : isWarnRow
                ? '1px solid rgba(196, 167, 108, 0.7)'
                : '1px solid var(--glass-border)',
              display: 'grid',
              gridTemplateColumns: '130px 1fr',
              gap: '0.35rem 0.6rem',
            }}
          >
            {columns.map((column) => (
              <div key={`${title}-${index}-${column}`} style={{ display: 'contents' }}>
                <div
                  style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}
                >
                  {toDisplayLabel(column)}
                </div>
                <div
                  style={{
                    color: getCellColor(column, row[column]),
                    fontSize: '0.8rem',
                    lineHeight: 1.5,
                    wordBreak: 'break-word',
                    fontWeight: isFailureValue(column, formatValue(row[column])) ? 600 : 400,
                  }}
                >
                  {formatValue(row[column])}
                </div>
              </div>
            ))}
          </div>
            );
          })()
        ))}
      </div>
      {rows.length > maxRows && (
        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          为保证可读性，仅展示前 {maxRows} 条。完整明细请使用“导出 PDF”查看。
        </div>
      )}
    </div>
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function toRecordArray(value: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is Record<string, unknown> => isRecord(item));
}

function toEntries(
  details: Record<string, unknown>,
  skipKeys: string[] = [],
): Array<{ key: string; value: string }> {
  const skip = new Set(skipKeys);
  return Object.entries(details)
    .filter(([key, value]) => !skip.has(key) && value !== undefined && value !== null)
    .map(([key, value]) => ({ key, value: formatValue(value) }));
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (typeof value === 'string') {
    const statusMap: Record<string, string> = {
      pass: '通过',
      error: '失败',
      warning: '警告',
      skipped: '跳过',
    };
    const mapped = statusMap[value.toLowerCase()];
    if (mapped) return mapped;
    return value;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return '[]';
    const preview = value.slice(0, 8).map((item) => {
      if (typeof item === 'string' || typeof item === 'number' || typeof item === 'boolean') {
        return String(item);
      }
      if (Array.isArray(item)) {
        return item.map((part) => String(part)).join(' / ');
      }
      if (isRecord(item)) {
        return Object.entries(item)
          .map(([k, v]) => `${toDisplayLabel(k)}: ${String(v)}`)
          .join('；');
      }
      return String(item);
    });
    const suffix = value.length > 8 ? ` …（共${value.length}项）` : '';
    return `${preview.join('，')}${suffix}`;
  }
  if (isRecord(value)) {
    const parts = Object.entries(value).map(([k, v]) => `${toDisplayLabel(k)}: ${formatValue(v)}`);
    return parts.join('；');
  }
  return String(value);
}

function toDisplayLabel(key: string): string {
  const map: Record<string, string> = {
    sequence_number: '序号',
    inspection_project: '检验项目',
    component_name: '部件名称',
    field_name: '字段',
    status: '状态',
    message: '说明',
    expected_conclusion: '期望结论',
    actual_conclusion: '实际结论',
    empty_fields: '空字段',
    error_count: '错误数量',
    first_number: '起始序号',
    last_number: '结束序号',
    missing_numbers: '缺失序号',
    duplicate_numbers: '重复序号',
    missing_markers: '缺少续标记',
    extra_markers: '多余续标记',
    wrong_markers: '续字位置错误',
    total_pages_checked: '检查页数',
    total_inconsistent: '总页数不一致',
    final_page_mismatch: '末页不一致',
  };
  return map[key] || key;
}

type StatusTone = 'pass' | 'warn' | 'fail' | 'neutral';

function getStatusTone(value: unknown): StatusTone {
  if (typeof value !== 'string') return 'neutral';
  const normalized = value.trim().toLowerCase();
  if (['pass', '通过', '一致', 'ok'].includes(normalized)) return 'pass';
  if (['warn', 'warning', '警告'].includes(normalized)) return 'warn';
  if (['fail', 'error', 'failed', '失败', '不一致', '不符合'].includes(normalized)) return 'fail';
  return 'neutral';
}

function isFailureValue(key: string, value: string): boolean {
  const tone = getStatusTone(value);
  if (key === 'status') return tone === 'fail';
  return /(失败|不一致|不符合|为空|未找到|缺少|错误)/.test(value);
}

function getValueColor(key: string, value: string): string {
  if (isFailureValue(key, value)) return 'var(--color-danger)';
  const tone = getStatusTone(value);
  if (tone === 'pass') return 'var(--color-success)';
  if (tone === 'warn') return 'var(--color-warn)';
  return 'var(--text-secondary)';
}

function getRecordTone(row: Record<string, unknown>): StatusTone {
  const direct = getStatusTone(row.status);
  if (direct !== 'neutral') return direct;
  const message = formatValue(row.message);
  if (/(失败|不一致|不符合|为空|未找到|缺少|错误)/.test(message)) return 'fail';
  return 'neutral';
}

function getCellColor(column: string, value: unknown): string {
  const formatted = formatValue(value);
  if (isFailureValue(column, formatted)) return 'var(--color-danger)';
  if (column === 'status') {
    const tone = getStatusTone(value);
    if (tone === 'pass') return 'var(--color-success)';
    if (tone === 'warn') return 'var(--color-warn)';
  }
  return 'var(--text-secondary)';
}
