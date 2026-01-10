import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Sparkles, Briefcase, AlertCircle, Loader2, Film, Music, ArrowLeft, Download, FileVideo, Check, X, RotateCcw } from 'lucide-react';
import { FileUpload } from '../components/FileUpload/FileUpload';
import { ProgressTracker } from '../components/ProgressTracker/ProgressTracker';
import { DownloadButton } from '../components/DownloadButton/DownloadButton';
import { useJobStore } from '../store/jobStore';
import { useProgressStore } from '../store/progressStore';
import { startJob, getJob, listJobFiles, downloadFile, uploadStyleReference, resumeJob } from '../api/client';
import { GlassCard, Button, StatusIndicator } from '../components/ui';
import type { Job, FileInfo } from '../types/api';

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [currentJob, setCurrentJob] = useState<Job | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isStarting, setIsStarting] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [jobFiles, setJobFiles] = useState<FileInfo[]>([]);
  const [isLoadingFiles, setIsLoadingFiles] = useState(false);

  // Style reference state
  const [styleFile, setStyleFile] = useState<File | null>(null);
  const [styleStatus, setStyleStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
  const [styleMessage, setStyleMessage] = useState<string>('');
  const styleInputRef = useRef<HTMLInputElement>(null);

  const { uploadedFiles, setUploadedFiles, reset: resetJob } = useJobStore();
  const { isProcessing, reset: resetProgress } = useProgressStore();

  const hasFiles = uploadedFiles.length > 0;

  // Determine job state
  const jobStage = currentJob?.stage?.toLowerCase() || '';
  const isDraft = jobStage === 'created';
  const isJobProcessing = !['created', 'completed', 'failed', 'cancelled'].includes(jobStage);
  const isJobFailed = jobStage === 'failed';
  const hasOutput = currentJob?.otio_file_id != null;

  // Job is "done" if it has output or status indicates completion
  const isJobDone = hasOutput || jobStage === 'completed';

  // Can only upload if job is in draft state and not processing
  const canUpload = isDraft && !isProcessing && !isJobDone;
  const canStart = isDraft && hasFiles && !isProcessing && !isJobDone;

  // Show the job result view (input summary + output) when not in draft mode
  const showJobResult = !isDraft || isJobDone || isJobProcessing || isJobFailed;

  // Load job on mount and when jobId changes
  useEffect(() => {
    if (!jobId) {
      navigate('/');
      return;
    }

    const loadJob = async () => {
      setIsLoading(true);
      try {
        const job = await getJob(jobId);
        setCurrentJob(job);
        resetProgress();

        // Fetch existing files and populate the store
        const files = await listJobFiles(jobId);
        setUploadedFiles(
          files.map((f) => ({
            file_id: f.file_id,
            filename: f.filename,
            size_bytes: f.size_bytes,
            content_type: f.content_type,
          }))
        );
      } catch (error) {
        console.error('Failed to load job:', error);
        navigate('/');
      } finally {
        setIsLoading(false);
      }
    };

    loadJob();
  }, [jobId, navigate, resetProgress, setUploadedFiles]);

  // Fetch files when viewing a job with result
  useEffect(() => {
    if (currentJob && showJobResult) {
      setIsLoadingFiles(true);
      listJobFiles(currentJob.id)
        .then(setJobFiles)
        .catch((error) => console.error('Failed to fetch files:', error))
        .finally(() => setIsLoadingFiles(false));
    } else {
      setJobFiles([]);
    }
  }, [currentJob?.id, showJobResult]);

  // Poll for updates when processing
  useEffect(() => {
    if (!currentJob || (!isProcessing && !isJobProcessing)) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getJob(currentJob.id);
        setCurrentJob(updated);
      } catch (error) {
        console.error('Failed to refresh job:', error);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [currentJob, isProcessing, isJobProcessing]);

  const handleDownloadFile = (fileId: string, filename: string) => {
    downloadFile(fileId, filename);
  };

  const handleStartProcessing = async () => {
    if (!currentJob) return;

    setIsStarting(true);
    try {
      await startJob(currentJob.id, { target_frame_rate: 60 });
      // Refresh job to get updated status
      const updated = await getJob(currentJob.id);
      setCurrentJob(updated);
    } catch (error) {
      console.error('Failed to start job:', error);
    } finally {
      setIsStarting(false);
    }
  };

  const handleResumeJob = async () => {
    if (!currentJob) return;

    setIsResuming(true);
    try {
      await resumeJob(currentJob.id);
      // Refresh job to get updated status
      const updated = await getJob(currentJob.id);
      setCurrentJob(updated);
    } catch (error) {
      console.error('Failed to resume job:', error);
    } finally {
      setIsResuming(false);
    }
  };

  const handleStyleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !currentJob) return;

    if (!file.name.toLowerCase().endsWith('.otio')) {
      setStyleStatus('error');
      setStyleMessage('Please select an .otio file');
      return;
    }

    setStyleFile(file);
    setStyleStatus('uploading');
    setStyleMessage('Uploading...');

    try {
      await uploadStyleReference(currentJob.id, file);
      setStyleStatus('success');
      setStyleMessage('Style will be extracted during processing');
    } catch (error) {
      console.error('Failed to upload style reference:', error);
      setStyleStatus('error');
      setStyleMessage('Failed to upload reference');
    }
  };

  const handleRemoveStyleFile = () => {
    setStyleFile(null);
    setStyleStatus('idle');
    setStyleMessage('');
    if (styleInputRef.current) {
      styleInputRef.current.value = '';
    }
  };

  const handleBack = () => {
    resetJob();
    resetProgress();
    navigate('/');
  };

  const getStatusColor = (stage: string): 'active' | 'warning' | 'error' | 'idle' => {
    switch (stage.toLowerCase()) {
      case 'completed':
        return 'active';
      case 'failed':
      case 'cancelled':
        return 'error';
      case 'created':
        return 'idle';
      default:
        return 'warning';
    }
  };

  const getStatusLabel = (stage: string) => {
    switch (stage.toLowerCase()) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      case 'created':
        return 'Draft';
      case 'queued':
        return 'Queued';
      case 'downloading_files':
        return 'Downloading';
      case 'annotating_assets':
        return 'Analyzing';
      case 'planning_edits':
        return 'Planning';
      case 'executing_timeline':
        return 'Generating';
      case 'uploading_result':
        return 'Uploading';
      default:
        return stage;
    }
  };

  if (isLoading) {
    return (
      <GlassCard className="p-8">
        <div className="flex items-center justify-center gap-3 text-white/40">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Loading job...</span>
        </div>
      </GlassCard>
    );
  }

  if (!currentJob) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Job Header */}
      <div className="flex items-start justify-between">
        <div>
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-sm text-white/40 hover:text-white/60 transition-colors mb-3"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to jobs
          </button>
          <div className="flex items-center gap-3 mb-1">
            <Briefcase className="w-5 h-5 text-accent-cyan" />
            <h2 className="text-xl font-semibold tracking-tight">
              {currentJob.name}
            </h2>
          </div>
          <StatusIndicator
            status={getStatusColor(currentJob.stage)}
            label={getStatusLabel(currentJob.stage)}
          />
        </div>
      </div>

      {/* Content based on job status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Draft Job: Can upload files and start processing */}
        {isDraft && !showJobResult && (
          <>
            {/* File Upload */}
            <motion.div
              className="lg:col-span-2"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <GlassCard className="p-6 h-full">
                <div className="flex items-center justify-between mb-4">
                  <span className="label">Media Assets</span>
                  <span className="text-[10px] font-mono text-white/30">
                    {uploadedFiles.length} files
                  </span>
                </div>
                <FileUpload jobId={currentJob.id} disabled={!canUpload} />
              </GlassCard>
            </motion.div>

            {/* Generate Panel */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <GlassCard className="p-6 h-full flex flex-col" glow={hasFiles} glowColor="cyan">
                <span className="label mb-4">Generate</span>

                <div className="flex-1 flex flex-col justify-center">
                  {hasFiles ? (
                    <div className="text-center">
                      <div className="w-12 h-12 rounded-xl bg-accent-cyan/10 border border-accent-cyan/20 flex items-center justify-center mx-auto mb-4">
                        <Sparkles className="w-5 h-5 text-accent-cyan" />
                      </div>
                      <p className="text-sm text-white/60 mb-6">
                        Ready to generate your edit
                      </p>
                      <Button
                        onClick={handleStartProcessing}
                        disabled={!canStart || isStarting || styleStatus === 'uploading'}
                        loading={isStarting}
                        className="w-full"
                        glow
                      >
                        {isStarting ? 'Starting...' : 'Generate Edit'}
                      </Button>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <p className="text-sm text-white/30">
                        Upload media files to begin
                      </p>
                    </div>
                  )}
                </div>

                {/* Style Reference Upload - Always visible */}
                <div className="mt-4 pt-4 border-t border-white/[0.06]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                      Style Reference
                    </span>
                    <span className="text-[10px] text-white/30">Optional</span>
                  </div>

                  {!styleFile ? (
                    <label className="flex items-center justify-center gap-2 p-3 rounded-lg border border-dashed border-white/[0.1] hover:border-white/[0.2] cursor-pointer transition-colors group">
                      <FileVideo className="w-4 h-4 text-white/30 group-hover:text-white/50" />
                      <span className="text-xs text-white/40 group-hover:text-white/60">
                        Upload .otio for style
                      </span>
                      <input
                        ref={styleInputRef}
                        type="file"
                        accept=".otio"
                        onChange={handleStyleFileSelect}
                        className="hidden"
                      />
                    </label>
                  ) : (
                    <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          {styleStatus === 'uploading' && (
                            <Loader2 className="w-4 h-4 text-accent-cyan animate-spin flex-shrink-0" />
                          )}
                          {styleStatus === 'success' && (
                            <Check className="w-4 h-4 text-green-400 flex-shrink-0" />
                          )}
                          {styleStatus === 'error' && (
                            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                          )}
                          <span className="text-xs text-white/60 truncate">
                            {styleFile.name}
                          </span>
                        </div>
                        <button
                          onClick={handleRemoveStyleFile}
                          className="p-1 rounded hover:bg-white/[0.05] text-white/30 hover:text-white/60 transition-colors flex-shrink-0"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                      {styleMessage && (
                        <p className={`text-[10px] mt-1 ${
                          styleStatus === 'success' ? 'text-green-400/70' :
                          styleStatus === 'error' ? 'text-red-400/70' : 'text-white/40'
                        }`}>
                          {styleMessage}
                        </p>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-white/[0.06] grid grid-cols-2 gap-4">
                  <div>
                    <span className="label">Videos</span>
                    <p className="text-lg font-mono text-white/80 mt-1">
                      {uploadedFiles.filter(f => f.content_type.startsWith('video/')).length}
                    </p>
                  </div>
                  <div>
                    <span className="label">Audio</span>
                    <p className="text-lg font-mono text-white/80 mt-1">
                      {uploadedFiles.filter(f => f.content_type.startsWith('audio/')).length}
                    </p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          </>
        )}

        {/* Processing/Completed/Failed: Show input summary and progress/output */}
        {showJobResult && (
          <>
            {/* Input Summary */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <GlassCard className="p-6 h-full">
                <span className="label mb-4 block">Input Files</span>

                {isLoadingFiles ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 text-white/40 animate-spin" />
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Video Files */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Film className="w-3 h-3 text-accent-cyan" />
                        <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                          Video ({jobFiles.filter(f => f.file_type === 'video_clip').length})
                        </span>
                      </div>
                      <div className="space-y-1">
                        {jobFiles
                          .filter(f => f.file_type === 'video_clip')
                          .map((file) => (
                            <div
                              key={file.file_id}
                              className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04] group hover:border-white/[0.08] transition-colors"
                            >
                              <span className="text-xs text-white/60 truncate flex-1 mr-2">
                                {file.filename}
                              </span>
                              <button
                                onClick={() => handleDownloadFile(file.file_id, file.filename)}
                                className="p-1 rounded hover:bg-white/[0.05] text-white/30 hover:text-accent-cyan transition-colors"
                                title="Download file"
                              >
                                <Download className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        {jobFiles.filter(f => f.file_type === 'video_clip').length === 0 && (
                          <p className="text-xs text-white/20 py-2">No video files</p>
                        )}
                      </div>
                    </div>

                    {/* Audio Files */}
                    <div>
                      <div className="flex items-center gap-2 mb-2">
                        <Music className="w-3 h-3 text-accent-amber" />
                        <span className="text-[10px] font-mono text-white/40 uppercase tracking-wider">
                          Audio ({jobFiles.filter(f => f.file_type === 'audio_clip').length})
                        </span>
                      </div>
                      <div className="space-y-1">
                        {jobFiles
                          .filter(f => f.file_type === 'audio_clip')
                          .map((file) => (
                            <div
                              key={file.file_id}
                              className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04] group hover:border-white/[0.08] transition-colors"
                            >
                              <span className="text-xs text-white/60 truncate flex-1 mr-2">
                                {file.filename}
                              </span>
                              <button
                                onClick={() => handleDownloadFile(file.file_id, file.filename)}
                                className="p-1 rounded hover:bg-white/[0.05] text-white/30 hover:text-accent-amber transition-colors"
                                title="Download file"
                              >
                                <Download className="w-3 h-3" />
                              </button>
                            </div>
                          ))}
                        {jobFiles.filter(f => f.file_type === 'audio_clip').length === 0 && (
                          <p className="text-xs text-white/20 py-2">No audio files</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-white/[0.06]">
                  <p className="text-[10px] font-mono text-white/30">
                    Total: {jobFiles.length} files
                  </p>
                </div>
              </GlassCard>
            </motion.div>

            {/* Progress/Output Panel */}
            <motion.div
              className="lg:col-span-2"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <GlassCard
                className="p-6"
                glow={isJobProcessing || isProcessing}
                glowColor={hasOutput ? 'amber' : 'cyan'}
              >
                {(isJobProcessing || isProcessing) && (
                  <>
                    <ProgressTracker
                      jobId={currentJob.id}
                      isStuck={isJobProcessing && !isProcessing}
                      hasManifest={currentJob.manifest_id != null}
                      hasBlueprint={currentJob.blueprint_id != null}
                    />
                    {/* Show Resume button for stuck jobs (processing stage but no active progress) */}
                    {isJobProcessing && !isProcessing && (
                      <div className="mt-4 pt-4 border-t border-white/[0.06]">
                        <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/10 border border-amber-500/20">
                          <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm text-amber-400 font-medium">Job appears stuck</p>
                            <p className="text-xs text-amber-400/70 mt-1">
                              The server may have been restarted. Click Resume to continue from the last checkpoint.
                            </p>
                            <Button
                              onClick={handleResumeJob}
                              disabled={isResuming}
                              loading={isResuming}
                              className="mt-3"
                              size="sm"
                            >
                              <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
                              {isResuming ? 'Resuming...' : 'Resume Job'}
                            </Button>
                          </div>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {(isJobDone || hasOutput) && !isProcessing && (
                  <DownloadButton jobId={currentJob.id} />
                )}

                {isJobFailed && !isProcessing && (
                  <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <p className="text-sm text-red-400 font-medium">Processing Failed</p>
                      <p className="text-xs text-red-400/70 mt-1">
                        {currentJob.error_message || 'The job encountered an error. Please try creating a new job.'}
                      </p>
                    </div>
                  </div>
                )}
              </GlassCard>
            </motion.div>
          </>
        )}
      </div>
    </div>
  );
}
