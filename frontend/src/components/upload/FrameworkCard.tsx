import React from 'react';
import { Leaf, Coffee, Package, Boxes, Server, Braces, Code, Check, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/utils/cn';
import { Badge } from '@/components/ui/Badge';
import type { SupportedFramework } from '@/types/upload';

const iconMap: Record<string, React.ElementType> = {
  Leaf, Coffee, Package, Boxes, Server, Braces, Code,
};

interface FrameworkCardProps {
  frameworks: SupportedFramework[];
}

export function FrameworkCard({ frameworks }: FrameworkCardProps) {
  return (
    <div className="w-full">
      <h3 className="text-sm font-semibold text-foreground mb-3">Supported Frameworks</h3>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {frameworks.map((fw, i) => {
          const Icon = iconMap[fw.icon] || Code;
          return (
            <motion.div
              key={fw.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
              className={cn(
                'relative flex flex-col items-center p-4 rounded-xl border text-center transition-all',
                fw.supported
                  ? 'border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-900/10 hover:shadow-sm'
                  : 'border-muted bg-muted/30 opacity-60'
              )}
            >
              {fw.supported && (
                <div className="absolute top-2 right-2">
                  <Check className="w-3.5 h-3.5 text-green-600 dark:text-green-400" />
                </div>
              )}
              <div className={cn(
                'w-10 h-10 rounded-lg flex items-center justify-center mb-2',
                fw.supported ? 'bg-green-100 dark:bg-green-900/30' : 'bg-muted'
              )}>
                <Icon className={cn('w-5 h-5', fw.supported ? 'text-green-700 dark:text-green-400' : 'text-muted-foreground')} />
              </div>
              <p className="text-sm font-medium text-foreground">{fw.name}</p>
              {fw.version && (
                <Badge variant="secondary" className="mt-1 text-[10px]">{fw.version}</Badge>
              )}
              {!fw.supported && (
                <Badge variant="outline" className="mt-1 text-[10px] text-muted-foreground">
                  <ArrowRight className="w-2.5 h-2.5 mr-0.5" /> Coming Soon
                </Badge>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
