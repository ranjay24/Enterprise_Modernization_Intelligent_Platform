import type { KPICard } from '@/types/dashboard';
import { StatCard } from '@/components/cards/StatCard';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function ExecutiveSummary({ data }: { data: KPICard[] }) {
  return (
    <section>
      <SectionHeader title="Executive Summary" description="Key performance indicators across the platform" size="lg" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3 mt-4">
        {data.map((card) => (
          <StatCard key={card.id} data={card} />
        ))}
      </div>
    </section>
  );
}
