import clsx from 'clsx';
import { motion } from 'framer-motion';

interface StatusIndicatorProps {
  status: 'active' | 'warning' | 'error' | 'idle';
  label?: string;
  pulse?: boolean;
}

export function StatusIndicator({ status, label, pulse = true }: StatusIndicatorProps) {
  const colors = {
    active: 'bg-accent-cyan shadow-[0_0_10px_rgba(0,240,255,0.5)]',
    warning: 'bg-accent-amber shadow-[0_0_10px_rgba(255,184,0,0.5)]',
    error: 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]',
    idle: 'bg-white/20',
  };

  return (
    <div className="flex items-center gap-2">
      <motion.div
        className={clsx('w-1.5 h-1.5 rounded-full', colors[status])}
        animate={pulse && status !== 'idle' ? { opacity: [0.5, 1, 0.5] } : undefined}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      />
      {label && (
        <span className="text-xs text-white/50 font-mono uppercase tracking-wider">
          {label}
        </span>
      )}
    </div>
  );
}
