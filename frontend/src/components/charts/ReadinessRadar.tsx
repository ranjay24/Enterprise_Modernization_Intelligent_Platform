import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts';
import type { ReadinessBreakdown } from '@/types/dashboard';

export function ReadinessRadar({ data }: { data: ReadinessBreakdown }) {
  const chartData = data.dimensions.map((d) => ({
    dimension: d.name,
    score: d.score,
    fullMark: 100,
  }));

  return (
    <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--border-subtle)] p-4 h-full">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">Radar View</h3>
      <p className="text-xs text-[var(--text-secondary)] mb-2">Score distribution across dimensions</p>
      <ResponsiveContainer width="100%" height={260}>
        <RadarChart data={chartData}>
          <defs>
            <linearGradient id="radarFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent-blue)" stopOpacity={0.2} />
              <stop offset="100%" stopColor="var(--accent-purple)" stopOpacity={0.05} />
            </linearGradient>
          </defs>
          <PolarGrid stroke="var(--border-subtle)" strokeWidth={0.5} />
          <PolarAngleAxis
            dataKey="dimension"
            tick={{ fill: 'var(--text-muted)', fontSize: 10, fontWeight: 500 }}
            tickLine={false}
          />
          <Radar
            name="Score"
            dataKey="score"
            stroke="var(--accent-blue)"
            fill="url(#radarFill)"
            strokeWidth={1.5}
            dot={{ r: 3, fill: 'var(--accent-blue)', strokeWidth: 0 }}
            activeDot={{ r: 4, fill: 'var(--accent-blue)', strokeWidth: 0 }}
            isAnimationActive={true}
            animationDuration={400}
          />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
