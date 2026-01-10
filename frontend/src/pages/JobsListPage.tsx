import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, Briefcase, Clock, CheckCircle, AlertCircle, Loader2, Film, Music, Download, Trash2, Plus } from 'lucide-react';
import { createJob, listJobs, deleteJob } from '../api/client';
import { GlassCard, Button } from '../components/ui';
import type { Job } from '../types/api';

export function JobsListPage() {
  const navigate = useNavigate();
  const [jobName, setJobName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [existingJobs, setExistingJobs] = useState<Job[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(true);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);

  // Fetch existing jobs on mount
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const jobs = await listJobs();
        setExistingJobs(jobs);
      } catch (error) {
        console.error('Failed to fetch jobs:', error);
      } finally {
        setIsLoadingJobs(false);
      }
    };
    fetchJobs();
  }, []);

  const handleDeleteJob = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation();
    if (deletingJobId) return;

    setDeletingJobId(jobId);
    try {
      await deleteJob(jobId);
      setExistingJobs((jobs) => jobs.filter((j) => j.id !== jobId));
    } catch (error) {
      console.error('Failed to delete job:', error);
    } finally {
      setDeletingJobId(null);
    }
  };

  const handleCreateJob = async () => {
    if (!jobName.trim()) return;

    setIsCreating(true);
    try {
      const job = await createJob({ name: jobName.trim() });
      navigate(`/jobs/${job.id}`);
    } catch (error) {
      console.error('Failed to create job:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSelectJob = (job: Job) => {
    navigate(`/jobs/${job.id}`);
  };

  const getStatusIcon = (stage: string) => {
    switch (stage.toLowerCase()) {
      case 'completed':
        return <CheckCircle className="w-3.5 h-3.5 text-accent-cyan" />;
      case 'failed':
      case 'cancelled':
        return <AlertCircle className="w-3.5 h-3.5 text-red-400" />;
      case 'created':
        return <Clock className="w-3.5 h-3.5 text-white/30" />;
      default:
        return <Loader2 className="w-3.5 h-3.5 text-accent-amber animate-spin" />;
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

  return (
    <div className="space-y-8">
      {/* Create New Job - Inline Form */}
      <GlassCard className="p-5">
        <div className="flex items-center gap-3">
          <input
            type="text"
            value={jobName}
            onChange={(e) => setJobName(e.target.value)}
            placeholder="Enter job name..."
            className="flex-1 bg-white/[0.03] border border-white/[0.06] rounded px-4 py-2.5 text-sm text-white placeholder-white/30 focus:outline-none focus:border-accent-cyan/50 transition-colors"
            onKeyDown={(e) => e.key === 'Enter' && handleCreateJob()}
          />
          <Button
            onClick={handleCreateJob}
            disabled={!jobName.trim() || isCreating}
            loading={isCreating}
            glow={!!jobName.trim()}
          >
            Create
            {!isCreating && <Plus className="w-4 h-4 ml-1.5" />}
          </Button>
        </div>
      </GlassCard>

      {/* Existing Jobs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <span className="label">Jobs</span>
          <span className="text-[10px] font-mono text-white/30">
            {existingJobs.length} total
          </span>
        </div>

        {isLoadingJobs ? (
          <GlassCard className="p-8">
            <div className="flex items-center justify-center gap-3 text-white/40">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span className="text-sm">Loading jobs...</span>
            </div>
          </GlassCard>
        ) : existingJobs.length === 0 ? (
          <GlassCard className="p-8">
            <div className="text-center">
              <Briefcase className="w-8 h-8 text-white/20 mx-auto mb-3" />
              <p className="text-sm text-white/40">No jobs yet</p>
              <p className="text-xs text-white/20 mt-1">Create your first job above</p>
            </div>
          </GlassCard>
        ) : (
          <div className="grid gap-3">
            {existingJobs.map((job, i) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <button
                  onClick={() => handleSelectJob(job)}
                  className="w-full text-left"
                >
                  <GlassCard className="p-4 hover:bg-white/[0.04] cursor-pointer group">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-white/[0.03] border border-white/[0.06] flex items-center justify-center flex-shrink-0 group-hover:border-accent-cyan/30 transition-colors">
                          <Briefcase className="w-4 h-4 text-white/40 group-hover:text-accent-cyan transition-colors" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <h3 className="text-sm font-medium truncate group-hover:text-accent-cyan transition-colors">
                            {job.name}
                          </h3>
                          <div className="flex items-center gap-3 mt-1">
                            {(job.video_file_count > 0 || job.audio_file_count > 0) ? (
                              <>
                                <span className="text-[10px] font-mono text-white/30 flex items-center gap-1">
                                  <Film className="w-3 h-3" />
                                  {job.video_file_count}
                                </span>
                                <span className="text-[10px] font-mono text-white/30 flex items-center gap-1">
                                  <Music className="w-3 h-3" />
                                  {job.audio_file_count}
                                </span>
                              </>
                            ) : (
                              <span className="text-[10px] font-mono text-white/20">No files</span>
                            )}
                            {job.otio_file_id && (
                              <span className="text-[10px] font-mono text-accent-cyan flex items-center gap-1">
                                <Download className="w-3 h-3" />
                                Output ready
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <div className="flex items-center gap-2">
                          {getStatusIcon(job.stage)}
                          <span className="text-xs text-white/50">
                            {getStatusLabel(job.stage)}
                          </span>
                        </div>
                        <button
                          onClick={(e) => handleDeleteJob(e, job.id)}
                          disabled={deletingJobId === job.id}
                          className="p-1.5 rounded-lg hover:bg-red-500/10 text-white/20 hover:text-red-400 transition-colors disabled:opacity-50"
                          title="Delete job"
                        >
                          {deletingJobId === job.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </button>
                        <ArrowRight className="w-4 h-4 text-white/20 group-hover:text-accent-cyan group-hover:translate-x-1 transition-all" />
                      </div>
                    </div>
                  </GlassCard>
                </button>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
