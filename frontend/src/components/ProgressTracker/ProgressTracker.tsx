import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, AlertCircle, Loader2, Sparkles, Pause, X } from 'lucide-react';
import clsx from 'clsx';
import { wsClient } from '../../api/websocket';
import { useProgressStore } from '../../store/progressStore';
import type { PipelineStage } from '../../types/progress';

interface ProgressTrackerProps {
  jobId: string;
  /** Whether the job appears stuck (no active progress updates) */
  isStuck?: boolean;
  /** Whether the job has failed */
  isFailed?: boolean;
  /** Error message for failed jobs */
  errorMessage?: string;
  /** Checkpoint: manifest exists (annotation complete) */
  hasManifest?: boolean;
  /** Checkpoint: blueprint exists (planning complete) */
  hasBlueprint?: boolean;
  /** Checkpoint: style profile extracted */
  hasStyleProfile?: boolean;
}

const STAGES: { key: PipelineStage; label: string; description: string }[] = [
  { key: 'uploading', label: 'Prepare', description: 'Initializing assets' },
  { key: 'annotating', label: 'Analyze', description: 'Processing media' },
  { key: 'planning', label: 'Plan', description: 'AI decision making' },
  { key: 'executing', label: 'Generate', description: 'Building timeline' },
  { key: 'completed', label: 'Done', description: 'Export ready' },
];

export function ProgressTracker({ jobId, isStuck = false, isFailed: isFailedProp = false, errorMessage, hasManifest = false, hasBlueprint = false, hasStyleProfile = false }: ProgressTrackerProps) {
  const {
    stage: wsStage,
    progressPercent: wsProgressPercent,
    currentItem,
    processedItems,
    totalItems,
    message,
    updateProgress,
  } = useProgressStore();

  useEffect(() => {
    wsClient.connect(jobId, updateProgress);
    return () => wsClient.disconnect();
  }, [jobId, updateProgress]);

  // Determine stage and progress based on checkpoints when stuck or failed
  let stage = wsStage;
  let progressPercent = wsProgressPercent;

  if ((isStuck || isFailedProp) && wsProgressPercent === 0) {
    // Initialize from checkpoints - show where we got to
    if (hasBlueprint) {
      stage = isFailedProp ? 'executing' : 'executing';  // Failed/paused during execute
      progressPercent = 70;
    } else if (hasStyleProfile) {
      stage = 'planning';   // Style done = at planning stage
      progressPercent = 55;
    } else if (hasManifest) {
      stage = 'planning';   // Manifest done = paused at planning
      progressPercent = 50;
    } else {
      stage = 'annotating'; // Failed early
      progressPercent = 25;
    }
  }

  const currentStageIndex = STAGES.findIndex((s) => s.key === stage);
  const isComplete = stage === 'completed';
  const isFailed = stage === 'failed' || isFailedProp;
  const isActive = !isComplete && !isFailed && !isStuck;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="label">Pipeline Status</span>
        <div className="flex items-center gap-2">
          {isActive && (
            <Loader2 className="w-3 h-3 text-accent-cyan animate-spin" />
          )}
          {isFailed && (
            <X className="w-3 h-3 text-red-400" />
          )}
          {isStuck && !isComplete && !isFailed && (
            <Pause className="w-3 h-3 text-amber-400" />
          )}
          <span className={clsx(
            "text-xs font-mono",
            isFailed ? "text-red-400" : isStuck && !isComplete ? "text-amber-400" : "text-white/50"
          )}>
            {isComplete ? 'COMPLETE' : isFailed ? 'FAILED' : isStuck ? 'STUCK' : 'PROCESSING'}
          </span>
        </div>
      </div>

      {/* Stage indicators */}
      <div className="flex items-center justify-between">
        {STAGES.map((s, index) => {
          const isCurrentStage = index === currentStageIndex;
          const isDone = index < currentStageIndex || isComplete;
          const isStuckAtStage = isStuck && isCurrentStage && !isComplete && !isFailed;
          const isFailedAtStage = isFailed && isCurrentStage;

          return (
            <div key={s.key} className="flex items-center flex-1 last:flex-initial">
              <div className="flex flex-col items-center">
                <motion.div
                  className={clsx(
                    'w-10 h-10 rounded-xl flex items-center justify-center text-xs font-medium border transition-all duration-300',
                    isDone
                      ? 'bg-accent-cyan/20 border-accent-cyan/30 text-accent-cyan'
                      : isFailedAtStage
                      ? 'bg-red-500/10 border-red-500/30 text-red-400'
                      : isStuckAtStage
                      ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                      : isCurrentStage
                      ? 'bg-white/[0.05] border-accent-cyan/50 text-white shadow-glow-sm'
                      : 'bg-white/[0.02] border-white/[0.06] text-white/30'
                  )}
                  animate={isCurrentStage && !isStuck && !isFailed ? { scale: [1, 1.05, 1] } : {}}
                  transition={{ duration: 2, repeat: Infinity }}
                >
                  {isDone ? (
                    <Check className="w-4 h-4" />
                  ) : isFailedAtStage ? (
                    <X className="w-4 h-4" />
                  ) : isStuckAtStage ? (
                    <Pause className="w-4 h-4" />
                  ) : isCurrentStage ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <span className="font-mono">{String(index + 1).padStart(2, '0')}</span>
                  )}
                </motion.div>
                <div className="mt-3 text-center">
                  <span
                    className={clsx(
                      'text-xs font-medium block',
                      isFailedAtStage ? 'text-red-400' : isStuckAtStage ? 'text-amber-400' : isCurrentStage ? 'text-white' : isDone ? 'text-accent-cyan/80' : 'text-white/30'
                    )}
                  >
                    {s.label}
                  </span>
                  <span className="text-[10px] text-white/20 mt-0.5 hidden sm:block">
                    {s.description}
                  </span>
                </div>
              </div>
              {index < STAGES.length - 1 && (
                <div className="flex-1 mx-3 relative">
                  <div className="h-px bg-white/[0.06]" />
                  <motion.div
                    className="absolute inset-y-0 left-0 h-px bg-accent-cyan"
                    initial={{ width: '0%' }}
                    animate={{ width: isDone ? '100%' : '0%' }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <span className={clsx("text-xs truncate", isFailed ? "text-red-400/70" : isStuck ? "text-amber-400/70" : "text-white/40")}>
              {isFailed && !currentItem && !message
                ? `Failed${hasBlueprint ? ' (planning complete)' : hasStyleProfile ? ' (style extracted)' : hasManifest ? ' (analysis complete)' : ''}`
                : isStuck && !currentItem && !message
                ? `Paused at checkpoint${hasBlueprint ? ' (planning complete)' : hasStyleProfile ? ' (style extracted)' : hasManifest ? ' (analysis complete)' : ''}`
                : currentItem || message || 'Initializing...'}
            </span>
          </div>
          <span className={clsx("text-sm font-mono ml-4", isFailed ? "text-red-400" : "text-accent-cyan")}>
            {Math.round(progressPercent)}%
          </span>
        </div>

        <div className="relative h-2 bg-white/[0.03] rounded-full overflow-hidden border border-white/[0.06]">
          <motion.div
            className={clsx(
              'absolute inset-y-0 left-0 rounded-full',
              isFailed ? 'bg-red-500' : isStuck ? 'bg-amber-500' : 'bg-accent-cyan'
            )}
            initial={{ width: '0%' }}
            animate={{ width: `${progressPercent}%` }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
          />
          {/* Shimmer effect - disabled when stuck */}
          {!isFailed && !isComplete && !isStuck && progressPercent > 0 && (
            <motion.div
              className="absolute inset-y-0 w-20 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              animate={{ x: ['-100%', '500%'] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}
            />
          )}
        </div>

        {totalItems > 0 && (
          <div className="flex items-center justify-between text-[10px] font-mono text-white/30">
            <span>{processedItems} / {totalItems} items</span>
            <span>{Math.round((processedItems / totalItems) * 100)}% complete</span>
          </div>
        )}
      </div>

      {/* Status messages */}
      <AnimatePresence mode="wait">
        {isFailed && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/20"
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-red-400 font-medium">Processing Failed</p>
              {(errorMessage || message) && <p className="text-xs text-red-400/70 mt-1">{errorMessage || message}</p>}
            </div>
          </motion.div>
        )}

        {isComplete && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="flex items-start gap-3 p-4 rounded-lg bg-accent-cyan/10 border border-accent-cyan/20"
          >
            <Sparkles className="w-5 h-5 text-accent-cyan flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-accent-cyan font-medium">Processing Complete</p>
              <p className="text-xs text-white/40 mt-1">Your OTIO timeline is ready for export</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
