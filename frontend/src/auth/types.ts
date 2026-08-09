import type { AuthTokens } from './storage';

export interface AuthUser {
  username: string;
  email: string;
  name: string;
}

export type AuthStatus = 'loading' | 'unauthenticated' | 'authenticated' | 'guest';

export interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<{ ok: boolean; status?: number; error?: string }>;
  signup: (username: string, email: string, password: string) => Promise<{
    ok: boolean;
    status?: number;
    error?: string;
    verificationCode?: string;
  }>;
  confirm: (username: string, code: string) => Promise<{ ok: boolean; error?: string }>;
  logout: () => void;
  continueAsGuest: () => void;
}

export interface LoginResponse {
  access_token: string;
  id_token: string;
  refresh_token: string;
  expires_in: number;
  user: AuthUser;
}

export type { AuthTokens };
