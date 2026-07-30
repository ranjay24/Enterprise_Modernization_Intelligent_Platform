import type { AIRecommendation } from '@/types/dashboard';
import { RecommendationCard } from '@/components/cards/RecommendationCard';
import { SectionHeader } from '@/components/ui/SectionHeader';

export function AIRecommendations({ data }: { data: AIRecommendation[] }) {
  return (
    <section>
      <SectionHeader title="AI Recommendations" description="AI-powered migration recommendations" />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {data.map((rec) => (
          <RecommendationCard key={rec.id} data={rec} />
        ))}
      </div>
    </section>
  );
}
