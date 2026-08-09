import { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';
import api from '@/services/api';
import { useAppStore } from '@/store/useAppStore';
import { loadTokens, saveTokens, clearTokens } from './storage';
import type { AuthContextValue, AuthStatus, AuthUser, LoginResponse } from './types';

const AuthContext = createContext<AuthContextValue | null>(null);

const isNotConfigured = (status: number | undefined) => status === 503 || status === undefined;

function userFromMe(data: unknown): AuthUser {
  const d = (data ?? {}) as Partial<AuthUser>;
  return {
    username: d.username ?? '',
    email: d.email ?? '',
    name: d.name ?? d.email ?? d.username ?? 'EMIP User',
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [user, setUser] = useState<AuthUser | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      // Demo mode never requires a login — the whole app runs on sample data.
      if (useAppStore.getState().demoMode) {
        setStatus('guest');
        return;
      }

      const tokens = loadTokens();
      if (tokens) {
        try {
          const { data } = await api.get('/auth/me');
          if (cancelled) return;
          setUser(userFromMe(data));
          setStatus('authenticated');
          return;
        } catch (err) {
          const statusCode = (err as { status?: number })?.status;
          if (statusCode !== 401) {
            // Cognito not configured or backend unreachable → guest session.
            if (cancelled) return;
            setStatus('guest');
            return;
          }
          clearTokens();
        }
      }

      try {
        await api.get('/auth/me');
        if (cancelled) return;
        setStatus('guest');
      } catch (err) {
        const statusCode = (err as { status?: number })?.status;
        if (cancelled) return;
        setStatus(isNotConfigured(statusCode) ? 'guest' : 'unauthenticated');
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback<AuthContextValue['login']>(async (username, password) => {
    try {
      const { data } = await api.post<LoginResponse>('/auth/login', { username, password });
      saveTokens({
        id_token: data.id_token,
        access_token: data.access_token,
        refresh_token: data.refresh_token,
      });
      setUser(data.user);
      setStatus('authenticated');
      return { ok: true };
    } catch (err) {
      const statusCode = (err as { status?: number })?.status;
      if (isNotConfigured(statusCode)) {
        setStatus('guest');
        return { ok: false, status: 503, error: (err as Error).message };
      }
      return { ok: false, status: statusCode, error: (err as Error).message };
    }
  }, []);

  const signup = useCallback<AuthContextValue['signup']>(async (username, email, password) => {
    try {
      const { data } = await api.post<{ message: string; verification_code?: string }>('/auth/signup', {
        username,
        email,
        password,
      });
      return { ok: true, verificationCode: data.verification_code };
    } catch (err) {
      const statusCode = (err as { status?: number })?.status;
      if (isNotConfigured(statusCode)) {
        setStatus('guest');
        return { ok: false, status: 503, error: (err as Error).message };
      }
      return { ok: false, status: statusCode, error: (err as Error).message };
    }
  }, []);

  const confirm = useCallback<AuthContextValue['confirm']>(async (username, code) => {
    try {
      await api.post('/auth/confirm', { username, code });
      return { ok: true };
    } catch (err) {
      return { ok: false, error: (err as Error).message };
    }
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
    setStatus('guest');
  }, []);

  const continueAsGuest = useCallback(() => {
    setUser(null);
    setStatus('guest');
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, signup, confirm, logout, continueAsGuest }),
    [status, user, login, signup, confirm, logout, continueAsGuest]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
