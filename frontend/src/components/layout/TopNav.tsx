import { useLocation } from 'react-router-dom';
import { Sun, Moon, Monitor, Bell, Search, Sparkles } from 'lucide-react';
import { useTheme } from '@/hooks/useTheme';
import { DemoModeToggle } from '@/components/ui/DemoModeToggle';
import { cn } from '@/utils/cn';
import { useAppStore } from '@/store/useAppStore';
import { useState } from 'react';

const routeLabels: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/upload': 'Analyze Code',
  '/jobs': 'Jobs',
  '/architecture': 'Architecture',
  '/migration': 'Migration Planner',
  '/reports': 'Reports',
  '/settings': 'Settings',
};

export function TopNav() {
  const { theme, cycleTheme } = useTheme();
  const location = useLocation();
  const { sidebarCollapsed } = useAppStore();
  const [showNotifications, setShowNotifications] = useState(false);

  const currentLabel = routeLabels[location.pathname] || 'EMIP';

  const themeIcons = {
    light: <Sun className="w-4 h-4" />,
    dark: <Moon className="w-4 h-4" />,
    system: <Monitor className="w-4 h-4" />,
  };

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
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-lg hover:bg-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors relative"
            title="Notifications"
          >
            <Bell className="w-4 h-4" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--risk)] ring-1 ring-[var(--bg-elevated)]" />
          </button>
          {showNotifications && (
            <div className="absolute right-0 top-full mt-1 w-72 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-xl animate-fade-up overflow-hidden">
              <div className="p-3 border-b border-[var(--border-subtle)]">
                <p className="text-sm font-semibold text-[var(--text-primary)]">Notifications</p>
              </div>
              <div className="p-4 text-sm text-[var(--text-muted)] text-center">
                No new notifications
              </div>
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
      </div>
    </header>
  );
}
