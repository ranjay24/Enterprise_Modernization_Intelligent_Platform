import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  ListTodo,
  GitBranch,
  FileText,
  Settings,
  ChevronLeft,
  ChevronRight,
  Search,
  Command,
  BarChart3,
  Layers,
  Code2,
  Bell,
  Clock,
  Sparkles,
  User,
  ChevronDown,
  Wand2,
} from 'lucide-react';
import { cn } from '@/utils/cn';
import { useAppStore } from '@/store/useAppStore';
import { useState } from 'react';
import { Input } from '@/components/ui/Input';

interface NavGroup {
  label: string;
  items: { to: string; icon: React.ElementType; label: string }[];
}

const navGroups: NavGroup[] = [
  {
    label: 'Overview',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/upload', icon: Upload, label: 'Analyze Code' },
      { to: '/jobs', icon: ListTodo, label: 'Jobs' },
    ],
  },
  {
    label: 'Analysis',
    items: [
      { to: '/architecture', icon: GitBranch, label: 'Architecture' },
      { to: '/migration', icon: Layers, label: 'Migration' },
      { to: '/reports', icon: BarChart3, label: 'Reports' },
    ],
  },
  {
    label: 'Modernization',
    items: [
      { to: '/studio', icon: Wand2, label: 'Modernization Studio' },
    ],
  },
  {
    label: 'Settings',
    items: [
      { to: '/settings', icon: Settings, label: 'Settings' },
    ],
  },
];

const flatNavItems = navGroups.flatMap((g) => g.items);

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useAppStore();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const navigate = useNavigate();

  const filtered = searchQuery
    ? flatNavItems.filter((i) => i.label.toLowerCase().includes(searchQuery.toLowerCase()))
    : flatNavItems;

  const handleSelect = (to: string) => {
    navigate(to);
    setSearchOpen(false);
    setSearchQuery('');
  };

  return (
    <>
      <aside
        className={cn(
          'h-screen flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-elevated)] sticky top-0 z-30',
          'transition-all duration-300 ease-[var(--ease-out)]',
          sidebarCollapsed ? 'w-[52px]' : 'w-60'
        )}
      >
        {/* ── Logo area ── */}
        <div className={cn(
          'flex items-center h-12 shrink-0',
          sidebarCollapsed ? 'justify-center px-2' : 'justify-between px-4'
        )}>
          {!sidebarCollapsed ? (
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center shrink-0">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-[13px] font-bold text-[var(--text-primary)] leading-tight">EMIP</h1>
                <p className="text-[9px] text-[var(--text-muted)] leading-tight truncate">Modernization Intel</p>
              </div>
            </div>
          ) : (
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
          )}
        </div>

        {/* ── Search ── */}
        <div className={cn('px-2 pb-2', sidebarCollapsed && 'flex justify-center')}>
          <button
            onClick={() => !sidebarCollapsed && setSearchOpen(true)}
            onDoubleClick={() => sidebarCollapsed && setSearchOpen(true)}
            className={cn(
              'flex items-center gap-2 w-full rounded-lg text-xs transition-colors',
              sidebarCollapsed
                ? 'justify-center h-8 w-8 mx-auto hover:bg-[var(--sidebar-hover)] text-[var(--text-muted)]'
                : 'px-2.5 h-8 hover:bg-[var(--sidebar-hover)] text-[var(--text-muted)] border border-[var(--border-subtle)]'
            )}
          >
            <Search className="w-3.5 h-3.5 shrink-0" />
            {!sidebarCollapsed && (
              <>
                <span className="flex-1 text-left">Search...</span>
                <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded border border-[var(--border-subtle)] bg-[var(--bg-card)] text-[10px] text-[var(--text-muted)]">
                  <Command className="w-2.5 h-2.5" />K
                </kbd>
              </>
            )}
          </button>
        </div>

        {/* ── Navigation groups ── */}
        <nav className="flex-1 px-2 pb-3 overflow-y-auto overflow-x-hidden space-y-4">
          {navGroups.map((group) => (
            <div key={group.label}>
              {!sidebarCollapsed && (
                <p className="px-2.5 pb-1 text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-widest">
                  {group.label}
                </p>
              )}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  return (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center rounded-lg text-sm transition-all duration-[var(--duration-fast)]',
                          sidebarCollapsed ? 'justify-center h-9 w-9 mx-auto' : 'gap-2.5 px-2.5 h-9',
                          isActive
                            ? sidebarCollapsed
                              ? 'text-[var(--accent-blue)] bg-[var(--accent-blue)]/10'
                              : 'text-[var(--accent-blue)] bg-[var(--accent-blue)]/8 border-l-2 border-[var(--accent-blue)] -ml-px'
                            : 'text-[var(--text-muted)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)]'
                        )
                      }
                    >
                      <Icon className={cn('shrink-0', sidebarCollapsed ? 'w-[18px] h-[18px]' : 'w-[18px] h-[18px]')} />
                      {!sidebarCollapsed && (
                        <span className="truncate text-[13px]">{item.label}</span>
                      )}
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* ── Recent analyses section ── */}
        {!sidebarCollapsed && (
          <div className="px-3 py-2 border-t border-[var(--border-subtle)]">
            <p className="text-[10px] font-semibold text-[var(--text-muted)] uppercase tracking-widest mb-2">Recent</p>
            <div className="space-y-1">
              {['E-Commerce Monolith', 'Banking Platform'].map((name) => (
                <button
                  key={name}
                  className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-[var(--text-muted)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)] transition-colors text-left"
                >
                  <Clock className="w-3.5 h-3.5 shrink-0" />
                  <span className="truncate">{name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── User section ── */}
        {!sidebarCollapsed && (
          <div className="px-3 py-2 border-t border-[var(--border-subtle)]">
            <button className="flex items-center gap-2.5 w-full px-2 py-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] transition-colors">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center text-white text-xs font-bold">
                JD
              </div>
              <div className="flex-1 min-w-0 text-left">
                <p className="text-xs font-medium text-[var(--text-primary)] truncate">John Doe</p>
                <p className="text-[10px] text-[var(--text-muted)] truncate">Enterprise Plan</p>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
            </button>
          </div>
        )}

        {/* ── Collapse toggle ── */}
        <div className={cn('border-t border-[var(--border-subtle)] p-2', sidebarCollapsed && 'flex justify-center')}>
          <button
            onClick={toggleSidebar}
            className={cn(
              'rounded-lg text-[var(--text-muted)] hover:bg-[var(--sidebar-hover)] hover:text-[var(--text-primary)] transition-colors',
              sidebarCollapsed ? 'h-8 w-8 flex items-center justify-center' : 'h-8 w-full flex items-center justify-center'
            )}
            title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {sidebarCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>
      </aside>

      {/* ── Search overlay ── */}
      {searchOpen && !sidebarCollapsed && (
        <div
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="absolute left-64 top-2 w-80 bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl shadow-xl animate-fade-up overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-2">
              <Input
                icon={<Search className="w-4 h-4" />}
                placeholder="Search pages..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
            </div>
            <div className="px-1 pb-1 max-h-48 overflow-y-auto">
              {filtered.length === 0 ? (
                <p className="px-3 py-4 text-sm text-[var(--text-muted)] text-center">No results</p>
              ) : (
                filtered.map((item) => (
                  <button
                    key={item.to}
                    onClick={() => handleSelect(item.to)}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm text-[var(--text-primary)] hover:bg-[var(--border-subtle)] transition-colors"
                  >
                    <item.icon className="w-4 h-4 text-[var(--text-muted)]" />
                    {item.label}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
