import { Sparkles } from 'lucide-react';
import { APP_VERSION } from '@/utils/constants';

export function Footer() {
  return (
    <footer className="h-8 border-t border-[var(--border-subtle)] bg-[var(--bg-elevated)] flex items-center justify-between px-4 text-[10px] text-[var(--text-muted)] shrink-0">
      <div className="flex items-center gap-1">
        <Sparkles className="w-2.5 h-2.5" />
        <span>EMIP v{APP_VERSION}</span>
      </div>
      <div className="flex items-center gap-3">
        <span>Powered by Amazon Bedrock</span>
        <span className="w-px h-3 bg-[var(--border-subtle)]" />
        <button className="hover:text-[var(--text-primary)] transition-colors">Privacy</button>
        <span className="w-px h-3 bg-[var(--border-subtle)]" />
        <button className="hover:text-[var(--text-primary)] transition-colors">Terms</button>
      </div>
    </footer>
  );
}
