import type { MigrationWave } from '@/types/api';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { WaveCard } from '@/components/cards/WaveCard';
import { MigrationTimelineChart } from '@/components/charts/MigrationTimelineChart';
import type { MigrationTimelineWave } from '@/types/dashboard';

function apiWaveToTimelineWave(wave: MigrationWave, allWaves: MigrationWave[]): MigrationTimelineWave {
  let weekStart = 1;
  for (const w of allWaves) {
    if (w.wave_number < wave.wave_number) weekStart += w.timeline_weeks;
  }
  return {
    id: `wave-${wave.wave_number}`,
    wave: wave.wave_number,
    name: wave.name,
    priority: wave.risk_level === 'high' ? 'high' : wave.risk_level === 'medium' ? 'medium' : 'low',
    duration: `${wave.timeline_weeks} weeks`,
    durationWeeks: { start: weekStart, end: weekStart + wave.timeline_weeks - 1 },
    services: wave.services,
    risk: wave.risk_level as 'low' | 'medium' | 'high' | 'critical',
    status: wave.wave_number === 1 ? 'completed' : wave.wave_number === 2 ? 'in_progress' : 'planned',
    progress: wave.wave_number === 1 ? 100 : wave.wave_number === 2 ? 35 : 0,
    dependencies: wave.dependencies,
    estimatedEngineers: wave.estimated_engineers,
    estimatedCost: 0,
  };
}

export function MigrationRoadmap({ waves }: { waves: MigrationWave[] }) {
  const safeWaves = (waves || []).filter(Boolean);
  const timelineWaves = safeWaves.map((w) => apiWaveToTimelineWave(w, safeWaves));
  const totalWeeks = (waves || []).reduce((sum, w) => sum + (w.timeline_weeks || 0), 0);
  const totalEngineers = waves.length > 0 ? Math.max(...waves.map((w) => w.estimated_engineers || 0)) : 0;

  return (
    <section>
      <SectionHeader
        title="Migration Roadmap"
        description={`${waves.length} waves • ${totalWeeks} weeks • Up to ${totalEngineers} engineers`}
      />
      <div className="space-y-4">
        <MigrationTimelineChart waves={timelineWaves} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {timelineWaves.map((wave) => (
            <WaveCard key={wave.id} data={wave} />
          ))}
        </div>
      </div>
    </section>
  );
}
