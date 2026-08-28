import axios, { AxiosHeaders, type AxiosRequestConfig } from 'axios';
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL ?? '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY ?? '';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  async (config) => {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session?.access_token) {
      const headers = AxiosHeaders.from(config.headers);
      headers.set('Authorization', `Bearer ${session.access_token}`);
      config.headers = headers;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

type JsonObject = Record<string, unknown>;
export interface ApiUploadOptions {
  onUploadProgress?: (progress: number) => void;
}

async function request<T>(config: AxiosRequestConfig): Promise<T> {
  const response = await api.request<T>(config);
  return response.data;
}

export function apiGet<T>(url: string, params?: JsonObject): Promise<T> {
  return request<T>({
    url,
    method: 'get',
    params,
  });
}

export function apiPost<T>(url: string, body?: JsonObject): Promise<T> {
  return request<T>({
    url,
    method: 'post',
    data: body,
  });
}

export function apiPatch<T>(url: string, body?: JsonObject): Promise<T> {
  return request<T>({
    url,
    method: 'patch',
    data: body,
  });
}

export function apiDelete<T>(url: string): Promise<T> {
  return request<T>({
    url,
    method: 'delete',
  });
}

export function apiUpload<T>(url: string, formData: FormData, options?: ApiUploadOptions): Promise<T> {
  return request<T>({
    url,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: options?.onUploadProgress
      ? (event) => {
          if (event.total) {
            options.onUploadProgress?.(Math.round((event.loaded * 100) / event.total));
          }
        }
      : undefined,
  });
}
