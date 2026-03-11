/**
 * PTR Compare Type Definitions
 *
 * Types for PTR clause comparison API responses and data structures.
 */

export interface UploadResponse {
  task_id: string;
  status: 'processing';
  message: string;
}

export interface ProgressResponse {
  task_id: string;
  status: 'processing' | 'completed' | 'error' | 'not_found';
  progress: number; // 0-100
  message: string;
  error?: string;
}

export interface ResultResponse {
  task_id: string;
  status: 'completed';
  result: PTRCompareResult;
}

// Summary statistics from backend
export interface ComparisonSummary {
  total_clauses: number;
  evaluated_clauses?: number;
  matches: number;
  differs: number;
  missing: number;
  excluded: number;
  match_rate: number;
}

// Backend response structure
export interface PTRCompareResult {
  summary: ComparisonSummary;
  warnings?: {
    out_of_scope?: {
      count: number;
      clauses: string[];
      message: string;
    };
    missing_in_scope?: {
      count: number;
      clauses: string[];
      message: string;
    };
  };
  clauses: ClauseResult[];  // Raw backend clause data
  tables: TableResult[];
  ptr_info?: {
    total_clauses: number;
    total_tables: number;
  };
  report_info?: {
    total_inspection_items: number;
  };
}

// Backend clause response structure
export interface ClauseResult {
  ptr_number: string;
  ptr_text: string;
  report_text: string;
  result: string;  // 'match' | 'differ' | 'missing' | 'excluded'
  similarity: number;
  status?: string;
  match_reason?: string;
  display_title?: string;
  display_type?: 'plain_text' | 'measurement_bundle' | 'segmented_threshold_bundle' | 'out_of_scope_notice';
  raw_text_collapsed?: boolean;
  structured_summary?: string;
  structured_notice?: string;
  structured_rows?: StructuredRow[];
  details?: Record<string, unknown>;
  differences?: Difference[];
  table_expansions?: ClauseTableExpansion[];
}

export interface StructuredRow {
  item?: string;
  segment?: string;
  requirement: string;
  actual: string;
  result?: string;
}

export interface ClauseTableExpansion {
  table_number: number;
  found: boolean;
  total_parameters: number;
  matches: number;
  match_rate: number;
  parameters?: TableParameter[];
}

export interface Difference {
  text: string;
  type: string;
}

// Frontend display clause structure
export interface Clause {
  id: string;
  number: string;
  title: string;
  ptr_text: string;
  report_text: string;
  is_match: boolean;
  status?: string;
  match_reason?: string;
  display_type?: ClauseResult['display_type'];
  raw_text_collapsed?: boolean;
  structured_summary?: string;
  structured_notice?: string;
  structured_rows?: StructuredRow[];
  diffs: DiffItem[];
  table_expansions?: ClauseTableExpansion[];
}

export interface TableResult {
  table_number: number;
  clause_number?: string;
  found: boolean;
  total_parameters: number;
  matches: number;
  match_rate: number;
  parameters?: TableParameter[];
}

export interface TableParameter {
  name: string;
  ptr_value: string;
  report_value: string;
  matches: boolean;
}

export type DiffType = 'insert' | 'delete' | 'replace' | 'equal';

export interface DiffItem {
  type: DiffType;
  value: string;
}

export type ProgressStatus = 'idle' | 'processing' | 'completed' | 'error';

export interface PTRUploadFiles {
  reportPdf?: FileUploadFile;
  ptrPdf?: FileUploadFile;
}

export interface FileUploadFile {
  id: string;
  name: string;
  size: number;
  file: File;
}
