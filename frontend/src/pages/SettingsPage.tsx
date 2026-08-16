import { useAppStore } from '@/store/useAppStore';
import { useAuth } from '@/auth/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Sun, Moon, Monitor, PanelLeftClose, PanelLeft, Info, Palette, ShieldCheck, LogOut, UserRound } from 'lucide-react';
import { cn } from '@/utils/cn';

const AUTH_LABELS: Record<string, string> = {
  loading: 'Checking session…',
  unauthenticated: 'Signed out',
  authenticated: 'Signed in',
  guest: 'Guest · API-key session',
};

export default function SettingsPage() {
  const { sidebarCollapsed, toggleSidebar, theme, setTheme } = useAppStore();
  const { status, user, logout } = useAuth();

  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto space-y-8">
      <div>
        <h1 className="text-display text-foreground mb-1">Settings</h1>
        <p className="text-body-sm text-muted-foreground">Configure platform preferences</p>
      </div>

      <div className="space-y-4">
        {/* Account */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-success" />
              Account
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-full bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center text-white font-bold shrink-0">
                {user ? (user.name || user.email || 'G').charAt(0).toUpperCase() : <UserRound className="w-5 h-5" />}
              </div>
              <div className="min-w-0">
                <p className="font-medium text-foreground truncate">{user ? user.name : 'Guest'}</p>
                <p className="text-sm text-muted-foreground truncate">
                  {user ? user.email : 'No authenticated session — requests use the API key'}
                </p>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Authentication</span>
              <span
                className={cn(
                  'text-sm font-medium',
                  status === 'authenticated' ? 'text-success' : 'text-muted-foreground'
                )}
              >
                {AUTH_LABELS[status]}
              </span>
            </div>
            {status === 'authenticated' && (
              <Button variant="outline" onClick={logout} className="gap-2">
                <LogOut className="w-4 h-4" /> Sign out
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Appearance */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="w-4 h-4 text-primary" />
              Appearance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <label className="text-sm font-medium text-foreground mb-3 block">Theme</label>
              <div className="flex gap-2">
                {(['light', 'dark', 'system'] as const).map((t) => {
                  const icons = { light: Sun, dark: Moon, system: Monitor };
                  const Icon = icons[t];
                  return (
                    <button
                      key={t}
                      onClick={() => setTheme(t)}
                      className={cn(
                        'flex items-center gap-2 px-4 py-2.5 rounded-lg border text-sm font-medium transition-all duration-fast',
                        theme === t
                          ? 'border-primary bg-primary/8 text-primary shadow-xs'
                          : 'border-input text-muted-foreground hover:border-foreground/20 hover:text-foreground'
                      )}
                    >
                      <Icon className="w-4 h-4" />
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-foreground mb-3 block">Sidebar</label>
              <Button variant="outline" onClick={toggleSidebar} className="gap-2">
                {sidebarCollapsed ? (
                  <><PanelLeft className="w-4 h-4" /> Expand Sidebar</>
                ) : (
                  <><PanelLeftClose className="w-4 h-4" /> Collapse Sidebar</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* About */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Info className="w-4 h-4 text-info" />
              About
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center justify-between py-2">
              <span className="text-muted-foreground">Platform</span>
              <span className="font-medium text-foreground">Enterprise Modernization Intelligence Platform</span>
            </div>
            <div className="flex items-center justify-between py-2 border-t">
              <span className="text-muted-foreground">Version</span>
              <span className="font-medium text-foreground">1.0.0</span>
            </div>
            <div className="flex items-center justify-between py-2 border-t">
              <span className="text-muted-foreground">Description</span>
              <span className="font-medium text-foreground">AI-Powered monolith to microservices migration analysis using Amazon Bedrock</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
