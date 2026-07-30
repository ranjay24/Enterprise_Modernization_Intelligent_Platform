import { Download, FileText, Code, FileJson } from 'lucide-react';
import { cn } from '@/utils/cn';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { Badge } from '@/components/ui/Badge';
import type { ExportOption } from '@/types/results';

const formatIcons: Record<string, React.ElementType> = {
  pdf: FileText,
  json: FileJson,
  markdown: Code,
};

const formatColors: Record<string, string> = {
  pdf: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50',
  json: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300 hover:bg-green-200 dark:hover:bg-green-900/50',
  markdown: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50',
};

export function ExportCenter({ exports: exportOptions }: { exports: ExportOption[] }) {
  return (
    <section>
      <SectionHeader
        title="Export Center"
        description="Download reports in your preferred format"
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {exportOptions.map((option) => (
          <article key={option.id} className="bg-card rounded-xl border p-5 hover:shadow-md transition-all">
            <div className="flex items-start justify-between mb-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Download className="w-5 h-5 text-primary" />
              </div>
              <Badge variant="outline">{option.formats.length} formats</Badge>
            </div>
            <h3 className="font-semibold text-foreground text-sm mb-1">{option.name}</h3>
            <p className="text-xs text-muted-foreground mb-3">{option.description}</p>
            <div className="text-xs text-muted-foreground mb-3">
              <span className="font-medium">Includes:</span>{' '}
              {option.sections.join(', ')}
            </div>
            <div className="flex flex-wrap gap-2">
              {option.formats.map((fmt) => {
                const FmtIcon = formatIcons[fmt] || FileText;
                return (
                  <button
                    key={fmt}
                    className={cn(
                      'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors',
                      formatColors[fmt],
                    )}
                  >
                    <FmtIcon className="w-3 h-3" />
                    Export as {fmt.toUpperCase()}
                  </button>
                );
              })}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
