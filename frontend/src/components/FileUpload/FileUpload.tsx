import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, Film, Music, FileVideo, FileAudio, Check, Loader2, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import { uploadFiles, type FileUploadProgress } from '../../api/client';
import { useJobStore } from '../../store/jobStore';

interface FileUploadProps {
  jobId: string;
  onUploadComplete?: () => void;
  disabled?: boolean;
}

export function FileUpload({ jobId, onUploadComplete, disabled }: FileUploadProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [fileProgress, setFileProgress] = useState<FileUploadProgress[]>([]);
  const [skippedFiles, setSkippedFiles] = useState<string[]>([]);
  const { uploadedFiles, addUploadedFiles } = useJobStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      // Filter out duplicates
      const existingFilenames = new Set(uploadedFiles.map((f) => f.filename));
      const newFiles = acceptedFiles.filter((f) => !existingFilenames.has(f.name));
      const duplicates = acceptedFiles.filter((f) => existingFilenames.has(f.name));

      // Show skipped files notification
      if (duplicates.length > 0) {
        setSkippedFiles(duplicates.map((f) => f.name));
        setTimeout(() => setSkippedFiles([]), 5000);
      }

      if (newFiles.length === 0) return;

      setIsUploading(true);
      setFileProgress([]);

      try {
        const result = await uploadFiles(jobId, newFiles, (progress) => {
          setFileProgress([...progress]);
        });
        addUploadedFiles(result);
        onUploadComplete?.();
      } catch (error) {
        console.error('Upload failed:', error);
      } finally {
        setIsUploading(false);
        setFileProgress([]);
      }
    },
    [jobId, addUploadedFiles, onUploadComplete, uploadedFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv', '.webm'],
      'audio/*': ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'],
    },
    disabled: disabled || isUploading,
  });

  const videoFiles = uploadedFiles.filter((f) =>
    f.content_type.startsWith('video/')
  );
  const audioFiles = uploadedFiles.filter((f) =>
    f.content_type.startsWith('audio/')
  );

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={clsx(
          'relative border border-dashed rounded-lg p-8 text-center cursor-pointer transition-all duration-300',
          isDragActive
            ? 'border-accent-cyan bg-accent-cyan/5'
            : 'border-white/[0.1] hover:border-white/[0.2] hover:bg-white/[0.02]',
          (disabled || isUploading) && 'opacity-50 cursor-not-allowed'
        )}
      >
        <input {...getInputProps()} />

        {/* Glow effect on drag */}
        <AnimatePresence>
          {isDragActive && (
            <motion.div
              className="absolute inset-0 rounded-lg bg-accent-cyan/10 pointer-events-none"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            />
          )}
        </AnimatePresence>

        <div className="relative">
          {isDragActive ? (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              <div className="w-12 h-12 rounded-xl bg-accent-cyan/20 border border-accent-cyan/30 flex items-center justify-center mx-auto mb-3">
                <Upload className="w-5 h-5 text-accent-cyan" />
              </div>
              <p className="text-sm text-accent-cyan">Release to upload</p>
            </motion.div>
          ) : (
            <>
              <div className="w-12 h-12 rounded-xl bg-white/[0.05] border border-white/[0.1] flex items-center justify-center mx-auto mb-3">
                <Upload className="w-5 h-5 text-white/40" />
              </div>
              <p className="text-sm text-white/60 mb-1">
                Drop files here or click to browse
              </p>
              <p className="text-[10px] font-mono text-white/30 uppercase tracking-wider">
                MP4 • MOV • AVI • MKV • MP3 • WAV • M4A
              </p>
            </>
          )}
        </div>
      </div>

      {/* Skipped Duplicates Warning */}
      <AnimatePresence>
        {skippedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-amber-500/10 rounded-lg p-3 border border-amber-500/20 flex items-start gap-2">
              <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs text-amber-400 font-medium">
                  {skippedFiles.length} duplicate{skippedFiles.length > 1 ? 's' : ''} skipped
                </p>
                <p className="text-xs text-amber-400/70 mt-0.5">
                  {skippedFiles.slice(0, 3).join(', ')}
                  {skippedFiles.length > 3 && ` +${skippedFiles.length - 3} more`}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Upload Progress */}
      <AnimatePresence>
        {isUploading && fileProgress.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-white/[0.03] rounded-lg p-4 border border-white/[0.06] space-y-3">
              {/* Overall progress header */}
              <div className="flex justify-between items-center">
                <span className="text-xs text-white/50 font-mono uppercase">
                  Uploading {fileProgress.filter(f => f.status === 'complete').length}/{fileProgress.length} files
                </span>
                <span className="text-xs font-mono text-accent-cyan">
                  {Math.round(
                    fileProgress.reduce((sum, f) => sum + f.percent, 0) / fileProgress.length
                  )}%
                </span>
              </div>

              {/* Per-file progress */}
              <div className="space-y-2">
                {fileProgress.map((file) => (
                  <div key={file.fileIndex} className="space-y-1">
                    <div className="flex items-center gap-2">
                      {/* Status icon */}
                      {file.status === 'complete' ? (
                        <Check className="w-3 h-3 text-green-400 flex-shrink-0" />
                      ) : file.status === 'error' ? (
                        <AlertCircle className="w-3 h-3 text-red-400 flex-shrink-0" />
                      ) : file.status === 'processing' ? (
                        <Loader2 className="w-3 h-3 text-accent-cyan animate-spin flex-shrink-0" />
                      ) : file.status === 'uploading' ? (
                        <Loader2 className="w-3 h-3 text-accent-cyan animate-spin flex-shrink-0" />
                      ) : (
                        <div className="w-3 h-3 rounded-full border border-white/20 flex-shrink-0" />
                      )}

                      {/* Filename */}
                      <span className={clsx(
                        'text-xs truncate flex-1',
                        file.status === 'complete' ? 'text-white/40' : 'text-white/70'
                      )}>
                        {file.fileName}
                      </span>

                      {/* Progress percent */}
                      <span className={clsx(
                        'text-xs font-mono',
                        file.status === 'complete' ? 'text-green-400' :
                        file.status === 'processing' ? 'text-accent-cyan' :
                        'text-white/40'
                      )}>
                        {file.status === 'processing' ? 'saving...' :
                         file.status === 'complete' ? 'done' :
                         file.status === 'pending' ? 'waiting' :
                         `${file.percent}%`}
                      </span>
                    </div>

                    {/* Progress bar for active file */}
                    {(file.status === 'uploading' || file.status === 'processing') && (
                      <div className="h-1 bg-white/[0.05] rounded-full overflow-hidden ml-5">
                        {file.status === 'processing' ? (
                          <motion.div
                            className="h-full w-1/3 bg-accent-cyan rounded-full"
                            animate={{ x: ['-100%', '400%'] }}
                            transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                          />
                        ) : (
                          <motion.div
                            className="h-full bg-accent-cyan rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${file.percent}%` }}
                            transition={{ duration: 0.1, ease: 'easeOut' }}
                          />
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Uploaded Files */}
      <AnimatePresence>
        {uploadedFiles.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="grid grid-cols-2 gap-4"
          >
            {/* Video Files */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Film className="w-3 h-3 text-accent-cyan" />
                <span className="label">Video ({videoFiles.length})</span>
              </div>
              <div className="space-y-1">
                {videoFiles.length > 0 ? (
                  videoFiles.map((file, i) => (
                    <motion.div
                      key={file.file_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-2 py-1.5 px-2 rounded bg-white/[0.02] border border-white/[0.04] group"
                    >
                      <FileVideo className="w-3 h-3 text-white/30 flex-shrink-0" />
                      <span className="text-xs text-white/60 truncate flex-1">
                        {file.filename}
                      </span>
                    </motion.div>
                  ))
                ) : (
                  <p className="text-xs text-white/20 py-2">No video files</p>
                )}
              </div>
            </div>

            {/* Audio Files */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Music className="w-3 h-3 text-accent-amber" />
                <span className="label">Audio ({audioFiles.length})</span>
              </div>
              <div className="space-y-1">
                {audioFiles.length > 0 ? (
                  audioFiles.map((file, i) => (
                    <motion.div
                      key={file.file_id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-center gap-2 py-1.5 px-2 rounded bg-white/[0.02] border border-white/[0.04] group"
                    >
                      <FileAudio className="w-3 h-3 text-white/30 flex-shrink-0" />
                      <span className="text-xs text-white/60 truncate flex-1">
                        {file.filename}
                      </span>
                    </motion.div>
                  ))
                ) : (
                  <p className="text-xs text-white/20 py-2">No audio files</p>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
