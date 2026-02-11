import type { FieldStatus } from '../types';

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function getStatusColor(status: FieldStatus): string {
  const colorMap: Record<FieldStatus, string> = {
    matched: '#10B981',
    mismatched: '#EF4444',
    missing: '#F59E0B',
    extra: '#6B7280',
  };
  return colorMap[status];
}

export function getStatusBgColor(status: FieldStatus): string {
  const colorMap: Record<FieldStatus, string> = {
    matched: '#D1FAE5',
    mismatched: '#FEE2E2',
    missing: '#FEF3C7',
    extra: '#F3F4F6',
  };
  return colorMap[status];
}

export function getStatusText(status: FieldStatus): string {
  const textMap: Record<FieldStatus, string> = {
    matched: '一致',
    mismatched: '不一致',
    missing: '缺失',
    extra: '额外',
  };
  return textMap[status];
}

export function formatConfidence(confidence: number): string {
  return `${(confidence * 100).toFixed(1)}%`;
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 15);
}
