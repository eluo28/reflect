import { forwardRef, HTMLAttributes, ReactNode } from 'react';
import { motion } from 'framer-motion';
import clsx from 'clsx';

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  glow?: boolean;
  glowColor?: 'cyan' | 'amber';
  hover?: boolean;
  children?: ReactNode;
}

export const GlassCard = forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, children, glow = false, glowColor = 'cyan', hover = true }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={clsx(
          'relative rounded-lg border border-white/[0.06] bg-white/[0.02] backdrop-blur-sm',
          'shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)]',
          hover && 'transition-all duration-300 hover:border-white/[0.1] hover:bg-white/[0.03]',
          className
        )}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {/* Top gradient highlight */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        {/* Glow effect */}
        {glow && (
          <div
            className={clsx(
              'absolute -inset-px rounded-lg opacity-50 blur-xl -z-10',
              glowColor === 'cyan' ? 'bg-accent-cyan/20' : 'bg-accent-amber/20'
            )}
          />
        )}

        {/* Content */}
        <div className="relative">{children}</div>
      </motion.div>
    );
  }
);

GlassCard.displayName = 'GlassCard';
