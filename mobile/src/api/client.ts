import Constants from 'expo-constants';

/**
 * The API runs on the same machine as the Metro bundler during development, so the host
 * is derived from Expo's connection rather than hardcoded. A hardcoded LAN IP breaks
 * every time the laptop changes network, and the failure looks like a dead server.
 */
function resolveBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  if (fromEnv) {
    return fromEnv;
  }

  const host = Constants.expoConfig?.hostUri?.split(':')[0];
  if (host) {
    return `http://${host}:8000`;
  }

  // Simulator/web fallback. A physical device reaching this means hostUri was unavailable.
  return 'http://localhost:8000';
}

export const API_BASE_URL = resolveBaseUrl();

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Every request goes through here. That matters later: it is the one place an auth
 * header gets attached once the auth milestone lands, rather than N call sites.
 */
export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new ApiError(
      response.status,
      `${init?.method ?? 'GET'} ${path} failed with ${response.status}`,
    );
  }

  return (await response.json()) as T;
}
