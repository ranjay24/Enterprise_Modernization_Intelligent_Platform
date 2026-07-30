import React from 'react';
import { AlertTriangle, RefreshCw, Wifi, ServerCrash } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import { Button } from '@/components/ui/Button';

type ErrorType = 'invalid_zip' | 'upload_failed' | 'network_error' | 'backend_unavailable';

interface ErrorBannerProps {
  type: ErrorType;
  message?: string;
  onRetry?: () => void;
}

const errorConfig: Record<ErrorType, { title: string; description: string; icon: React.ElementType }> = {
  invalid_zip: {
    title: 'Invalid ZIP File',
    description: 'The uploaded file is not a valid ZIP archive. Please ensure the file is not corrupted.',
    icon: AlertTriangle,
  },
  upload_failed: {
    title: 'Upload Failed',
    description: 'Something went wrong during the upload. Please try again.',
    icon: RefreshCw,
  },
  network_error: {
    title: 'Network Error',
    description: 'Unable to connect to the server. Please check your internet connection.',
    icon: Wifi,
  },
  backend_unavailable: {
    title: 'Service Unavailable',
    description: 'The backend service is currently unavailable. Please try again later.',
    icon: ServerCrash,
  },
};

export function ErrorBanner({ type, message, onRetry }: ErrorBannerProps) {
  const config = errorConfig[type];
  const Icon = config.icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn(
        'w-full max-w-2xl mx-auto border rounded-xl p-5',
        'border-destructive/30 bg-destructive/5'
      )}
    >
      <div className="flex items-start gap-4">
        <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
          <Icon className="w-5 h-5 text-destructive" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-foreground">{config.title}</p>
          <p className="text-sm text-muted-foreground mt-0.5">{message || config.description}</p>
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry} className="shrink-0">
            <RefreshCw className="w-3.5 h-3.5 mr-1" />
            Retry
          </Button>
        )}
      </div>
    </motion.div>
  );
}
