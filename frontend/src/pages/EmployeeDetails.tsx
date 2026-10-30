import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { employeesApi } from "../api/services";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { ConfirmDialog, Modal } from "../components/Modal";
import { SectionLoader, Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";
import { Avatar, Card, DetailItem, ErrorState, RoleBadge, StatusBadge } from "../components/ui";
import { WORKING_STATUSES, type Employee, type EmploymentStatus } from "../types";
import { formatDate, humanize, tenure } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const ALL_STATUSES: EmploymentStatus[] = ["ACTIVE", "PROBATION", "NOTICE_PERIOD", "INACTIVE", "TERMINATED"];

export default function EmployeeDetails() {
  const { employeeId = "" } = useParams();
  const { user, hasRole } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const { data, loading, error, reload } = useAsync(() => employeesApi.get(employeeId), [employeeId]);
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);
  const [nextStatus, setNextStatus] = useState<EmploymentStatus>("INACTIVE");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const record = employee?.employee_id === employeeId ? employee : data;
  const canManage = hasRole("ADMIN", "HR");
  const isSelf = record?.user_id === user?.user_id;
  const hrBlocked = hasRole("HR") && record?.role === "ADMIN";

  if (loading && !record) return <SectionLoader />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!record) return null;

  const isWorking = WORKING_STATUSES.includes(record.employment_status);

  const applyStatus = async () => {
    setSaving(true);
    try {
      const updated = await employeesApi.setStatus(record.employee_id, nextStatus);
      setEmployee(updated);
      toast.success(`Status changed to ${humanize(nextStatus)}.`);
      setConfirmOpen(false);
      setStatusOpen(false);
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <button className="btn btn-ghost btn-sm back-link" onClick={() => navigate(-1)}>
        <Icon name="arrowLeft" size={16} /> Back
      </button>

      <div className="profile-hero">
        <Avatar name={record.full_name} size={64} />
        <div className="profile-hero-text">
          <h1>{record.full_name}</h1>
          <div className="profile-hero-meta">
            <span className="mono">{record.employee_id}</span>
            <span>·</span>
            <span>{record.designation?.name ?? "No designation"}</span>
            {record.department && (
              <>
                <span>·</span>
                <span>{record.department.name}</span>
              </>
            )}
          </div>
          <div className="profile-hero-badges">
            <StatusBadge status={record.employment_status} />
            <RoleBadge role={record.role} />
            {!record.account_active && <span className="badge badge-red">Login disabled</span>}
          </div>
        </div>
        {canManage && !hrBlocked && (
          <div className="profile-hero-actions">
            <Link className="btn btn-secondary" to={`/employees/${record.employee_id}/edit`}>
              <Icon name="edit" size={16} /> Edit
            </Link>
            {!isSelf && (
              <button
                className={`btn ${isWorking ? "btn-danger-outline" : "btn-primary"}`}
                onClick={() => {
                  setNextStatus(isWorking ? "INACTIVE" : "ACTIVE");
                  setStatusOpen(true);
                }}
              >
                {isWorking ? "Deactivate" : "Reactivate"}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="grid-2">
        <Card title="Personal information">
          <dl className="detail-grid">
            <DetailItem label="Full name" value={record.full_name} />
            <DetailItem label="Email" value={<a href={`mailto:${record.email}`}>{record.email}</a>} />
            <DetailItem label="Phone" value={record.phone_number} />
            <DetailItem label="Gender" value={record.gender ? humanize(record.gender) : null} />
            <DetailItem label="Date of birth" value={record.date_of_birth ? formatDate(record.date_of_birth) : null} />
            <DetailItem label="Address" value={record.address} />
          </dl>
        </Card>
        <Card title="Employment">
          <dl className="detail-grid">
            <DetailItem label="Employee ID" value={<span className="mono">{record.employee_id}</span>} />
            <DetailItem label="User ID" value={<span className="mono">{record.user_id}</span>} />
            <DetailItem label="Department" value={record.department?.name} />
            <DetailItem label="Designation" value={record.designation?.name} />
            <DetailItem label="Joining date" value={`${formatDate(record.joining_date)} (${tenure(record.joining_date)})`} />
            <DetailItem label="Employment type" value={humanize(record.employment_type)} />
            <DetailItem label="Status" value={<StatusBadge status={record.employment_status} />} />
            <DetailItem
              label="Reporting manager"
              value={
                record.reporting_manager ? (
                  canManage ? (
                    <Link to={`/employees/${record.reporting_manager.employee_id}`}>{record.reporting_manager.full_name}</Link>
                  ) : (
                    record.reporting_manager.full_name
                  )
                ) : null
              }
            />
          </dl>
        </Card>
      </div>
      <p className="muted small record-meta">
        Created {formatDate(record.created_at)} · Last updated {formatDate(record.updated_at)}
      </p>

      <Modal
        open={statusOpen}
        title="Change employment status"
        onClose={() => setStatusOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setStatusOpen(false)}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              disabled={nextStatus === record.employment_status}
              onClick={() => (WORKING_STATUSES.includes(nextStatus) ? applyStatus() : setConfirmOpen(true))}
            >
              {saving ? <Spinner size={16} /> : "Save status"}
            </button>
          </>
        }
      >
        <label className="field">
          <span className="field-label">New status</span>
          <select className="input" value={nextStatus} onChange={(e) => setNextStatus(e.target.value as EmploymentStatus)}>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {humanize(s)}
              </option>
            ))}
          </select>
          <span className="field-hint">
            Inactive and terminated employees cannot sign in. The record is kept (soft deactivation).
          </span>
        </label>
      </Modal>

      <ConfirmDialog
        open={confirmOpen}
        title={`Set ${record.full_name} to ${humanize(nextStatus)}?`}
        message="Their login will be disabled immediately and every active session will be signed out."
        confirmLabel="Deactivate"
        busy={saving}
        onConfirm={applyStatus}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
