import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, Mail, Lock, User, KeyRound, AlertCircle, CheckCircle2, FlaskConical } from 'lucide-react';
import { useAuth } from '@/auth/AuthContext';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { AuthShowcase } from '@/components/auth/AuthShowcase';

export default function SignupPage() {
  const { signup, confirm } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [code, setCode] = useState('');
  const [stage, setStage] = useState<'form' | 'verify' | 'done'>('form');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [devCode, setDevCode] = useState<string | undefined>(undefined);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setSubmitting(true);
    const result = await signup(username.trim(), email.trim(), password);
    setSubmitting(false);
    if (result.ok) {
      setDevCode(result.verificationCode);
      setStage('verify');
      return;
    }
    if (result.status === 503) {
      setError('Authentication is not configured on this deployment — sign in is unavailable.');
      return;
    }
    setError(result.error || 'Account creation failed');
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    const result = await confirm(username.trim(), code.trim());
    setSubmitting(false);
    if (result.ok) {
      setStage('done');
      return;
    }
    setError(result.error || 'Verification failed');
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
            {stage === 'done' ? (
              <div className="space-y-4 text-center py-4 animate-scale-in">
                <div className="relative inline-flex">
                  <CheckCircle2 className="w-14 h-14 text-[var(--success)] mx-auto" />
                  <span className="absolute inset-0 rounded-full bg-[var(--success)]/20 animate-ping" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-[var(--text-primary)]">Account confirmed</h2>
                  <p className="text-sm text-[var(--text-muted)]">
                    You can now sign in with your new account.
                  </p>
                </div>
                <Button variant="primary" onClick={() => navigate('/login')} className="w-full">
                  Go to Sign in
                </Button>
              </div>
            ) : stage === 'verify' ? (
              <>
                <div>
                  <h2 className="text-lg font-semibold text-[var(--text-primary)]">Verify your email</h2>
                  <p className="text-sm text-[var(--text-muted)]">
                    We sent a verification code to <span className="font-medium text-[var(--text-primary)]">{email}</span>.
                    Enter it below to activate your account.
                  </p>
                </div>

                {devCode && (
                  <div className="flex items-start gap-2 rounded-lg border border-[var(--warning)]/25 bg-[var(--warning)]/5 px-3 py-2.5 text-sm text-[var(--text-secondary)] animate-scale-in">
                    <FlaskConical className="w-4 h-4 mt-0.5 shrink-0 text-[var(--warning)]" />
                    <span>
                      <span className="font-medium text-[var(--warning)]">Development mode</span> — no email
                      service is configured, so here is your code:{' '}
                      <code className="rounded bg-[var(--bg-base)] px-1.5 py-0.5 font-mono text-sm font-semibold tracking-widest text-[var(--accent-blue)]">
                        {devCode}
                      </code>
                    </span>
                  </div>
                )}

                {error && (
                  <div className="flex items-start gap-2 rounded-lg border border-[var(--risk)]/25 bg-[var(--risk)]/5 px-3 py-2.5 text-sm text-[var(--risk)] animate-scale-in">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleVerify} className="space-y-4">
                  <div className="space-y-1.5">
                    <label htmlFor="code" className="text-sm font-medium text-[var(--text-primary)]">
                      Verification code
                    </label>
                    <Input
                      id="code"
                      type="text"
                      inputMode="numeric"
                      icon={<KeyRound className="w-4 h-4" />}
                      placeholder="123456"
                      value={code}
                      onChange={(e) => setCode(e.target.value)}
                      required
                      autoFocus
                    />
                  </div>
                  <Button type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
                    {submitting ? 'Verifying…' : 'Confirm account'}
                  </Button>
                </form>
              </>
            ) : (
              <>
                <div>
                  <h2 className="text-xl font-semibold text-[var(--text-primary)]">Create an account</h2>
                  <p className="text-sm text-[var(--text-muted)]">
                    Self-service sign up with email verification
                  </p>
                </div>

                {error && (
                  <div className="flex items-start gap-2 rounded-lg border border-[var(--risk)]/25 bg-[var(--risk)]/5 px-3 py-2.5 text-sm text-[var(--risk)] animate-scale-in">
                    <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-1.5">
                    <label htmlFor="su-username" className="text-sm font-medium text-[var(--text-primary)]">
                      Username
                    </label>
                    <Input
                      id="su-username"
                      type="text"
                      autoComplete="username"
                      icon={<User className="w-4 h-4" />}
                      placeholder="jdoe"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      required
                      autoFocus
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor="su-email" className="text-sm font-medium text-[var(--text-primary)]">
                      Email
                    </label>
                    <Input
                      id="su-email"
                      type="email"
                      autoComplete="email"
                      icon={<Mail className="w-4 h-4" />}
                      placeholder="you@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor="su-password" className="text-sm font-medium text-[var(--text-primary)]">
                      Password
                    </label>
                    <Input
                      id="su-password"
                      type="password"
                      autoComplete="new-password"
                      icon={<Lock className="w-4 h-4" />}
                      placeholder="At least 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label htmlFor="su-confirm" className="text-sm font-medium text-[var(--text-primary)]">
                      Confirm password
                    </label>
                    <Input
                      id="su-confirm"
                      type="password"
                      autoComplete="new-password"
                      icon={<Lock className="w-4 h-4" />}
                      placeholder="Repeat your password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </div>

                  <Button type="submit" variant="primary" size="lg" className="w-full" disabled={submitting}>
                    {submitting ? 'Creating account…' : 'Create account'}
                  </Button>
                </form>
              </>
            )}

            <p className="text-center text-sm text-[var(--text-muted)] border-t border-[var(--border-subtle)] pt-3">
              Already have an account?{' '}
              <Link to="/login" className="text-[var(--accent-blue)] hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
