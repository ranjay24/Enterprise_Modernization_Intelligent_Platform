import { Link } from 'react-router-dom';
import { Clock, ChevronRight } from 'lucide-react';
import { formatDate } from '@/utils/formatters';
import { JobStatusBadge } from './JobStatusBadge';
import type { JobResponse } from '@/types';

export function JobCard({ job }: { job: JobResponse }) {
  return (
    <Link
      to={`/jobs/${job.job_id}`}
      className="block border rounded-xl p-4 hover:bg-accent/50 transition-colors group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <JobStatusBadge status={job.status} />
          <div className="min-w-0">
            <p className="font-medium text-foreground truncate">{job.filename}</p>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
              <Clock className="w-3 h-3" />
              {formatDate(job.created_at)}
              <span className="text-muted-foreground/50">|</span>
              <span className="font-mono">{job.job_id.slice(0, 8)}</span>
            </div>
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition-colors shrink-0" />
      </div>
    </Link>
  );
}
