import { Navigate, Outlet, useLocation } from "react-router-dom";
import { FullPageSpinner } from "../components/Spinner";
import type { RoleName } from "../types";
import { useAuth } from "./AuthContext";

interface Props {
  roles?: RoleName[];
}

/** UX guard only — the API rejects unauthorized calls regardless of what the UI shows. */
export function ProtectedRoute({ roles }: Props) {
  const { user, initializing } = useAuth();
  const location = useLocation();

  if (initializing) return <FullPageSpinner />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/forbidden" replace />;
  return <Outlet />;
}
