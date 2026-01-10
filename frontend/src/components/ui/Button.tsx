import { forwardRef, ReactNode, MouseEventHandler } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface ButtonProps {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  glow?: boolean;
  loading?: boolean;
  disabled?: boolean;
  className?: string;
  children?: ReactNode;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  type?: 'button' | 'submit' | 'reset';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, children, variant = 'primary', size = 'md', glow = false, loading = false, disabled, onClick, type = 'button' }, ref) => {
    const baseStyles = 'relative inline-flex items-center justify-center font-medium transition-all duration-200 rounded overflow-hidden';

    const variants = {
      primary: clsx(
        'bg-accent-cyan text-void',
        'hover:bg-accent-cyan/90',
        glow && 'shadow-glow-cyan'
      ),
      secondary: clsx(
        'bg-white/[0.05] text-white border border-white/[0.1]',
        'hover:bg-white/[0.08] hover:border-white/[0.15]'
      ),
      ghost: clsx(
        'text-white/60',
        'hover:text-white hover:bg-white/[0.05]'
      ),
    };

    const sizes = {
      sm: 'px-3 py-1.5 text-xs',
      md: 'px-4 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    const isDisabled = disabled || loading;

    return (
      <motion.button
        ref={ref}
        type={type}
        onClick={onClick}
        className={clsx(
          baseStyles,
          variants[variant],
          sizes[size],
          isDisabled && 'opacity-50 cursor-not-allowed',
          className
        )}
        disabled={isDisabled}
        whileHover={!isDisabled ? { scale: 1.02 } : undefined}
        whileTap={!isDisabled ? { scale: 0.98 } : undefined}
      >
        {/* Shimmer effect */}
        {variant === 'primary' && !isDisabled && (
          <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent bg-[length:200%_100%] animate-shimmer" />
        )}

        {/* Loading spinner */}
        {loading && (
          <svg className="animate-spin -ml-1 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}

        <span className="relative inline-flex items-center">{children}</span>
      </motion.button>
    );
  }
);

Button.displayName = 'Button';
