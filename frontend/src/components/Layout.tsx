import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "./Icon";
import { NAV_SECTIONS } from "./navigation";
import { Avatar, RoleBadge } from "./ui";
import { useToast } from "./Toast";

export function Layout() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => setMobileOpen(false), [location.pathname]);

  if (!user) return null;
  const displayName = user.employee?.full_name ?? user.user_id;

  const sections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => item.roles.includes(user.role)),
  })).filter((section) => section.items.length > 0);

  const handleLogout = async () => {
    await logout();
    toast.info("You have been signed out.");
    navigate("/login", { replace: true });
  };

  return (
    <div className={`app-shell ${mobileOpen ? "nav-open" : ""}`}>
      <aside className="sidebar" aria-label="Main navigation">
        <div className="brand">
          <span className="brand-mark">H</span>
          <div>
            <div className="brand-name">HRMS</div>
            <div className="brand-sub">People Platform</div>
          </div>
        </div>
        <nav>
          {sections.map((section) => (
            <div className="nav-section" key={section.title}>
              <div className="nav-title">{section.title}</div>
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/employees"}
                  className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                >
                  <Icon name={item.icon} />
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="muted-on-dark">v1.0 · Phases 1–4</span>
        </div>
      </aside>
      <div className="sidebar-scrim" onClick={() => setMobileOpen(false)} />

      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setMobileOpen((open) => !open)} aria-label="Toggle navigation">
            <Icon name="menu" />
          </button>
          <div className="topbar-spacer" />
          <div className="topbar-user">
            <Avatar name={displayName} size={34} />
            <div className="topbar-user-text">
              <div className="topbar-name">{displayName}</div>
              <div className="topbar-meta">
                <RoleBadge role={user.role} />
                {user.employee && <span className="muted">{user.employee.employee_id}</span>}
              </div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={handleLogout}>
              <Icon name="logout" size={16} /> <span className="hide-sm">Sign out</span>
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
