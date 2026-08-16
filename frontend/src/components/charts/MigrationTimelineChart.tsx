import type { MigrationTimelineWave } from '@/types/dashboard';
import { cn } from '@/utils/cn';
import { motion } from 'framer-motion';

const barColors: Record<string, string> = {
  completed: 'bg-[var(--success)]',
  in_progress: 'bg-[var(--warning)]',
  planned: 'bg-[var(--border-strong)]',
  blocked: 'bg-[var(--risk)]',
};

export function MigrationTimelineChart({ waves }: { waves: MigrationTimelineWave[] }) {
  const maxWeek = Math.max(...waves.map(w => w.durationWeeks.end));

  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-5">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Timeline</h3>
      <div className="space-y-3">
        {waves.map((wave, i) => {
          const left = ((wave.durationWeeks.start - 1) / maxWeek) * 100;
          const width = ((wave.durationWeeks.end - wave.durationWeeks.start + 1) / maxWeek) * 100;
          return (
            <motion.div
              key={wave.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="flex items-center gap-3 mb-1">
                <span className="text-xs font-medium text-[var(--text-primary)] w-24 shrink-0 truncate">{wave.name}</span>
                <div className="flex-1 h-6 relative bg-[var(--border-subtle)] rounded-md overflow-hidden">
                  <div
                    className={cn('absolute top-0 h-full rounded-md transition-all duration-700 ease-[var(--ease-out)]', barColors[wave.status] || 'bg-[var(--border-strong)]')}
                    style={{ left: `${left}%`, width: `${width}%`, opacity: wave.status === 'planned' ? 0.4 : 1 }}
                  />
                  {wave.status === 'in_progress' && (
                    <div
                      className="absolute top-0 h-full rounded-md bg-[var(--warning)] transition-all duration-700 ease-[var(--ease-out)]"
                      style={{ left: `${left}%`, width: `${Math.min(width, (wave.progress / 100) * width)}%` }}
                    />
                  )}
                </div>
                <span className="text-[10px] text-[var(--text-muted)] w-16 text-right shrink-0">{wave.duration}</span>
              </div>
            </motion.div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-4 text-[10px] text-[var(--text-muted)]">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[var(--success)]" /> Completed</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[var(--warning)]" /> In Progress</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-[var(--border-strong)]" /> Planned</span>
      </div>
    </div>
  );
}
