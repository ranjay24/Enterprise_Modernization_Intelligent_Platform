import axios from 'axios';
import { API_BASE } from '@/utils/constants';
import { loadTokens, clearTokens } from '@/auth/storage';

const apiKey = import.meta.env.VITE_API_KEY || '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,
  headers: apiKey ? { 'X-API-Key': apiKey } : {},
});

api.interceptors.request.use((config) => {
  const tokens = loadTokens();
  if (tokens?.id_token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${tokens.id_token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const message = error.response?.data?.detail || error.message || 'Request failed';

    const attachedToken = !!error.config?.headers?.Authorization;
    const isAuthRoute = /\/auth\//.test(error.config?.url || '');
    if (status === 401 && attachedToken && !isAuthRoute) {
      clearTokens();
      if (window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }

    const wrapped = new Error(message) as Error & { status?: number };
    if (status) wrapped.status = status;
    return Promise.reject(wrapped);
  }
);

export default api;
