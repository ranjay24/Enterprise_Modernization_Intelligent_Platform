import { useLocation, useNavigate } from 'react-router-dom';
import { Sun, Moon, Monitor, Bell, Search, Sparkles, X, LogOut } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { useNotifications, type AppNotification } from '@/hooks/useNotifications';
import { useAuth } from '@/auth/AuthContext';
import { DemoModeToggle } from '@/components/ui/DemoModeToggle';
import { useAppStore } from '@/store/useAppStore';
import { cn } from '@/utils/cn';
import { useState } from 'react';
import type { JobStatus } from '@/types';

const routeLabels: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/upload': 'Analyze Code',
  '/jobs': 'Jobs',
  '/architecture': 'Architecture',
  '/migration': 'Migration Planner',
  '/reports': 'Reports',
  '/settings': 'Settings',
};

const NOTIFY_STYLE: Record<JobStatus, { dot: string; label: string; text: string }> = {
  uploaded: { dot: 'bg-[var(--text-muted)]', label: 'Uploaded', text: 'text-[var(--text-muted)]' },
  analyzing: { dot: 'bg-[var(--accent-blue)] animate-pulse', label: 'Analyzing', text: 'text-[var(--accent-blue)]' },
  paused: { dot: 'bg-[var(--warning)]', label: 'Paused', text: 'text-[var(--warning)]' },
  cancelled: { dot: 'bg-[var(--text-muted)]', label: 'Cancelled', text: 'text-[var(--text-muted)]' },
  analysis_complete: { dot: 'bg-[var(--success)]', label: 'Complete', text: 'text-[var(--success)]' },
  generating: { dot: 'bg-[var(--accent-purple)] animate-pulse', label: 'Generating', text: 'text-[var(--accent-purple)]' },
  generation_complete: { dot: 'bg-[var(--success)]', label: 'Complete', text: 'text-[var(--success)]' },
  generation_with_warnings: { dot: 'bg-[var(--warning)]', label: 'With warnings', text: 'text-[var(--warning)]' },
  failed: { dot: 'bg-[var(--risk)]', label: 'Failed', text: 'text-[var(--risk)]' },
  deployed: { dot: 'bg-[var(--success)]', label: 'Deployed', text: 'text-[var(--success)]' },
};

function relativeTime(at: number): string {
  const seconds = Math.max(1, Math.round((Date.now() - at) / 1000));
  if (seconds < 60) return 'just now';
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

function notifyRoute(n: AppNotification): string {
  if (n.status === 'analysis_complete' || n.status === 'generation_complete' || n.status === 'generation_with_warnings') {
    return `/jobs/${n.jobId}/results`;
  }
  return `/jobs/${n.jobId}`;
}

export function TopNav() {
  const { theme, cycleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const { sidebarCollapsed } = useAppStore();
  const { user, status, logout } = useAuth();
  const { notifications, unseen, toast, markSeen, dismissToast, demoMode } = useNotifications();
  const [showNotifications, setShowNotifications] = useState(false);

  const currentLabel = routeLabels[location.pathname] || 'EMIP';

  const themeIcons = {
    light: <Sun className="w-4 h-4" />,
    dark: <Moon className="w-4 h-4" />,
    system: <Monitor className="w-4 h-4" />,
  };

  function toggleNotifications() {
    const next = !showNotifications;
    setShowNotifications(next);
    if (next) markSeen();
  }

  return (
    <header className="h-12 border-b border-[var(--border-subtle)] bg-[var(--bg-elevated)] flex items-center justify-between px-4 sticky top-0 z-20">
      <div className="flex items-center gap-3 min-w-0">
        <h2 className="text-[15px] font-semibold text-[var(--text-primary)] truncate">{currentLabel}</h2>
        <span className="hidden sm:inline text-xs text-[var(--text-muted)]">/</span>
        <span className="hidden sm:inline text-xs text-[var(--text-muted)] truncate">
          Enterprise Modernization Intelligence Platform
        </span>
      </div>

      <div className="flex items-center gap-1">
        {/* Global search shortcut */}
        {sidebarCollapsed && (
          <button
            className="p-2 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            title="Search"
          >
            <Search className="w-4 h-4" />
          </button>
        )}

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={toggleNotifications}
            className="p-2 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors relative"
            title="Notifications"
            aria-label="Notifications"
          >
            <Bell className="w-4 h-4" />
            {unseen > 0 ? (
              <>
                <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--risk)] opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--risk)] ring-1 ring-[var(--bg-elevated)]" />
                </span>
                <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-full bg-[var(--risk)] text-white text-[9px] font-bold flex items-center justify-center ring-1 ring-[var(--bg-elevated)]">
                  {unseen > 9 ? '9+' : unseen}
                </span>
              </>
            ) : (
              <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--text-muted)]/40 ring-1 ring-[var(--bg-elevated)]" />
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 top-full mt-1 w-80 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-xl animate-fade-up overflow-hidden z-30">
              <div className="flex items-center justify-between p-3 border-b border-[var(--border-subtle)]">
                <p className="text-sm font-semibold text-[var(--text-primary)]">Notifications</p>
                {demoMode && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[var(--warning)]/10 text-[var(--warning)]">
                    sample
                  </span>
                )}
              </div>
              {notifications.length === 0 ? (
                <div className="p-4 text-sm text-[var(--text-muted)] text-center">
                  No new notifications
                </div>
              ) : (
                <ul className="max-h-80 overflow-y-auto">
                  {notifications.map((n) => {
                    const style = NOTIFY_STYLE[n.status] ?? NOTIFY_STYLE.uploaded;
                    return (
                      <li key={n.id}>
                        <button
                          onClick={() => {
                            setShowNotifications(false);
                            navigate(notifyRoute(n));
                          }}
                          className="flex items-start gap-3 w-full px-3 py-2.5 text-left hover:bg-[var(--border-subtle)]/50 transition-colors"
                        >
                          <span className={cn('mt-1.5 h-2 w-2 rounded-full shrink-0', style.dot)} />
                          <span className="flex-1 min-w-0">
                            <span className="block text-sm text-[var(--text-primary)] truncate">
                              {n.title}
                            </span>
                            <span className="block text-[11px] text-[var(--text-muted)] mt-0.5">
                              {relativeTime(n.at)}
                            </span>
                          </span>
                          <span className={cn('text-[10px] font-semibold uppercase tracking-wide shrink-0', style.text)}>
                            {style.label}
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          )}
        </div>

        <DemoModeToggle />

        {/* Theme toggle */}
        <button
          onClick={cycleTheme}
          className="p-2 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
          title={`Theme: ${theme}`}
        >
          {themeIcons[theme]}
        </button>

        {/* User chip */}
        {status === 'authenticated' && user && (
          <div className="flex items-center gap-1 pl-1 ml-1 border-l border-[var(--border-subtle)]">
            <div className="flex flex-col items-end leading-tight pr-0.5">
              <span className="text-xs font-medium text-[var(--text-primary)] max-w-[120px] truncate">
                {user.name}
              </span>
              <span className="text-[10px] text-[var(--text-muted)] max-w-[140px] truncate">
                {user.email}
              </span>
            </div>
            <button
              onClick={logout}
              className="p-2 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--risk)] transition-colors"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Notification toast — slides in from the top right on terminal events */}
      {toast && (
        <div
          className="fixed top-16 right-4 z-50 w-80 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-2xl animate-slide-down overflow-hidden"
          role="status"
        >
          <div className="flex items-start gap-3 p-3">
            <span className={cn('mt-1.5 h-2 w-2 rounded-full shrink-0', NOTIFY_STYLE[toast.status]?.dot)} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--text-primary)] truncate">{toast.title}</p>
              <p className="text-[11px] text-[var(--text-muted)] mt-0.5">
                {NOTIFY_STYLE[toast.status]?.label} · {relativeTime(toast.at)}
              </p>
            </div>
            <button
              onClick={() => {
                dismissToast();
                navigate(notifyRoute(toast));
              }}
              className="shrink-0 text-xs font-semibold text-[var(--accent-blue)] hover:underline"
            >
              View
            </button>
            <button
              onClick={dismissToast}
              className="shrink-0 p-1 rounded hover:bg-[var(--border-subtle)] text-[var(--text-muted)]"
              aria-label="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <Sparkles className="absolute -top-1 -right-1 w-6 h-6 text-[var(--accent-purple)]/20" />
        </div>
      )}
    </header>
  );
}
