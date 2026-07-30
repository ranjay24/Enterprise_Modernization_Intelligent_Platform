import axios from 'axios';
import { API_BASE } from '@/utils/constants';

const apiKey = import.meta.env.VITE_API_KEY || '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,
  headers: apiKey ? { 'X-API-Key': apiKey } : {},
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'Request failed';
    return Promise.reject(new Error(message));
  }
);

export default api;
