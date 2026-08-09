export interface AuthTokens {
  id_token: string;
  access_token: string;
  refresh_token: string;
}

const TOKENS_KEY = 'emip-tokens';

export function loadTokens(): AuthTokens | null {
  try {
    const raw = localStorage.getItem(TOKENS_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<AuthTokens>;
    if (parsed && typeof parsed.id_token === 'string' && parsed.id_token) {
      return {
        id_token: parsed.id_token,
        access_token: typeof parsed.access_token === 'string' ? parsed.access_token : '',
        refresh_token: typeof parsed.refresh_token === 'string' ? parsed.refresh_token : '',
      };
    }
    return null;
  } catch {
    return null;
  }
}

export function saveTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKENS_KEY, JSON.stringify(tokens));
}

export function clearTokens(): void {
  localStorage.removeItem(TOKENS_KEY);
}
