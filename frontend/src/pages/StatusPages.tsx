import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { homePathFor } from "../components/navigation";

function StatusPage({ code, title, message }: { code: string; title: string; message: string }) {
  const { user } = useAuth();
  return (
    <div className="status-page">
      <div className="status-code">{code}</div>
      <h1>{title}</h1>
      <p className="muted">{message}</p>
      <Link className="btn btn-primary" to={user ? homePathFor(user.role) : "/login"}>
        Back to dashboard
      </Link>
    </div>
  );
}

export function ForbiddenPage() {
  return <StatusPage code="403" title="Access denied" message="Your role does not have permission to view this page." />;
}

export function NotFoundPage() {
  return <StatusPage code="404" title="Page not found" message="The page you are looking for does not exist." />;
}
