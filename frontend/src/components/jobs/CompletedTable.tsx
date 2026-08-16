import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, FileText, Download } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ReusableTable } from '@/components/ui/ReusableTable';
import type { JobDetail } from '@/types/jobs';
import { formatDate } from '@/utils/formatters';

function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

const riskVariant: Record<string, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  low: 'success',
  medium: 'warning',
  high: 'destructive',
};

interface CompletedTableProps {
  jobs: JobDetail[];
}

export function CompletedTable({ jobs }: CompletedTableProps) {
  const navigate = useNavigate();

  const columns = [
    {
      key: 'projectName',
      header: 'Project',
      render: (item: JobDetail) => (
        <div>
          <p className="font-medium text-foreground">{item.projectName}</p>
          <p className="text-xs text-muted-foreground font-mono">{item.fileName}</p>
        </div>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      render: (item: JobDetail) => <span className="text-muted-foreground">{item.metadata.version}</span>,
    },
    {
      key: 'completedAt',
      header: 'Completed',
      render: (item: JobDetail) => (
        <span className="text-muted-foreground text-sm">{item.completedAt ? formatDate(item.completedAt) : '—'}</span>
      ),
    },
    {
      key: 'readinessScore',
      header: 'Readiness',
      render: (item: JobDetail) => (
        item.readinessScore !== null
          ? <span className="font-semibold text-foreground">{item.readinessScore}/100</span>
          : <span className="text-muted-foreground">—</span>
      ),
    },
    {
      key: 'riskLevel',
      header: 'Risk',
      render: (item: JobDetail) => (
        item.riskLevel
          ? <Badge variant={riskVariant[item.riskLevel]}>{item.riskLevel}</Badge>
          : <span className="text-muted-foreground">—</span>
      ),
    },
    {
      key: 'aiConfidence',
      header: 'Confidence',
      render: (item: JobDetail) => (
        item.aiConfidence !== null
          ? <span className="text-foreground">{item.aiConfidence}%</span>
          : <span className="text-muted-foreground">—</span>
      ),
    },
    {
      key: 'elapsed',
      header: 'Duration',
      render: (item: JobDetail) => <span className="text-muted-foreground">{formatElapsed(item.elapsed)}</span>,
    },
    {
      key: 'actions',
      header: '',
      render: (item: JobDetail) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => navigate(`/jobs/${item.id}/results`)}>
            <ExternalLink className="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" disabled title="Coming soon">
            <FileText className="w-3.5 h-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" disabled title="Coming soon">
            <Download className="w-3.5 h-3.5" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="border rounded-xl overflow-hidden">
      <ReusableTable data={jobs} columns={columns} emptyMessage="No completed analyses" />
    </div>
  );
}
