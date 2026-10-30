import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { UNAUTHORIZED_EVENT } from "../api/client";
import { authApi } from "../api/services";
import type { RoleName, User } from "../types";

interface AuthState {
  user: User | null;
  /** True until the initial /auth/me check has finished. */
  initializing: boolean;
  login: (userId: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hasRole: (...roles: RoleName[]) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Holds only the *public* user object in memory. The session itself is the
 * httpOnly cookie, so a page reload re-hydrates by calling GET /auth/me.
 * Role checks here only shape the UI — the backend enforces every permission.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setUser(await authApi.me());
    } catch {
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refresh().finally(() => setInitializing(false));
  }, [refresh]);

  useEffect(() => {
    const onUnauthorized = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized);
  }, []);

  const login = useCallback(async (userId: string, password: string) => {
    const result = await authApi.login(userId, password);
    setUser(result.user);
    return result.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUser(null);
    }
  }, []);

  const hasRole = useCallback((...roles: RoleName[]) => !!user && roles.includes(user.role), [user]);

  const value = useMemo(
    () => ({ user, initializing, login, logout, refresh, hasRole }),
    [user, initializing, login, logout, refresh, hasRole],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
