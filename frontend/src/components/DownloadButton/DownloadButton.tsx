import { useState } from 'react';
import { motion } from 'framer-motion';
import { Download, FileDown, Check, ExternalLink, Clock } from 'lucide-react';
import clsx from 'clsx';
import { downloadOtioFile } from '../../api/client';

const API_BASE = '/api';

interface DownloadButtonProps {
  jobId: string;
  disabled?: boolean;
  startedAt?: string | null;
  completedAt?: string | null;
}

function formatDuration(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (hours > 0) {
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  } else if (minutes > 0) {
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  } else {
    return `${seconds}s`;
  }
}

export function DownloadButton({ jobId, disabled, startedAt, completedAt }: DownloadButtonProps) {
  const [isDownloading, setIsDownloading] = useState(false);
  const [isDownloaded, setIsDownloaded] = useState(false);

  // Calculate duration if both timestamps exist
  const duration = startedAt && completedAt
    ? new Date(completedAt).getTime() - new Date(startedAt).getTime()
    : null;

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      const blob = await downloadOtioFile(jobId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `reflect_edit_${jobId}.otio`;
      a.style.display = 'none';
      document.body.appendChild(a);
      a.click();
      // Delay cleanup to ensure download starts
      setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }, 100);
      setIsDownloaded(true);
      setTimeout(() => setIsDownloaded(false), 3000);
    } catch (error) {
      console.error('Download failed:', error);
      alert(`Download failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="label">Export</span>
        <span className="text-[10px] font-mono text-accent-amber">OTIO FORMAT</span>
      </div>

      {/* Duration display */}
      {duration !== null && (
        <div className="flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-accent-cyan/10 border border-accent-cyan/20">
          <Clock className="w-3.5 h-3.5 text-accent-cyan" />
          <span className="text-xs text-accent-cyan">
            Completed in <span className="font-mono font-medium">{formatDuration(duration)}</span>
          </span>
        </div>
      )}

      <motion.button
        onClick={handleDownload}
        disabled={disabled || isDownloading}
        className={clsx(
          'relative w-full py-4 rounded-lg font-medium transition-all duration-300',
          'flex items-center justify-center gap-3 overflow-hidden',
          'border',
          disabled
            ? 'bg-white/[0.02] border-white/[0.06] text-white/30 cursor-not-allowed'
            : isDownloaded
            ? 'bg-accent-cyan/20 border-accent-cyan/30 text-accent-cyan'
            : 'bg-accent-amber/10 border-accent-amber/30 text-accent-amber hover:bg-accent-amber/20 hover:border-accent-amber/50',
          isDownloading && 'opacity-75'
        )}
        whileHover={!disabled && !isDownloading ? { scale: 1.01 } : undefined}
        whileTap={!disabled && !isDownloading ? { scale: 0.99 } : undefined}
      >
        {/* Shimmer effect */}
        {!disabled && !isDownloading && !isDownloaded && (
          <motion.div
            className="absolute inset-0 bg-gradient-to-r from-transparent via-accent-amber/10 to-transparent"
            animate={{ x: ['-100%', '200%'] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
          />
        )}

        {/* Icon */}
        <span className="relative">
          {isDownloaded ? (
            <Check className="w-5 h-5" />
          ) : isDownloading ? (
            <motion.div
              animate={{ y: [0, -3, 0] }}
              transition={{ duration: 0.6, repeat: Infinity }}
            >
              <FileDown className="w-5 h-5" />
            </motion.div>
          ) : (
            <Download className="w-5 h-5" />
          )}
        </span>

        {/* Text */}
        <span className="relative text-sm">
          {isDownloaded
            ? 'Downloaded!'
            : isDownloading
            ? 'Downloading...'
            : 'Download OTIO File'}
        </span>
      </motion.button>

      {/* Info text */}
      <p className="text-[10px] text-center text-white/30 font-mono">
        Import into DaVinci Resolve, Premiere Pro, or Final Cut Pro
      </p>

      {/* Direct link fallback */}
      <a
        href={`${API_BASE}/jobs/${jobId}/download`}
        download={`reflect_edit_${jobId}.otio`}
        className="flex items-center justify-center gap-2 text-[10px] text-white/30 hover:text-white/50 transition-colors"
      >
        <ExternalLink className="w-3 h-3" />
        Direct download link
      </a>
    </div>
  );
}
