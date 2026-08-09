import { Link } from 'react-router-dom';
import { LogOut, UserRound } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';

export function UserChip() {
  const { status, user, logout } = useAuth();

  if (status === 'authenticated' && user) {
    const initial = (user.name || user.email || 'G').charAt(0).toUpperCase();
    return (
      <div className="flex items-center gap-2.5 w-full px-2 py-1.5">
        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center text-white text-xs font-bold shrink-0">
          {initial}
        </div>
        <div className="flex-1 min-w-0 text-left">
          <p className="text-xs font-medium text-[var(--text-primary)] truncate">{user.name}</p>
          <p className="text-[10px] text-[var(--text-muted)] truncate">{user.email}</p>
        </div>
        <button
          onClick={logout}
          className="p-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--text-muted)] hover:text-[var(--risk)] transition-colors shrink-0"
          title="Sign out"
          aria-label="Sign out"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2.5 w-full px-2 py-1.5">
      <div className="w-7 h-7 rounded-full bg-[var(--border-subtle)] flex items-center justify-center text-[var(--text-muted)] shrink-0">
        <UserRound className="w-3.5 h-3.5" />
      </div>
      <div className="flex-1 min-w-0 text-left">
        <p className="text-xs font-medium text-[var(--text-primary)] truncate">Guest</p>
        <p className="text-[10px] text-[var(--text-muted)] truncate">API-key session</p>
      </div>
      <Link
        to="/login"
        className="p-1.5 rounded-lg hover:bg-[var(--sidebar-hover)] text-[var(--text-muted)] hover:text-[var(--accent-blue)] transition-colors shrink-0"
        title="Sign in"
        aria-label="Sign in"
      >
        <LogOut className="w-3.5 h-3.5 rotate-180" />
      </Link>
    </div>
  );
}
