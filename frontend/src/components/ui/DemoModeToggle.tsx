import { FlaskConical, FlaskRound } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/utils/cn';

export function DemoModeToggle() {
  const { demoMode, toggleDemoMode } = useAppStore();

  return (
    <button
      onClick={toggleDemoMode}
      className={cn(
        'flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors',
        demoMode
          ? 'bg-[var(--accent-purple)]/10 text-[var(--accent-purple)]'
          : 'text-[var(--text-muted)] hover:bg-[var(--border-subtle)] hover:text-[var(--text-primary)]'
      )}
      title={demoMode ? 'Demo Mode ON' : 'Demo Mode OFF'}
    >
      {demoMode ? <FlaskConical className="w-3.5 h-3.5" /> : <FlaskRound className="w-3.5 h-3.5" />}
      <span className="hidden sm:inline">Demo</span>
    </button>
  );
}
