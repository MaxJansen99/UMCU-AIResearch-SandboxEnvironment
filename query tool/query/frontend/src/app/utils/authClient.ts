export type UserRole = 'researcher' | 'datamanager';

export type AuthUser = {
  id: number;
  username: string;
  role: UserRole;
};

export type LoginResult = {
  token: string;
  token_type: 'bearer';
  user: AuthUser;
};

const TOKEN_KEY = 'dicom_query_token';

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function storeToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export async function login(username: string, password: string): Promise<LoginResult> {
  const response = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });

  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || 'Verkeerde inloggegevens.');
  }

  return {
    token: payload.token,
    token_type: payload.token_type,
    user: payload.user,
  };
}

export async function me(token: string): Promise<AuthUser> {
  const response = await fetch('/auth/me', {
    headers: authorizationHeaders(token),
  });

  const payload = await response.json();
  if (!response.ok || !payload.ok) {
    throw new Error(payload.error || 'Niet ingelogd.');
  }

  return payload.user;
}

export function authorizationHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export function routeForRole(role: UserRole): string {
  return role === 'datamanager' ? '/datamanager' : '/researcher';
}
