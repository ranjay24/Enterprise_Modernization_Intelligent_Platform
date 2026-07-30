import type { DebtItem } from '@/types/dashboard';
import { DebtCard } from '@/components/cards/DebtCard';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function TechnicalDebt({ data }: { data: DebtItem[] }) {
  return (
    <section>
      <SectionHeader title="Technical Debt" description="Code quality issues detected" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.map((item) => (
          <DebtCard key={item.id} data={item} />
        ))}
      </div>
    </section>
  );
}
