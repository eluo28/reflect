import { create } from 'zustand';
import type { Job, UploadedFile } from '../types/api';

interface JobState {
  currentJob: Job | null;
  uploadedFiles: UploadedFile[];
  isLoading: boolean;
  error: string | null;

  setCurrentJob: (job: Job | null) => void;
  setUploadedFiles: (files: UploadedFile[]) => void;
  addUploadedFiles: (files: UploadedFile[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useJobStore = create<JobState>((set) => ({
  currentJob: null,
  uploadedFiles: [],
  isLoading: false,
  error: null,

  setCurrentJob: (job) => set({ currentJob: job }),
  setUploadedFiles: (files) => set({ uploadedFiles: files }),
  addUploadedFiles: (files) =>
    set((state) => ({ uploadedFiles: [...state.uploadedFiles, ...files] })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),
  reset: () =>
    set({
      currentJob: null,
      uploadedFiles: [],
      isLoading: false,
      error: null,
    }),
}));
