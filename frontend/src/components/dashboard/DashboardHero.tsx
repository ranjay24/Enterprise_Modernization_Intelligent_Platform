import { motion } from 'framer-motion';
import { Download, GitBranch, FileText, AlertTriangle, DollarSign, Database, Package, Shield } from 'lucide-react';
import { GlassCard, GlassCardContent } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { cn } from '@/utils/cn';
import { useEffect, useState } from 'react';

interface HeroStat {
  label: string;
  value: number | string;
  unit?: string;
  icon: React.ElementType;
  color: string;
}

interface DashboardHeroProps {
  overallScore: number;
  confidence: number;
  statusLabel: string;
  statusColor: string;
  stats: HeroStat[];
}

function AnimatedNumber({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0);
  useEffect(() => {
    let start = 0;
    const duration = 700;
    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      start = Math.round(eased * value);
      setDisplay(start);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value]);
  return <>{display}{suffix}</>;
}

function RadialGauge({
  score,
  size = 180,
  strokeWidth = 8,
}: {
  score: number;
  size?: number;
  strokeWidth?: number;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const [offset, setOffset] = useState(circumference);

  useEffect(() => {
    const targetOffset = circumference * (1 - score / 100);
    let start = circumference;
    const duration = 700;
    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      start = circumference - eased * (circumference - targetOffset);
      setOffset(start);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [score, circumference]);

  const scoreColor = score >= 70 ? '#2FD97F' : score >= 40 ? '#F5A623' : '#FB4B6C';

  return (
    <svg width={size} height={size} className="shrink-0">
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="var(--border-subtle)"
        strokeWidth={strokeWidth}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={scoreColor}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{ transition: 'stroke-dashoffset 50ms linear' }}
      />
    </svg>
  );
}

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.1 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as [number, number, number, number] } },
};

export function DashboardHero({ overallScore, confidence, statusLabel, statusColor, stats }: DashboardHeroProps) {
  const scoreColor = overallScore >= 70 ? 'text-[var(--success)]' : overallScore >= 40 ? 'text-[var(--warning)]' : 'text-[var(--risk)]';

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <GlassCard glow="blue" className="w-full">
        <GlassCardContent className="p-6 lg:p-8">
          <div className="flex flex-col lg:flex-row gap-8 lg:gap-12">
            {/* Left - Radial gauge */}
            <motion.div variants={itemVariants} className="flex flex-col items-center shrink-0">
              <div className="relative">
                <RadialGauge score={overallScore} size={180} strokeWidth={10} />
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className={cn('text-hero leading-none', scoreColor)}>
                    <AnimatedNumber value={overallScore} />
                  </span>
                  <span className="text-xs text-[var(--text-secondary)] mt-1 font-medium">/ 100</span>
                </div>
              </div>
              <div className={cn('mt-4 px-3 py-1 rounded-full text-xs font-semibold', statusColor)}>
                {statusLabel}
              </div>
              <div className="mt-2 text-xs text-[var(--text-muted)]">
                Confidence: <span className="font-semibold text-[var(--text-primary)]">{confidence}%</span>
              </div>
            </motion.div>

            {/* Right - 2x3 stat grid */}
            <motion.div variants={itemVariants} className="flex-1 grid grid-cols-2 sm:grid-cols-3 gap-4 auto-rows-min">
              {stats.map((stat) => {
                const Icon = stat.icon;
                return (
                  <div key={stat.label} className="space-y-1">
                    <div className="flex items-center gap-1.5">
                      <Icon className={cn('w-3.5 h-3.5', stat.color)} />
                      <span className="text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
                        {stat.label}
                      </span>
                    </div>
                    <div className="text-xl font-bold text-[var(--text-primary)] tabular-nums leading-tight">
                      {typeof stat.value === 'number' ? (
                        <AnimatedNumber value={stat.value} />
                      ) : (
                        stat.value
                      )}
                      {stat.unit && (
                        <span className="text-sm font-normal text-[var(--text-secondary)] ml-0.5">{stat.unit}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </motion.div>
          </div>

          {/* Action bar */}
          <motion.div variants={itemVariants} className="flex items-center gap-3 mt-8 pt-6 border-t border-[var(--border-subtle)]">
            <Button variant="primary" className="gap-2" disabled title="Coming soon">
              <Download className="w-4 h-4" />
              Download Report
            </Button>
            <Button variant="secondary" className="gap-2" disabled title="Coming soon">
              <GitBranch className="w-4 h-4" />
              View Architecture
            </Button>
          </motion.div>
        </GlassCardContent>
      </GlassCard>
    </motion.div>
  );
}
