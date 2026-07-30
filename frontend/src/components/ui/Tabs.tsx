import { useState } from 'react';
import { cn } from '@/utils/cn';

interface Tab {
  id: string;
  label: string;
  badge?: string | number;
  icon?: React.ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  activeTab?: string;
  onChange?: (tabId: string) => void;
  className?: string;
  variant?: 'underline' | 'pills' | 'segmented';
  children?: React.ReactNode;
}

export function Tabs({ tabs, activeTab, onChange, className, variant = 'underline', children }: TabsProps) {
  const [internal, setInternal] = useState(tabs[0]?.id ?? '');
  const selected = activeTab ?? internal;

  const handleChange = (id: string) => {
    setInternal(id);
    onChange?.(id);
  };

  return (
    <div className={className}>
      <div className={cn(
        'flex',
        variant === 'underline' && 'border-b gap-0',
        variant === 'pills' && 'gap-1',
        variant === 'segmented' && 'rounded-lg bg-muted p-1 gap-0',
      )}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => handleChange(tab.id)}
            className={cn(
              'flex items-center gap-1.5 whitespace-nowrap text-sm font-medium transition-all duration-fast',
              variant === 'underline' && cn(
                'px-4 py-2.5 border-b-2 border-transparent -mb-px',
                'hover:text-foreground',
                selected === tab.id ? 'border-primary text-foreground' : 'text-muted-foreground'
              ),
              variant === 'pills' && cn(
                'px-3 py-1.5 rounded-md',
                'hover:bg-accent hover:text-accent-foreground',
                selected === tab.id ? 'bg-accent text-accent-foreground' : 'text-muted-foreground'
              ),
              variant === 'segmented' && cn(
                'px-4 py-1.5 rounded-md text-[13px]',
                selected === tab.id ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground'
              ),
            )}
          >
            {tab.icon}
            {tab.label}
            {tab.badge != null && (
              <span className={cn(
                'inline-flex items-center justify-center min-w-[18px] h-[18px] rounded-full px-1 text-[10px] font-medium',
                selected === tab.id ? 'bg-primary/10 text-primary' : 'bg-muted-foreground/10 text-muted-foreground'
              )}>
                {tab.badge}
              </span>
            )}
          </button>
        ))}
      </div>
      {children && (
        <div className="mt-4">
          {Array.isArray(children) ? children[tabs.findIndex(t => t.id === selected)] : children}
        </div>
      )}
    </div>
  );
}
