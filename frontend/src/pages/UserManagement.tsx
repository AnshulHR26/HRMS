import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { getErrorMessage } from "../api/client";
import { usersApi } from "../api/services";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { ConfirmDialog, Modal } from "../components/Modal";
import { SectionLoader, Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";
import { Card, EmptyState, ErrorState, Field, PageHeader, Pagination, RoleBadge } from "../components/ui";
import type { RoleName, User } from "../types";
import { formatDateTime } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const ROLES: RoleName[] = ["ADMIN", "HR", "EMPLOYEE"];
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,128}$/;

type Dialog =
  | { kind: "create" }
  | { kind: "role"; user: User }
  | { kind: "password"; user: User }
  | { kind: "status"; user: User }
  | null;

export default function UserManagement() {
  const { user: me } = useAuth();
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState<RoleName | "">("");
  const [dialog, setDialog] = useState<Dialog>(null);
  const [busy, setBusy] = useState(false);
  const [newUser, setNewUser] = useState({ user_id: "", password: "", role: "HR" as RoleName });
  const [newRole, setNewRole] = useState<RoleName>("EMPLOYEE");
  const [newPassword, setNewPassword] = useState("");
  const [dialogError, setDialogError] = useState<string | null>(null);

  const users = useAsync(
    () => usersApi.list({ page, page_size: 15, search: search.trim() || undefined, role: role || undefined }),
    [page, search, role],
  );

  const close = () => {
    setDialog(null);
    setDialogError(null);
    setNewPassword("");
  };

  const run = async (action: () => Promise<unknown>, message: string): Promise<boolean> => {
    setBusy(true);
    setDialogError(null);
    try {
      await action();
      toast.success(message);
      close();
      users.reload();
      return true;
    } catch (err) {
      setDialogError(getErrorMessage(err));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const submitCreate = (event: FormEvent) => {
    event.preventDefault();
    if (!PASSWORD_RE.test(newUser.password)) {
      setDialogError("Password must be 8+ characters with at least one letter and one digit.");
      return;
    }
    void run(
      () => usersApi.create({ ...newUser, user_id: newUser.user_id.trim(), is_active: true }),
      `Account ${newUser.user_id} created.`,
    ).then((ok) => ok && setNewUser({ user_id: "", password: "", role: "HR" }));
  };

  return (
    <>
      <PageHeader
        title="User Management"
        subtitle="Login accounts, roles and access. Employee accounts are created from the Add Employee form."
        actions={
          <button className="btn btn-primary" onClick={() => setDialog({ kind: "create" })}>
            <Icon name="plus" size={16} /> New account
          </button>
        }
      />
      <Card>
        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={16} />
            <input
              className="input"
              placeholder="Search User ID, name or employee ID"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>
          <select
            className="input"
            value={role}
            onChange={(e) => {
              setRole(e.target.value as RoleName | "");
              setPage(1);
            }}
          >
            <option value="">All roles</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        {users.error && <ErrorState message={users.error} onRetry={users.reload} />}
        {users.loading && !users.data && <SectionLoader />}
        {users.data &&
          (users.data.items.length === 0 ? (
            <EmptyState title="No accounts found" />
          ) : (
            <>
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr>
                      <th>User ID</th>
                      <th>Role</th>
                      <th>Employee profile</th>
                      <th>Status</th>
                      <th>Last sign-in</th>
                      <th className="align-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.data.items.map((u) => {
                      const self = u.id === me?.id;
                      return (
                        <tr key={u.id}>
                          <td className="mono">
                            {u.user_id} {self && <span className="badge badge-blue">You</span>}
                          </td>
                          <td>
                            <RoleBadge role={u.role} />
                          </td>
                          <td>
                            {u.employee ? (
                              <Link to={`/employees/${u.employee.employee_id}`}>
                                {u.employee.full_name} · {u.employee.employee_id}
                              </Link>
                            ) : (
                              <span className="muted">Not linked</span>
                            )}
                          </td>
                          <td>
                            <span className={`badge ${u.is_active ? "badge-green" : "badge-slate"}`}>
                              {u.is_active ? "Active" : "Disabled"}
                            </span>
                          </td>
                          <td className="muted">{formatDateTime(u.last_login_at)}</td>
                          <td className="align-right">
                            <div className="row-actions">
                              <button
                                className="btn btn-ghost btn-sm"
                                disabled={self}
                                title={self ? "You cannot change your own role" : "Change role"}
                                onClick={() => {
                                  setNewRole(u.role);
                                  setDialog({ kind: "role", user: u });
                                }}
                              >
                                Role
                              </button>
                              <button
                                className="btn btn-ghost btn-sm"
                                disabled={self}
                                onClick={() => setDialog({ kind: "password", user: u })}
                              >
                                <Icon name="key" size={14} /> Reset
                              </button>
                              <button
                                className={`btn btn-sm ${u.is_active ? "btn-danger-outline" : "btn-secondary"}`}
                                disabled={self}
                                onClick={() => setDialog({ kind: "status", user: u })}
                              >
                                {u.is_active ? "Disable" : "Enable"}
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination
                page={users.data.page}
                pages={users.data.pages}
                total={users.data.total}
                pageSize={users.data.page_size}
                onChange={setPage}
              />
            </>
          ))}
      </Card>

      <Modal
        open={dialog?.kind === "create"}
        title="Create login account"
        onClose={close}
        footer={
          <>
            <button className="btn btn-secondary" onClick={close}>
              Cancel
            </button>
            <button className="btn btn-primary" form="create-user-form" type="submit" disabled={busy}>
              {busy ? <Spinner size={16} /> : "Create account"}
            </button>
          </>
        }
      >
        <form id="create-user-form" className="form-stack" onSubmit={submitCreate}>
          {dialogError && <div className="alert alert-error">{dialogError}</div>}
          <p className="muted small">
            Use this for system accounts (e.g. HR or Admin users without an employee profile).
          </p>
          <Field label="User ID" required>
            <input className="input" value={newUser.user_id} onChange={(e) => setNewUser({ ...newUser, user_id: e.target.value })} />
          </Field>
          <Field label="Password" required hint="8+ characters, letters and digits">
            <input
              className="input"
              type="password"
              autoComplete="new-password"
              value={newUser.password}
              onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
            />
          </Field>
          <Field label="Role" required>
            <select className="input" value={newUser.role} onChange={(e) => setNewUser({ ...newUser, role: e.target.value as RoleName })}>
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </Field>
        </form>
      </Modal>

      <Modal
        open={dialog?.kind === "role"}
        title={dialog?.kind === "role" ? `Change role — ${dialog.user.user_id}` : ""}
        onClose={close}
        footer={
          <>
            <button className="btn btn-secondary" onClick={close}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              disabled={busy || (dialog?.kind === "role" && dialog.user.role === newRole)}
              onClick={() =>
                dialog?.kind === "role" &&
                run(() => usersApi.setRole(dialog.user.id, newRole), `Role updated to ${newRole}.`)
              }
            >
              {busy ? <Spinner size={16} /> : "Save role"}
            </button>
          </>
        }
      >
        {dialogError && <div className="alert alert-error">{dialogError}</div>}
        <Field label="Role" hint="The user is signed out everywhere so the new permissions apply immediately.">
          <select className="input" value={newRole} onChange={(e) => setNewRole(e.target.value as RoleName)}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </Field>
      </Modal>

      <Modal
        open={dialog?.kind === "password"}
        title={dialog?.kind === "password" ? `Reset password — ${dialog.user.user_id}` : ""}
        onClose={close}
        footer={
          <>
            <button className="btn btn-secondary" onClick={close}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              disabled={busy || !PASSWORD_RE.test(newPassword)}
              onClick={() =>
                dialog?.kind === "password" &&
                run(() => usersApi.resetPassword(dialog.user.id, newPassword), "Password reset. The user must sign in again.")
              }
            >
              {busy ? <Spinner size={16} /> : "Reset password"}
            </button>
          </>
        }
      >
        {dialogError && <div className="alert alert-error">{dialogError}</div>}
        <Field label="New password" hint="8+ characters with letters and digits. Share it securely.">
          <input className="input" type="password" autoComplete="new-password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
        </Field>
      </Modal>

      <ConfirmDialog
        open={dialog?.kind === "status"}
        title={dialog?.kind === "status" ? `${dialog.user.is_active ? "Disable" : "Enable"} ${dialog.user.user_id}?` : ""}
        message={
          <>
            {dialog?.kind === "status" && dialog.user.is_active
              ? "The user will be signed out and cannot sign in until the account is enabled again."
              : "The user will be able to sign in again."}
            {dialogError && <div className="alert alert-error mt-2">{dialogError}</div>}
          </>
        }
        confirmLabel={dialog?.kind === "status" && dialog.user.is_active ? "Disable account" : "Enable account"}
        tone={dialog?.kind === "status" && dialog.user.is_active ? "danger" : "primary"}
        busy={busy}
        onConfirm={() =>
          dialog?.kind === "status" &&
          run(
            () => usersApi.setStatus(dialog.user.id, !dialog.user.is_active),
            dialog.user.is_active ? "Account disabled." : "Account enabled.",
          )
        }
        onCancel={close}
      />
    </>
  );
}
