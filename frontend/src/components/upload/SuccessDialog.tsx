import React from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle, ArrowRight, LayoutDashboard } from 'lucide-react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import type { UploadSuccessData } from '@/types/upload';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

interface SuccessDialogProps {
  data: UploadSuccessData;
  onDismiss: () => void;
}

export function SuccessDialog({ data, onDismiss }: SuccessDialogProps) {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4"
      onClick={onDismiss}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-card rounded-2xl border shadow-xl max-w-md w-full p-8 text-center"
        onClick={(e) => e.stopPropagation()}
      >
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, delay: 0.2 }}
          className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mx-auto mb-6"
        >
          <CheckCircle className="w-8 h-8 text-green-600 dark:text-green-400" />
        </motion.div>

        <h2 className="text-xl font-bold text-foreground mb-2">Upload Successful</h2>
        <p className="text-sm text-muted-foreground mb-6">Your project has been uploaded and is ready for analysis.</p>

        <div className="grid grid-cols-2 gap-3 text-sm mb-6">
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-muted-foreground text-xs">Project</p>
            <p className="font-medium text-foreground">{data.projectName}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-muted-foreground text-xs">File Size</p>
            <p className="font-medium text-foreground">{formatBytes(data.fileSize)}</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-muted-foreground text-xs">Job ID</p>
            <p className="font-medium text-foreground font-mono text-xs">{data.jobId.slice(0, 12)}...</p>
          </div>
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-muted-foreground text-xs">Upload Time</p>
            <p className="font-medium text-foreground">{data.uploadTime}s</p>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <Button
            onClick={() => navigate(`/jobs/${data.jobId}`)}
            className="w-full"
          >
            Start Analysis
            <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
          <Button
            variant="ghost"
            onClick={() => navigate('/dashboard')}
            className="w-full"
          >
            <LayoutDashboard className="w-4 h-4 mr-1" />
            Return to Dashboard
          </Button>
        </div>
      </motion.div>
    </motion.div>
  );
}
