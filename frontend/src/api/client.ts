import type {
  Job,
  UploadedFile,
  FileInfo,
  CreateJobRequest,
  StartJobRequest
} from '../types/api';

const API_BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Request failed');
  }
  return response.json();
}

// Jobs
export async function createJob(data: CreateJobRequest): Promise<Job> {
  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<Job>(response);
}

export async function getJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  return handleResponse<Job>(response);
}

export async function listJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE}/jobs`);
  return handleResponse<Job[]>(response);
}

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`, {
    method: 'DELETE',
  });
  await handleResponse<{ status: string }>(response);
}

// Files
export interface FileUploadProgress {
  fileIndex: number;
  fileName: string;
  percent: number;
  status: 'pending' | 'uploading' | 'processing' | 'complete' | 'error';
}

export interface UploadProgressCallback {
  (progress: FileUploadProgress[]): void;
}

async function uploadSingleFile(
  jobId: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append('files', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText);
          resolve(response[0]); // Single file returns array with one item
        } catch {
          reject(new ApiError(xhr.status, 'Invalid JSON response'));
        }
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new ApiError(xhr.status, error.detail || 'Upload failed'));
        } catch {
          reject(new ApiError(xhr.status, 'Upload failed'));
        }
      }
    });

    xhr.addEventListener('error', () => {
      reject(new ApiError(0, 'Network error during upload'));
    });

    xhr.open('POST', `${API_BASE}/jobs/${jobId}/files`);
    xhr.send(formData);
  });
}

export async function uploadFiles(
  jobId: string,
  files: File[],
  onProgress?: UploadProgressCallback
): Promise<UploadedFile[]> {
  const results: UploadedFile[] = [];

  // Initialize progress state for all files
  const progressState: FileUploadProgress[] = files.map((file, index) => ({
    fileIndex: index,
    fileName: file.name,
    percent: 0,
    status: 'pending' as const,
  }));

  onProgress?.(progressState);

  // Upload files sequentially for accurate per-file progress
  for (let i = 0; i < files.length; i++) {
    const file = files[i];

    // Mark current file as uploading
    progressState[i].status = 'uploading';
    onProgress?.(progressState);

    try {
      const result = await uploadSingleFile(jobId, file, (percent) => {
        progressState[i].percent = percent;
        if (percent === 100) {
          progressState[i].status = 'processing';
        }
        onProgress?.(progressState);
      });

      // Mark as complete
      progressState[i].status = 'complete';
      progressState[i].percent = 100;
      onProgress?.(progressState);

      results.push(result);
    } catch (error) {
      progressState[i].status = 'error';
      onProgress?.(progressState);
      throw error;
    }
  }

  return results;
}

export async function downloadOtioFile(jobId: string): Promise<Blob> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/download`);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new ApiError(response.status, error.detail || 'Download failed');
  }

  return response.blob();
}

export async function listJobFiles(jobId: string): Promise<FileInfo[]> {
  const response = await fetch(`${API_BASE}/files/list/${jobId}`);
  return handleResponse<FileInfo[]>(response);
}

export function downloadFile(fileId: string, filename: string): void {
  const a = document.createElement('a');
  a.href = `${API_BASE}/files/download/${fileId}`;
  a.download = filename;
  a.click();
}

// Style Reference
export interface StyleReferenceResponse {
  status: string;
  message: string;
  reference_file_id: string;
}

export async function uploadStyleReference(
  jobId: string,
  file: File
): Promise<StyleReferenceResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/jobs/${jobId}/style-reference`, {
    method: 'POST',
    body: formData,
  });

  return handleResponse<StyleReferenceResponse>(response);
}

// Job Processing
export async function startJob(jobId: string, data?: StartJobRequest): Promise<Job> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data || {}),
  });
  return handleResponse<Job>(response);
}

export async function cancelJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
  await handleResponse<{ status: string }>(response);
}

export async function resumeJob(jobId: string): Promise<Job> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/resume`, {
    method: 'POST',
  });
  return handleResponse<Job>(response);
}
