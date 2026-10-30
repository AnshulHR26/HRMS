import axios from "axios";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { authApi, employeesApi } from "../api/services";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { SectionLoader, Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";
import { Avatar, Card, DetailItem, ErrorState, Field, RoleBadge, StatusBadge } from "../components/ui";
import type { Employee } from "../types";
import { formatDate, formatDateTime, humanize, tenure } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,128}$/;

export default function MyProfile() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const profile = useAsync(
    () =>
      employeesApi.me().catch((err) => {
        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
        throw err;
      }),
    [],
  );
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [editingContact, setEditingContact] = useState(false);
  const [contact, setContact] = useState({ phone_number: "", address: "" });
  const [saving, setSaving] = useState(false);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwError, setPwError] = useState<string | null>(null);
  const [pwSaving, setPwSaving] = useState(false);

  useEffect(() => {
    if (profile.data) setEmployee(profile.data);
  }, [profile.data]);

  const saveContact = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    try {
      const updated = await employeesApi.updateMe({
        phone_number: contact.phone_number.trim() || null,
        address: contact.address.trim() || null,
      });
      setEmployee(updated);
      setEditingContact(false);
      toast.success("Contact details updated.");
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (event: FormEvent) => {
    event.preventDefault();
    if (!PASSWORD_RE.test(pw.next)) return setPwError("New password needs 8+ characters with letters and digits.");
    if (pw.next !== pw.confirm) return setPwError("New passwords do not match.");
    setPwSaving(true);
    setPwError(null);
    try {
      await authApi.changePassword(pw.current, pw.next);
      toast.success("Password changed. Please sign in with your new password.");
      await logout().catch(() => undefined);
      navigate("/login", { replace: true });
    } catch (err) {
      setPwError(getErrorMessage(err));
    } finally {
      setPwSaving(false);
    }
  };

  if (!user) return null;
  if (profile.loading && !profile.data) return <SectionLoader />;
  if (profile.error) return <ErrorState message={profile.error} onRetry={profile.reload} />;

  return (
    <>
      <div className="profile-hero">
        <Avatar name={employee?.full_name ?? user.user_id} size={64} />
        <div className="profile-hero-text">
          <h1>{employee?.full_name ?? user.user_id}</h1>
          <div className="profile-hero-meta">
            <span className="mono">{user.user_id}</span>
            {employee && (
              <>
                <span>·</span>
                <span className="mono">{employee.employee_id}</span>
              </>
            )}
          </div>
          <div className="profile-hero-badges">
            <RoleBadge role={user.role} />
            {employee && <StatusBadge status={employee.employment_status} />}
          </div>
        </div>
      </div>

      {employee ? (
        <div className="grid-2">
          <Card
            title="Personal information"
            actions={
              !editingContact && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setContact({ phone_number: employee.phone_number ?? "", address: employee.address ?? "" });
                    setEditingContact(true);
                  }}
                >
                  <Icon name="edit" size={14} /> Edit contact
                </button>
              )
            }
          >
            {editingContact ? (
              <form className="form-stack" onSubmit={saveContact}>
                <Field label="Phone number">
                  <input className="input" value={contact.phone_number} onChange={(e) => setContact({ ...contact, phone_number: e.target.value })} maxLength={20} />
                </Field>
                <Field label="Address">
                  <textarea className="input" rows={3} value={contact.address} onChange={(e) => setContact({ ...contact, address: e.target.value })} maxLength={1000} />
                </Field>
                <div className="form-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => setEditingContact(false)}>
                    Cancel
                  </button>
                  <button className="btn btn-primary" disabled={saving}>
                    {saving ? <Spinner size={16} /> : "Save"}
                  </button>
                </div>
                <p className="muted small">Other details are maintained by HR. Contact HR to request changes.</p>
              </form>
            ) : (
              <dl className="detail-grid">
                <DetailItem label="Full name" value={employee.full_name} />
                <DetailItem label="Email" value={employee.email} />
                <DetailItem label="Phone" value={employee.phone_number} />
                <DetailItem label="Gender" value={employee.gender ? humanize(employee.gender) : null} />
                <DetailItem label="Date of birth" value={employee.date_of_birth ? formatDate(employee.date_of_birth) : null} />
                <DetailItem label="Address" value={employee.address} />
              </dl>
            )}
          </Card>
          <Card title="Employment">
            <dl className="detail-grid">
              <DetailItem label="Employee ID" value={<span className="mono">{employee.employee_id}</span>} />
              <DetailItem label="Department" value={employee.department?.name} />
              <DetailItem label="Designation" value={employee.designation?.name} />
              <DetailItem label="Joining date" value={`${formatDate(employee.joining_date)} (${tenure(employee.joining_date)})`} />
              <DetailItem label="Employment type" value={humanize(employee.employment_type)} />
              <DetailItem label="Employment status" value={<StatusBadge status={employee.employment_status} />} />
              <DetailItem label="Reporting manager" value={employee.reporting_manager?.full_name} />
            </dl>
          </Card>
        </div>
      ) : (
        <Card title="Account">
          <dl className="detail-grid">
            <DetailItem label="User ID" value={<span className="mono">{user.user_id}</span>} />
            <DetailItem label="Role" value={<RoleBadge role={user.role} />} />
            <DetailItem label="Last sign-in" value={formatDateTime(user.last_login_at)} />
          </dl>
          <p className="muted small">This is a system account with no linked employee profile.</p>
        </Card>
      )}

      <Card title="Change password" className="narrow-card">
        <form className="form-stack" onSubmit={changePassword} noValidate>
          {pwError && <div className="alert alert-error">{pwError}</div>}
          <Field label="Current password" required>
            <input className="input" type="password" autoComplete="current-password" value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
          </Field>
          <Field label="New password" required hint="8+ characters with letters and digits">
            <input className="input" type="password" autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
          </Field>
          <Field label="Confirm new password" required>
            <input className="input" type="password" autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
          </Field>
          <div className="form-actions">
            <button className="btn btn-primary" disabled={pwSaving || !pw.current || !pw.next}>
              {pwSaving ? <Spinner size={16} /> : "Update password"}
            </button>
          </div>
          <p className="muted small">Changing your password signs you out of every device.</p>
        </form>
      </Card>
    </>
  );
}
