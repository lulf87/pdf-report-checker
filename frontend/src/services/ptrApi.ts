/**
 * PTR Compare API Service
 *
 * Handles API calls for PTR clause comparison.
 */

import type {
  UploadResponse,
  ProgressResponse,
  ResultResponse,
} from '../types/ptr';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Upload PTR and report PDFs for comparison
 */
export async function uploadPTRFiles(
  reportPdf: File,
  ptrPdf: File,
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('report_file', reportPdf);  // Match backend parameter name
  formData.append('ptr_file', ptrPdf);        // Match backend parameter name

  const response = await fetch(`${API_BASE_URL}/api/ptr/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    // Handle FastAPI 422 error which returns detail as array
    const errorMsg = typeof error.detail === 'string'
      ? error.detail
      : Array.isArray(error.detail)
        ? error.detail.map((e: { msg: string }) => e.msg).join('; ')
        : 'Upload failed';
    throw new Error(errorMsg);
  }

  return response.json();
}

/**
 * Poll for processing progress
 */
export async function getPTRProgress(taskId: string): Promise<ProgressResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ptr/${taskId}/progress`);

  if (!response.ok) {
    if (response.status === 404) {
      return {
        task_id: taskId,
        status: 'not_found',
        progress: 0,
        message: 'Task not found',
        error: 'Task not found',
      };
    }
    throw new Error('Failed to fetch progress');
  }

  return response.json();
}

/**
 * Get comparison results
 */
export async function getPTRResult(taskId: string): Promise<ResultResponse> {
  const response = await fetch(`${API_BASE_URL}/api/ptr/${taskId}/result`);

  if (!response.ok) {
    throw new Error('Failed to fetch results');
  }

  return response.json();
}

/**
 * Poll progress with timeout and interval
 *
 * @param taskId - Task ID to poll
 * @param onProgress - Callback for progress updates
 * @param timeout - Timeout in milliseconds (default: 60000ms)
 * @param interval - Polling interval in milliseconds (default: 1000ms)
 */
export async function pollPTRProgress(
  taskId: string,
  onProgress: (progress: ProgressResponse) => void,
  timeout: number = 60000,
  interval: number = 1000,
): Promise<ResultResponse> {
  const startTime = Date.now();

  return new Promise((resolve, reject) => {
    const poll = async () => {
      // Check timeout
      if (Date.now() - startTime > timeout) {
        reject(new Error('Polling timeout exceeded'));
        return;
      }

      try {
        const progress = await getPTRProgress(taskId);
        onProgress(progress);

        if (progress.status === 'completed') {
          const result = await getPTRResult(taskId);
          resolve(result);
        } else if (progress.status === 'not_found') {
          reject(new Error(progress.error || 'Task not found'));
        } else if (progress.status === 'error') {
          reject(new Error(progress.error || 'Processing failed'));
        } else {
          // Continue polling
          setTimeout(poll, interval);
        }
      } catch (error) {
        reject(error);
      }
    };

    // Start polling
    poll();
  });
}
