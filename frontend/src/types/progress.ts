export type PipelineStage =
  | 'idle'
  | 'uploading'
  | 'annotating'
  | 'planning'
  | 'executing'
  | 'completed'
  | 'failed';

export interface ProgressMessage {
  job_id: string;
  stage: PipelineStage;
  progress_percent: number;
  current_item: string | null;
  total_items: number;
  processed_items: number;
  message: string;
}
