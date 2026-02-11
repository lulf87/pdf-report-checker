import { create } from 'zustand';
import type {
  UploadedFile,
  VerificationResult,
  FilterType,
} from '../types';

interface AppState {
  // Files
  files: UploadedFile[];
  addFile: (file: UploadedFile) => void;
  removeFile: (id: string) => void;
  updateFileStatus: (
    id: string,
    status: UploadedFile['status'],
    errorMessage?: string
  ) => void;
  clearFiles: () => void;

  // Verification
  currentResult: VerificationResult | null;
  isProcessing: boolean;
  progress: number;
  setProcessing: (processing: boolean) => void;
  setProgress: (progress: number) => void;
  setResult: (result: VerificationResult | null) => void;

  // UI State
  filter: FilterType;
  searchQuery: string;
  selectedFieldId: string | null;
  imagePreviewOpen: boolean;
  previewImagePath: string | null;
  setFilter: (filter: FilterType) => void;
  setSearchQuery: (query: string) => void;
  selectField: (id: string | null) => void;
  openImagePreview: (path: string) => void;
  closeImagePreview: () => void;

  // Error
  error: string | null;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Files
  files: [],
  addFile: (file) =>
    set((state) => ({
      files: [...state.files, file],
    })),
  removeFile: (id) =>
    set((state) => ({
      files: state.files.filter((f) => f.id !== id),
    })),
  updateFileStatus: (id, status, errorMessage) =>
    set((state) => ({
      files: state.files.map((f) =>
        f.id === id ? { ...f, status, errorMessage } : f
      ),
    })),
  clearFiles: () => set({ files: [] }),

  // Verification
  currentResult: null,
  isProcessing: false,
  progress: 0,
  setProcessing: (processing) => set({ isProcessing: processing }),
  setProgress: (progress) => set({ progress }),
  setResult: (result) => set({ currentResult: result }),

  // UI State
  filter: 'all',
  searchQuery: '',
  selectedFieldId: null,
  imagePreviewOpen: false,
  previewImagePath: null,
  setFilter: (filter) => set({ filter }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  selectField: (id) => set({ selectedFieldId: id }),
  openImagePreview: (path) =>
    set({ imagePreviewOpen: true, previewImagePath: path }),
  closeImagePreview: () =>
    set({ imagePreviewOpen: false, previewImagePath: null }),

  // Error
  error: null,
  setError: (error) => set({ error }),
}));
