const DEFAULT_API_BASE_URL = 'http://localhost:8000/api';

function normalizeApiBaseUrl(rawUrl: string): string {
  const trimmed = rawUrl.trim().replace(/\/+$/, '');
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
}

const rawApiUrl =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  DEFAULT_API_BASE_URL;

export const API_BASE_URL = normalizeApiBaseUrl(rawApiUrl);
export const API_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '');
