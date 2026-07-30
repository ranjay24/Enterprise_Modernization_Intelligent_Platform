import type { ADRPreview as ADRPreviewType } from '@/types/dashboard';
import { ADRCardNew } from '@/components/cards/ADRCardNew';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function ADRPreview({ data }: { data: ADRPreviewType[] }) {
  return (
    <section>
      <SectionHeader title="ADR Preview" description="Architecture Decision Records" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data.map((adr) => (
          <ADRCardNew key={adr.id} data={adr} />
        ))}
      </div>
    </section>
  );
}
