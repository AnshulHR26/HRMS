import type { ReactNode } from "react";
import type { EmploymentStatus, RecordStatus, RoleName } from "../types";
import { humanize } from "../utils/format";
import { Icon, type IconName } from "./Icon";

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, children, className = "" }: {
  title?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          {title && <h2>{title}</h2>}
          {actions}
        </div>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function StatCard({ label, value, icon, tone = "blue", hint }: {
  label: string;
  value: number | string;
  icon: IconName;
  tone?: "blue" | "green" | "amber" | "slate" | "violet";
  hint?: string;
}) {
  return (
    <div className="stat-card">
      <div className={`stat-icon tone-${tone}`}>
        <Icon name={icon} size={20} />
      </div>
      <div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {hint && <div className="stat-hint">{hint}</div>}
      </div>
    </div>
  );
}

const STATUS_TONE: Record<string, string> = {
  ACTIVE: "green",
  PROBATION: "blue",
  NOTICE_PERIOD: "amber",
  INACTIVE: "slate",
  TERMINATED: "red",
};

export function StatusBadge({ status }: { status: EmploymentStatus | RecordStatus }) {
  return <span className={`badge badge-${STATUS_TONE[status] ?? "slate"}`}>{humanize(status)}</span>;
}

const ROLE_TONE: Record<RoleName, string> = { ADMIN: "violet", HR: "blue", EMPLOYEE: "slate" };

export function RoleBadge({ role }: { role: RoleName }) {
  return <span className={`badge badge-${ROLE_TONE[role]}`}>{role}</span>;
}

export function EmptyState({ title, message, action }: { title: string; message?: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">
        <Icon name="search" size={22} />
      </div>
      <h3>{title}</h3>
      {message && <p className="muted">{message}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <Icon name="alert" />
      <span>{message}</span>
      {onRetry && (
        <button className="btn btn-secondary btn-sm" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function Pagination({ page, pages, total, pageSize, onChange }: {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onChange: (page: number) => void;
}) {
  if (total === 0) return null;
  const from = (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);
  return (
    <div className="pagination">
      <span className="muted">
        Showing <strong>{from}</strong>–<strong>{to}</strong> of <strong>{total}</strong>
      </span>
      <div className="pagination-controls">
        <button className="btn btn-secondary btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
          <Icon name="chevronLeft" size={16} /> Prev
        </button>
        <span className="page-indicator">
          Page {page} of {Math.max(pages, 1)}
        </span>
        <button className="btn btn-secondary btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
          Next <Icon name="chevronRight" size={16} />
        </button>
      </div>
    </div>
  );
}

export function Field({ label, error, required, hint, children }: {
  label: string;
  error?: string;
  required?: boolean;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className={`field ${error ? "has-error" : ""}`}>
      <span className="field-label">
        {label}
        {required && <span className="required">*</span>}
      </span>
      {children}
      {error ? <span className="field-error">{error}</span> : hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  );
}

export function DetailItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="detail-item">
      <dt>{label}</dt>
      <dd>{value ?? <span className="muted">—</span>}</dd>
    </div>
  );
}

export function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
  return (
    <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.38 }}>
      {initials || "?"}
    </span>
  );
}
