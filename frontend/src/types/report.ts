/**
 * Types for Report Self-Check functionality
 */

// Check status enum
export type CheckStatus = 'PASS' | 'FAIL' | 'WARN' | 'SKIP';

// Error level enum
export type ErrorLevel = 'ERROR' | 'WARN' | 'INFO';

// Individual check result
export interface CheckResult {
  code: string; // C01, C02, etc.
  name: string;
  status: CheckStatus;
  level: ErrorLevel;
  message?: string;
  details?: Record<string, unknown>;
}

// Statistics summary
export interface CheckStatistics {
  total: number;
  passed: number;
  failed: number;
  warnings: number;
}

// Full report check result
export interface ReportCheckResult {
  task_id: string;
  status: 'completed' | 'error' | 'processing';
  statistics: CheckStatistics;
  checks: CheckResult[];
  summary?: string;
  error?: string;
}

// Progress response
export interface ReportProgressResponse {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'error' | 'not_found';
  progress: number;
  message?: string;
}

// Upload response
export interface ReportUploadResponse {
  task_id: string;
  status: 'pending' | 'processing';
  message?: string;
}
