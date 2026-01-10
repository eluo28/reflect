import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Play, Zap } from 'lucide-react';
import { StatusIndicator } from './ui';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Grid background */}
      <div className="fixed inset-0 grid-bg pointer-events-none" />

      {/* Gradient orbs */}
      <div className="fixed top-0 left-1/4 w-[600px] h-[600px] bg-accent-cyan/[0.03] rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-0 right-1/4 w-[400px] h-[400px] bg-accent-amber/[0.02] rounded-full blur-[100px] pointer-events-none" />

      {/* Header */}
      <header className="relative z-10 border-b border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <motion.div
            className="flex items-center gap-3"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="relative">
              <div className="w-9 h-9 rounded-lg bg-accent-cyan/10 border border-accent-cyan/20 flex items-center justify-center">
                <Play className="w-4 h-4 text-accent-cyan fill-accent-cyan" />
              </div>
              {/* Glow behind logo */}
              <div className="absolute inset-0 rounded-lg bg-accent-cyan/20 blur-xl -z-10" />
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight">Reflect</h1>
              <p className="text-[10px] uppercase tracking-widest text-white/40 font-mono">
                Style Engine
              </p>
            </div>
          </motion.div>

          {/* Status */}
          <motion.div
            className="flex items-center gap-6"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <div className="flex items-center gap-2 text-white/40">
              <Zap className="w-3 h-3" />
              <span className="text-[10px] uppercase tracking-widest font-mono">
                System Online
              </span>
            </div>
            <StatusIndicator status="active" />
          </motion.div>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 flex-1 max-w-6xl w-full mx-auto px-6 py-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {children}
        </motion.div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/[0.06]">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <p className="text-[10px] uppercase tracking-widest text-white/30 font-mono">
            AI-Powered Video Editing
          </p>
          <div className="flex items-center gap-1 text-[10px] font-mono text-white/30">
            <span>v0.1.0</span>
            <span className="text-white/10">|</span>
            <span className="text-accent-cyan/60">OTIO Export</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
