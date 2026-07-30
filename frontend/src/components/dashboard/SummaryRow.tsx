import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';

interface SummaryStat {
  label: string;
  value: number;
  unit?: string;
  format?: (v: number) => string;
}

function StatValue({ stat }: { stat: SummaryStat }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const duration = 700;
    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      start = Math.round(eased * stat.value);
      setDisplay(start);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [stat.value]);

  return (
    <>
      {stat.format ? stat.format(display) : display}
      {stat.unit && <span className="text-sm font-normal text-[var(--text-muted)] ml-0.5">{stat.unit}</span>}
    </>
  );
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.04, delayChildren: 0.2 } },
};

const itemVariants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } },
};

export function SummaryRow({ stats }: { stats: SummaryStat[] }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="flex items-stretch gap-10 pb-5 border-b border-[var(--border-subtle)]"
    >
      {stats.map((stat, i) => (
        <motion.div key={stat.label} variants={itemVariants} className="flex items-baseline gap-2 min-w-0">
          <span className="text-2xl font-bold text-[var(--text-primary)] tabular-nums leading-none">
            <StatValue stat={stat} />
          </span>
          <span className="text-xs text-[var(--text-muted)] whitespace-nowrap">{stat.label}</span>
          {i < stats.length - 1 && (
            <span className="hidden sm:block w-px h-5 bg-[var(--border-subtle)] ml-2 shrink-0" />
          )}
        </motion.div>
      ))}
    </motion.div>
  );
}
