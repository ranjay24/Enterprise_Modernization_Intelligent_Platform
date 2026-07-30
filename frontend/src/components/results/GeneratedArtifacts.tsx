import { FileText, Code, Server, GitBranch, Network, Layout, FileJson, Lock } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import type { GeneratedArtifact } from '@/types/results';

const iconMap: Record<string, React.ElementType> = {
  'architecture-report': Layout,
  'adr-report': GitBranch,
  'migration-plan': FileText,
  'readiness-report': FileJson,
  'dependency-graph': Network,
  'boundary-report': Layout,
  'generated-code': Code,
  'infrastructure-templates': Server,
};

const typeColors: Record<string, string> = {
  'architecture-report': 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  'adr-report': 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400',
  'migration-plan': 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400',
  'readiness-report': 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400',
  'dependency-graph': 'bg-cyan-100 dark:bg-cyan-900/30 text-cyan-600 dark:text-cyan-400',
  'boundary-report': 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400',
  'generated-code': 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400',
  'infrastructure-templates': 'bg-gray-100 dark:bg-gray-900/30 text-gray-600 dark:text-gray-400',
};

const formatBadge: Record<string, string> = {
  pdf: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
  json: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  markdown: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  html: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
};

export function GeneratedArtifacts({ artifacts }: { artifacts: GeneratedArtifact[] }) {
  const available = artifacts.filter((a) => a.available).length;
  const total = artifacts.length;

  return (
    <section>
      <SectionHeader
        title="Generated Artifacts"
        description={`${available}/${total} artifacts ready for download`}
        action={
          <Badge variant={available > 0 ? 'success' : 'outline'}>
            {available} Available
          </Badge>
        }
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {artifacts.map((artifact) => {
          const Icon = iconMap[artifact.type] || FileText;
          return (
            <article
              key={artifact.id}
              className={cn(
                'bg-card rounded-xl border p-4 transition-all',
                artifact.available ? 'hover:shadow-md cursor-pointer' : 'opacity-50',
              )}
            >
              <div className="flex items-start justify-between mb-3">
                <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center', typeColors[artifact.type])}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex items-center gap-1">
                  <span className={cn('px-1.5 py-0.5 rounded text-[10px] font-medium uppercase', formatBadge[artifact.format])}>
                    {artifact.format}
                  </span>
                  {!artifact.available && (
                    <Lock className="w-3 h-3 text-muted-foreground" />
                  )}
                </div>
              </div>
              <h3 className="font-semibold text-foreground text-sm mb-1">{artifact.name}</h3>
              <p className="text-xs text-muted-foreground mb-2 line-clamp-2">{artifact.description}</p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                {artifact.size && <span>{artifact.size}</span>}
                {!artifact.available && (
                  <span className="text-yellow-600 dark:text-yellow-400">Coming Soon</span>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
