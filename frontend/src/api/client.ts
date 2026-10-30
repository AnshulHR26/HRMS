import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import type { ApiErrorBody } from "../types";

/**
 * Token storage strategy: the JWT lives in an httpOnly cookie set by the backend,
 * so JavaScript never sees it (an XSS payload cannot exfiltrate it). Because the
 * browser attaches cookies automatically, state-changing requests also send the
 * value of the readable `hrms_csrf` cookie in the `X-CSRF-Token` header
 * (double-submit pattern), which a cross-site attacker cannot read.
 */
const CSRF_COOKIE = "hrms_csrf";
const CSRF_HEADER = "X-CSRF-Token";
const UNSAFE_METHODS = new Set(["post", "put", "patch", "delete"]);

export const UNAUTHORIZED_EVENT = "hrms:unauthorized";

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((row) => row.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  withCredentials: true,
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (config.method && UNSAFE_METHODS.has(config.method.toLowerCase())) {
    const csrf = readCookie(CSRF_COOKIE);
    if (csrf) config.headers.set(CSRF_HEADER, csrf);
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    const isLoginCall = error.config?.url?.includes("/auth/login");
    if (error.response?.status === 401 && !isLoginCall) {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
    }
    return Promise.reject(error);
  },
);

export interface FieldError {
  field: string;
  message: string;
}

export function getErrorMessage(error: unknown, fallback = "Something went wrong. Please try again."): string {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    if (!error.response) return "Cannot reach the server. Check your connection.";
    const body = error.response.data;
    if (body?.error?.code === "VALIDATION_ERROR" && Array.isArray(body.error.details)) {
      const first = (body.error.details as FieldError[])[0];
      if (first) return `${first.field ? `${first.field}: ` : ""}${first.message}`;
    }
    return body?.error?.message ?? fallback;
  }
  return fallback;
}

export function getFieldErrors(error: unknown): Record<string, string> {
  if (!axios.isAxiosError<ApiErrorBody>(error)) return {};
  const details = error.response?.data?.error?.details;
  if (!Array.isArray(details)) return {};
  const result: Record<string, string> = {};
  for (const item of details as FieldError[]) {
    const key = item.field.split(".").pop() ?? item.field;
    if (!result[key]) result[key] = item.message.replace(/^Value error, /, "");
  }
  return result;
}
