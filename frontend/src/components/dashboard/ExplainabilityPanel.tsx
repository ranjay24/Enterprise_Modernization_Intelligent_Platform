import { useState, useCallback } from 'react';
import type { ExplainabilityEntry } from '@/types/dashboard';
import { ExplainabilityCard } from '@/components/cards/ExplainabilityCard';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function ExplainabilityPanel({ data }: { data: ExplainabilityEntry[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggle = useCallback((id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  }, []);

  return (
    <section>
      <SectionHeader title="Explainability Panel" description="Why these services were identified" />
      <div className="space-y-3">
        {data.map((entry) => (
          <ExplainabilityCard
            key={entry.id}
            data={entry}
            expanded={expandedId === entry.id}
            onToggle={() => toggle(entry.id)}
          />
        ))}
      </div>
    </section>
  );
}
