export interface Job {
  id: string;
  name: string;
  description: string;
  stage: string;
  video_file_count: number;
  audio_file_count: number;
  progress_percent: number;
  current_file: string | null;
  total_files: number;
  processed_files: number;
  error_message: string | null;
  otio_file_id: string | null;
  // Checkpoint IDs for resume support
  manifest_id: string | null;
  blueprint_id: string | null;
  has_style_profile: boolean;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string;
}

export interface UploadedFile {
  file_id: string;
  filename: string;
  size_bytes: number;
  content_type: string;
}

export interface FileInfo {
  file_id: string;
  filename: string;
  size_bytes: number;
  content_type: string;
  file_type: string;
}

export interface CreateJobRequest {
  name: string;
  description?: string;
}

export interface StartJobRequest {
  target_frame_rate?: number;
  style_profile_text?: string | null;
}

export interface ProgressMessage {
  job_id: string;
  stage: string;
  progress_percent: number;
  current_item: string | null;
  total_items: number;
  processed_items: number;
  message: string;
}
