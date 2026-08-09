import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { ChartDataPoint } from '@/types/dashboard';

interface TooltipEntry {
  name?: string | number;
  value?: number | string;
  color?: string;
}

interface CostTrendTooltipProps {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string | number;
}

const CustomTooltip = ({ active, payload, label }: CostTrendTooltipProps) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-lg p-3 text-xs">
      <p className="font-semibold text-[var(--text-primary)] mb-1.5">{label}</p>
      {payload.map((entry) => (
        <div key={String(entry.name)} className="flex items-center gap-2 py-0.5">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-[var(--text-muted)]">{entry.name}:</span>
          <span className="font-medium text-[var(--text-primary)]">{Number(entry.value).toLocaleString()}</span>
        </div>
      ))}
    </div>
  );
};

export function CostTrendChart({ data }: { data: ChartDataPoint[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="currentGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--accent-blue)" stopOpacity={0.15} />
            <stop offset="95%" stopColor="var(--accent-blue)" stopOpacity={0.01} />
          </linearGradient>
          <linearGradient id="projectedGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--success)" stopOpacity={0.15} />
            <stop offset="95%" stopColor="var(--success)" stopOpacity={0.01} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" strokeWidth={0.5} />
        <XAxis
          dataKey="name"
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          tickLine={false}
          axisLine={{ stroke: 'var(--border-subtle)', strokeWidth: 0.5 }}
        />
        <YAxis
          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 11, color: 'var(--text-muted)' }}
          iconType="circle"
          iconSize={8}
        />
        <Area
          type="monotone"
          dataKey="current"
          name="Current"
          stroke="var(--accent-blue)"
          strokeWidth={1.5}
          fill="url(#currentGrad)"
          dot={false}
          activeDot={{ r: 4, fill: 'var(--accent-blue)', strokeWidth: 0 }}
          isAnimationActive={true}
          animationDuration={400}
        />
        <Area
          type="monotone"
          dataKey="projected"
          name="Projected"
          stroke="var(--success)"
          strokeWidth={1.5}
          fill="url(#projectedGrad)"
          dot={false}
          activeDot={{ r: 4, fill: 'var(--success)', strokeWidth: 0 }}
          isAnimationActive={true}
          animationDuration={400}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
