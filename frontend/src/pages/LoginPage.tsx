import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { homePathFor } from "../components/navigation";
import { FullPageSpinner, Spinner } from "../components/Spinner";

export default function LoginPage() {
  const { user, initializing, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [userId, setUserId] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (initializing) return <FullPageSpinner />;
  if (user) return <Navigate to={homePathFor(user.role)} replace />;

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!userId.trim() || !password) {
      setError("Enter your User ID and password.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const signedIn = await login(userId.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : homePathFor(signedIn.role), { replace: true });
    } catch (err) {
      setError(getErrorMessage(err, "Sign-in failed."));
      setPassword("");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-aside">
        <div className="brand brand-lg">
          <span className="brand-mark">H</span>
          <div>
            <div className="brand-name">HRMS</div>
            <div className="brand-sub">People Platform</div>
          </div>
        </div>
        <div className="login-pitch">
          <h2>One place for your people operations.</h2>
          <ul>
            <li><Icon name="users" /> Employee records &amp; directory</li>
            <li><Icon name="building" /> Departments &amp; designations</li>
            <li><Icon name="shield" /> Role-based access for Admin, HR and employees</li>
          </ul>
        </div>
        <div className="muted-on-dark small">Secure sign-in · sessions use httpOnly cookies</div>
      </div>

      <div className="login-panel">
        <form className="login-card" onSubmit={onSubmit} noValidate>
          <h1>Sign in</h1>
          <p className="muted">Use the User ID and password provided by your administrator.</p>

          {error && (
            <div className="alert alert-error" role="alert">
              <Icon name="alert" size={16} /> {error}
            </div>
          )}

          <label className="field">
            <span className="field-label">User ID</span>
            <input
              className="input"
              autoComplete="username"
              autoFocus
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. jane.doe"
              maxLength={50}
            />
          </label>

          <label className="field">
            <span className="field-label">Password</span>
            <div className="input-group">
              <input
                className="input"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                maxLength={128}
              />
              <button type="button" className="input-addon" onClick={() => setShowPassword((s) => !s)}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
          </label>

          <button className="btn btn-primary btn-block" type="submit" disabled={submitting}>
            {submitting ? <Spinner size={16} /> : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
