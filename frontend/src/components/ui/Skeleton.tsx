import clsx from 'clsx';

interface SkeletonProps {
  className?: string;
  lines?: number;
  variant?: 'text' | 'circular' | 'rectangular';
}

export function Skeleton({ className, lines = 1, variant = 'text' }: SkeletonProps) {
  const baseStyles = 'skeleton';

  const variants = {
    text: 'h-4 rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-lg',
  };

  if (lines > 1) {
    return (
      <div className="space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={clsx(baseStyles, variants[variant], className)}
            style={{ width: i === lines - 1 ? '60%' : '100%' }}
          />
        ))}
      </div>
    );
  }

  return <div className={clsx(baseStyles, variants[variant], className)} />;
}

// Terminal-style skeleton that looks like loading data
export function TerminalSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="font-mono text-xs space-y-1.5">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-accent-cyan/50">{'>'}</span>
          <div
            className="skeleton h-3 rounded"
            style={{ width: `${40 + Math.random() * 40}%` }}
          />
        </div>
      ))}
      <div className="flex items-center gap-2">
        <span className="text-accent-cyan">{'>'}</span>
        <span className="cursor" />
      </div>
    </div>
  );
}
