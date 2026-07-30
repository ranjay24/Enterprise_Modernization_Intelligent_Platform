import type { ADR } from '@/types/api';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { ADRCard } from '@/components/cards/ADRCard';
import { Badge } from '@/components/ui/Badge';

export function ADRCenter({ adrs }: { adrs: ADR[] }) {
  const accepted = adrs.filter((a) => a.status === 'accepted').length;
  const proposed = adrs.filter((a) => a.status === 'proposed').length;

  return (
    <section>
      <SectionHeader
        title="ADR Center"
        description={`${adrs.length} Architecture Decision Records`}
        action={
          <div className="flex items-center gap-2">
            {accepted > 0 && <Badge variant="success">{accepted} Accepted</Badge>}
            {proposed > 0 && <Badge variant="outline">{proposed} Proposed</Badge>}
          </div>
        }
      />
      <div className="space-y-3">
        {adrs.map((adr) => (
          <ADRCard key={adr.id} adr={adr} />
        ))}
        {adrs.length === 0 && (
          <div className="bg-card rounded-xl border p-8 text-center">
            <p className="text-muted-foreground">No ADRs generated yet.</p>
          </div>
        )}
      </div>
    </section>
  );
}
