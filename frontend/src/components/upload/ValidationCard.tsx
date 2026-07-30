import React from 'react';
import { CheckCircle, XCircle, Loader2, AlertTriangle, Circle } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import type { UploadValidation } from '@/types/upload';

const statusConfig = {
  pending: { icon: Circle, color: 'text-muted-foreground', bg: 'bg-muted' },
  pass: { icon: CheckCircle, color: 'text-green-600 dark:text-green-400', bg: 'bg-green-50 dark:bg-green-900/20' },
  fail: { icon: XCircle, color: 'text-destructive', bg: 'bg-destructive/10' },
  warning: { icon: AlertTriangle, color: 'text-yellow-600 dark:text-yellow-400', bg: 'bg-yellow-50 dark:bg-yellow-900/20' },
};

interface ValidationCardProps {
  validations: UploadValidation[];
}

export function ValidationCard({ validations }: ValidationCardProps) {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <h3 className="text-sm font-semibold text-foreground mb-3">Pre-Upload Validation</h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {validations.map((v, i) => {
          const config = statusConfig[v.status];
          const Icon = config.icon;
          return (
            <motion.div
              key={v.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className={cn(
                'flex items-center gap-3 p-3 rounded-lg border transition-colors',
                v.status === 'pass' && 'border-green-200 dark:border-green-800',
                v.status === 'fail' && 'border-destructive/30',
                v.status === 'warning' && 'border-yellow-200 dark:border-yellow-800',
                v.status === 'pending' && 'border-muted'
              )}
            >
              <div className={cn('w-8 h-8 rounded-full flex items-center justify-center shrink-0', config.bg)}>
                {v.status === 'pending' ? (
                  <Circle className="w-4 h-4 text-muted-foreground" />
                ) : v.status === 'pass' ? (
                  <CheckCircle className="w-4 h-4 text-green-600 dark:text-green-400" />
                ) : v.status === 'fail' ? (
                  <XCircle className="w-4 h-4 text-destructive" />
                ) : v.status === 'warning' ? (
                  <AlertTriangle className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                ) : (
                  <Icon className={cn('w-4 h-4', config.color)} />
                )}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{v.label}</p>
                <p className="text-xs text-muted-foreground truncate">{v.description}</p>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
