import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ExternalLink, RotateCcw } from 'lucide-react';
import { ReusableTable } from '@/components/ui/ReusableTable';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import type { UploadHistoryEntry } from '@/types/upload';

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const statusVariant: Record<string, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  completed: 'success',
  in_progress: 'warning',
  failed: 'destructive',
  pending: 'secondary',
};

const statusLabel: Record<string, string> = {
  completed: 'Completed',
  in_progress: 'In Progress',
  failed: 'Failed',
  pending: 'Pending',
};

interface HistoryTableProps {
  data: UploadHistoryEntry[];
  onRetry?: (entry: UploadHistoryEntry) => void;
}

export function HistoryTable({ data, onRetry }: HistoryTableProps) {
  const navigate = useNavigate();

  const columns = [
    {
      key: 'projectName',
      header: 'Project',
      render: (item: UploadHistoryEntry) => (
        <div>
          <p className="font-medium text-foreground">{item.projectName}</p>
          <p className="text-xs text-muted-foreground">{item.fileName}</p>
        </div>
      ),
    },
    {
      key: 'version',
      header: 'Version',
      render: (item: UploadHistoryEntry) => <span className="text-muted-foreground">{item.version}</span>,
    },
    {
      key: 'uploadDate',
      header: 'Upload Date',
      render: (item: UploadHistoryEntry) => <span className="text-muted-foreground">{formatDate(item.uploadDate)}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      render: (item: UploadHistoryEntry) => (
        <Badge variant={statusVariant[item.status]}>{statusLabel[item.status]}</Badge>
      ),
    },
    {
      key: 'readiness',
      header: 'Last Analysis',
      render: (item: UploadHistoryEntry) => (
        item.readiness !== null
          ? <span className="font-medium text-foreground">{item.readiness}/100</span>
          : <span className="text-muted-foreground">—</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      render: (item: UploadHistoryEntry) => (
        <div className="flex items-center gap-1">
          {item.jobId && item.status === 'completed' && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => navigate(`/jobs/${item.jobId}/results`)}>
              <ExternalLink className="w-3.5 h-3.5" />
            </Button>
          )}
          {item.status === 'failed' && onRetry && (
            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => onRetry(item)}>
              <RotateCcw className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-foreground mb-3">Upload History</h3>
      <div className="border rounded-xl overflow-hidden">
        <ReusableTable data={data} columns={columns} emptyMessage="No uploads yet" />
      </div>
    </div>
  );
}
