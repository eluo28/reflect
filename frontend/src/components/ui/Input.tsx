import { forwardRef, InputHTMLAttributes } from 'react';
import clsx from 'clsx';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, ...props }, ref) => {
    return (
      <div className="space-y-2">
        {label && (
          <label className="label">{label}</label>
        )}
        <div className="relative">
          <input
            ref={ref}
            className={clsx(
              'w-full bg-white/[0.03] border rounded px-4 py-3',
              'text-white placeholder-white/30 text-sm',
              'focus:outline-none transition-all duration-200',
              error
                ? 'border-red-500/50 focus:border-red-500'
                : 'border-white/[0.06] focus:border-accent-cyan/50 focus:shadow-glow-sm',
              className
            )}
            {...props}
          />
          {/* Focus glow effect */}
          <div className="absolute inset-0 rounded opacity-0 focus-within:opacity-100 pointer-events-none transition-opacity duration-200 bg-accent-cyan/5" />
        </div>
        {error && (
          <p className="text-xs text-red-400">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
