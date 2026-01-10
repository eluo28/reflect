import { create } from 'zustand';
import type { PipelineStage, ProgressMessage } from '../types/progress';

interface ProgressState {
  stage: PipelineStage;
  progressPercent: number;
  currentItem: string | null;
  totalItems: number;
  processedItems: number;
  message: string;
  isProcessing: boolean;

  updateProgress: (message: ProgressMessage) => void;
  setProcessing: (processing: boolean) => void;
  reset: () => void;
}

export const useProgressStore = create<ProgressState>((set) => ({
  stage: 'idle',
  progressPercent: 0,
  currentItem: null,
  totalItems: 0,
  processedItems: 0,
  message: '',
  isProcessing: false,

  updateProgress: (message) =>
    set({
      stage: message.stage,
      progressPercent: message.progress_percent,
      currentItem: message.current_item,
      totalItems: message.total_items,
      processedItems: message.processed_items,
      message: message.message,
      isProcessing: !['idle', 'completed', 'failed'].includes(message.stage),
    }),

  setProcessing: (processing) => set({ isProcessing: processing }),

  reset: () =>
    set({
      stage: 'idle',
      progressPercent: 0,
      currentItem: null,
      totalItems: 0,
      processedItems: 0,
      message: '',
      isProcessing: false,
    }),
}));
