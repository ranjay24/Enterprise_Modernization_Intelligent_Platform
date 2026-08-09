import { Select } from '@/components/ui/Select';
import { cn } from '@/utils/cn';
import type { JobResponse } from '@/types';

interface CompletedJobSelectorProps {
  jobs: JobResponse[];
  selectedJobId?: string;
  onChange: (jobId: string) => void;
  className?: string;
}

export function CompletedJobSelector({ jobs, selectedJobId, onChange, className }: CompletedJobSelectorProps) {
  if (jobs.length <= 1) return null;

  const options = jobs.map((j) => ({
    value: j.job_id,
    label: `${j.filename.replace(/\.zip$/i, '').replace(/[-_]/g, ' ')} — ${new Date(j.created_at).toLocaleDateString()}`,
  }));

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <span className="text-sm text-muted-foreground whitespace-nowrap">Project:</span>
      <Select
        className="w-64"
        value={selectedJobId || ''}
        onChange={(e) => onChange(e.target.value)}
        options={options}
      />
    </div>
  );
}
