// File types
export interface UploadedFile {
  id: string;
  name: string;
  type: 'pdf' | 'docx';
  size: number;
  path: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  errorMessage?: string;
}

// Verification result types
export type FieldStatus = 'matched' | 'mismatched' | 'missing' | 'extra';

export interface FieldResult {
  id: string;
  fieldName: string;
  tableValue: string | null;
  ocrValue: string | null;
  status: FieldStatus;
  confidence: number;
  pageNumber: number;
  tableRow?: number;
  tableCol?: string;
  imagePath?: string;
  boundingBox?: BoundingBox;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface VerificationStats {
  totalFields: number;
  matched: number;
  mismatched: number;
  missing: number;
  extra: number;
  confidence: number;
}

export interface VerificationResult {
  id: string;
  fileId: string;
  fileName: string;
  completedAt: string;
  stats: VerificationStats;
  fields: FieldResult[];
  inspectionItemCheck?: InspectionItemCheckResult; // 新增 v2.1: 检验项目核对结果
}

// UI State types
export type FilterType = 'all' | 'matched' | 'mismatched' | 'missing' | 'extra';

export interface UIState {
  currentPage: 'upload' | 'results';
  filter: FilterType;
  searchQuery: string;
  selectedFieldId: string | null;
  imagePreviewOpen: boolean;
  previewImagePath: string | null;
}

// Inspection Item Check types (新增 v2.1)
export type InspectionItemStatus = 'pass' | 'warning' | 'fail';

export interface RequirementCheck {
  requirement_text: string;
  inspection_result: string;
  remark: string;
}

export interface ClauseCheck {
  clause_number: string;
  requirements: RequirementCheck[];
  conclusion: string;
  expected_conclusion: string;
  is_conclusion_correct: boolean;
}

export interface InspectionItemCheck {
  item_number: string;
  item_name: string;
  clauses: ClauseCheck[];
  issues: string[];
  status: InspectionItemStatus;
}

export interface InspectionItemCheckResult {
  has_table: boolean;
  total_items: number;
  total_clauses: number;
  correct_conclusions: number;
  incorrect_conclusions: number;
  item_checks: InspectionItemCheck[];
  cross_page_continuations: number;
  errors: ErrorItem[];
}

export interface ErrorItem {
  code: string;
  message: string;
  level: 'error' | 'warning' | 'info';
  item_number?: string;
  clause_number?: string;
}

// App State
export interface AppState {
  files: UploadedFile[];
  currentResult: VerificationResult | null;
  isProcessing: boolean;
  progress: number;
  error: string | null;
}
