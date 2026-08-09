import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, Mail, Lock, LogIn, FlaskConical, AlertCircle } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { useAppStore } from '@/store/useAppStore';
import { AuthShowcase } from '@/components/auth/AuthShowcase';

export default function LoginPage() {
  const { login, continueAsGuest } = useAuth();
  const navigate = useNavigate();
  const setDemoMode = useAppStore((s) => s.setDemoMode);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demoNotice, setDemoNotice] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await login(username.trim(), password);
    setSubmitting(false);
    if (result.ok) {
      navigate('/dashboard', { replace: true });
      return;
    }
    if (result.status === 503) {
      setDemoNotice(true);
      return;
    }
    setError(result.error || 'Sign in failed');
  }

  function handleDemo() {
    setDemoMode(true);
    continueAsGuest();
    navigate('/dashboard', { replace: true });
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-2 bg-[var(--bg-base)]">
      <div className="hidden lg:block">
        <AuthShowcase />
      </div>

      <div className="relative flex items-center justify-center p-6">
        <div className="absolute inset-0 opacity-[0.5] [background-image:radial-gradient(var(--border-subtle)_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none" />
        <div className="relative w-full max-w-md space-y-6 animate-fade-up">
          <div className="lg:hidden flex flex-col items-center gap-3 text-center">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] flex items-center justify-center">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">EMIP</h1>
              <p className="text-sm text-[var(--text-muted)]">
                Enterprise Modernization Intelligence Platform
              </p>
            </div>
          </div>

          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-2xl shadow-xl p-6 sm:p-8 space-y-5">
            <div>
              <h2 className="text-xl font-semibold text-[var(--text-primary)]">Welcome back</h2>
              <p className="text-sm text-[var(--text-muted)]">Sign in to your modernization workspace</p>
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-[var(--risk)]/25 bg-[var(--risk)]/5 px-3 py-2.5 text-sm text-[var(--risk)] animate-scale-in">
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {demoNotice && (
              <div className="flex items-start gap-2 rounded-lg border border-[var(--warning)]/25 bg-[var(--warning)]/5 px-3 py-2.5 text-sm text-[var(--text-secondary)] animate-scale-in">
                <FlaskConical className="w-4 h-4 mt-0.5 shrink-0 text-[var(--warning)]" />
                <span>
                  Authentication is not configured on this deployment. You can continue without
                  signing in.
                </span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <label htmlFor="username" className="text-sm font-medium text-[var(--text-primary)]">
                  Email
                </label>
                <Input
                  id="username"
                  type="email"
                  autoComplete="username"
                  icon={<Mail className="w-4 h-4" />}
                  placeholder="you@company.com"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoFocus
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="password" className="text-sm font-medium text-[var(--text-primary)]">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  icon={<Lock className="w-4 h-4" />}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <div className="flex items-center justify-end">
                <span className="text-xs text-[var(--text-muted)]">Forgot password? Contact your admin</span>
              </div>

              <Button type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
                <LogIn className="w-4 h-4" />
                {submitting ? 'Signing in…' : 'Sign in'}
              </Button>
            </form>

            <div className="pt-2 flex flex-col gap-3 border-t border-[var(--border-subtle)]">
              <button
                onClick={handleDemo}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-[var(--warning)]/30 bg-[var(--warning)]/5 px-4 py-2.5 text-sm font-medium text-[var(--warning)] hover:bg-[var(--warning)]/10 transition-colors"
              >
                <FlaskConical className="w-4 h-4" />
                Continue in Demo Mode
              </button>

              <p className="text-center text-sm text-[var(--text-muted)]">
                No account?{' '}
                <Link to="/signup" className="text-[var(--accent-blue)] hover:underline font-medium">
                  Create one
                </Link>
              </p>
            </div>
          </div>

          <p className="text-center text-xs text-[var(--text-muted)]">
            Protected by Amazon Cognito · Sign up uses self-service email verification
          </p>
        </div>
      </div>
    </div>
  );
}
