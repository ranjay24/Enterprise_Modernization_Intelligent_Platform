import { create } from 'zustand';

interface AppState {
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;
  theme: 'light' | 'dark' | 'system';
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  demoMode: boolean;
  toggleDemoMode: () => void;
  setDemoMode: (on: boolean) => void;
}

function getInitialTheme(): 'light' | 'dark' | 'system' {
  if (typeof window === 'undefined') return 'system';
  const stored = localStorage.getItem('emip-theme');
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  return 'system';
}

function getInitialSidebar(): boolean {
  if (typeof window === 'undefined') return false;
  return localStorage.getItem('emip-sidebar') === 'true';
}

function getInitialDemoMode(): boolean {
  if (typeof window === 'undefined') return false;
  return sessionStorage.getItem('emip-demo') === 'true';
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: getInitialSidebar(),
  toggleSidebar: () =>
    set((state) => {
      const next = !state.sidebarCollapsed;
      localStorage.setItem('emip-sidebar', String(next));
      return { sidebarCollapsed: next };
    }),
  theme: getInitialTheme(),
  setTheme: (theme) => {
    localStorage.setItem('emip-theme', theme);
    set({ theme });
  },
  demoMode: getInitialDemoMode(),
  toggleDemoMode: () =>
    set((state) => {
      const next = !state.demoMode;
      sessionStorage.setItem('emip-demo', String(next));
      return { demoMode: next };
    }),
  setDemoMode: (on) => {
    sessionStorage.setItem('emip-demo', String(on));
    set({ demoMode: on });
  },
}));
