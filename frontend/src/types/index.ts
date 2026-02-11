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

// App State
export interface AppState {
  files: UploadedFile[];
  currentResult: VerificationResult | null;
  isProcessing: boolean;
  progress: number;
  error: string | null;
}
