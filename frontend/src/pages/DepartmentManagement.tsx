import axios from "axios";
import { useState, type FormEvent } from "react";
import { getErrorMessage, getFieldErrors } from "../api/client";
import { departmentsApi, designationsApi } from "../api/services";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { ConfirmDialog, Modal } from "../components/Modal";
import { SectionLoader, Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";
import { Card, EmptyState, ErrorState, Field, PageHeader, StatusBadge } from "../components/ui";
import type { Department, DepartmentInput, RecordStatus } from "../types";
import { useAsync } from "../utils/useAsync";

const EMPTY: DepartmentInput = { name: "", code: "", description: "", status: "ACTIVE" };

export default function DepartmentManagement() {
  const { hasRole } = useAuth();
  const canEdit = hasRole("ADMIN");
  const toast = useToast();
  const [search, setSearch] = useState("");
  const departments = useAsync(() => departmentsApi.list({ search: search.trim() || undefined }), [search]);

  const [editing, setEditing] = useState<Department | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<DepartmentInput>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [deleting, setDeleting] = useState<Department | null>(null);
  const [reassigning, setReassigning] = useState<Department | null>(null);
  const [target, setTarget] = useState({ department: "", designation: "" });
  const targetDesignations = useAsync(
    () => (target.department ? designationsApi.list({ department_id: Number(target.department), status: "ACTIVE" }) : Promise.resolve([])),
    [target.department],
  );

  const openForm = (department: Department | null) => {
    setEditing(department);
    setForm(
      department
        ? { name: department.name, code: department.code, description: department.description ?? "", status: department.status }
        : EMPTY,
    );
    setErrors({});
    setFormError(null);
    setFormOpen(true);
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    const clientErrors: Record<string, string> = {};
    if (form.name.trim().length < 2) clientErrors.name = "Name must be at least 2 characters";
    if (!/^[A-Za-z0-9_-]{2,20}$/.test(form.code.trim())) clientErrors.code = "2–20 letters, digits, - or _";
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;

    setBusy(true);
    setFormError(null);
    const payload = { ...form, name: form.name.trim(), code: form.code.trim(), description: form.description?.trim() || null };
    try {
      if (editing) await departmentsApi.update(editing.id, payload);
      else await departmentsApi.create(payload);
      toast.success(editing ? "Department updated." : "Department created.");
      setFormOpen(false);
      departments.reload();
    } catch (err) {
      setErrors(getFieldErrors(err));
      setFormError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const confirmDelete = async () => {
    if (!deleting) return;
    setBusy(true);
    try {
      await departmentsApi.remove(deleting.id);
      toast.success(`Department ${deleting.name} deleted.`);
      departments.reload();
      setDeleting(null);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        // Employees are still assigned: switch to the reassignment flow.
        setReassigning(deleting);
        setTarget({ department: "", designation: "" });
        setDeleting(null);
        toast.info("Reassign the employees first, then delete the department.");
      } else {
        toast.error(getErrorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  };

  const doReassign = async () => {
    if (!reassigning || !target.department) return;
    setBusy(true);
    try {
      const result = await departmentsApi.reassign(
        reassigning.id,
        Number(target.department),
        target.designation ? Number(target.designation) : null,
      );
      toast.success(`${result.moved_employees} employee(s) moved. You can now delete ${reassigning.name}.`);
      setReassigning(null);
      departments.reload();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Departments"
        subtitle={canEdit ? "Create and maintain the organization structure" : "Organization structure (read-only for HR)"}
        actions={
          canEdit && (
            <button className="btn btn-primary" onClick={() => openForm(null)}>
              <Icon name="plus" size={16} /> New department
            </button>
          )
        }
      />
      <Card>
        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={16} />
            <input className="input" placeholder="Search name or code" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
        </div>
        {departments.error && <ErrorState message={departments.error} onRetry={departments.reload} />}
        {departments.loading && !departments.data && <SectionLoader />}
        {departments.data &&
          (departments.data.length === 0 ? (
            <EmptyState title="No departments" message={canEdit ? "Create your first department." : undefined} />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Department</th>
                    <th>Code</th>
                    <th>Designations</th>
                    <th>Employees</th>
                    <th>Status</th>
                    {canEdit && <th className="align-right">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {departments.data.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <div className="person-name">{d.name}</div>
                        {d.description && <div className="muted small">{d.description}</div>}
                      </td>
                      <td className="mono">{d.code}</td>
                      <td>{d.designation_count}</td>
                      <td>{d.employee_count}</td>
                      <td>
                        <StatusBadge status={d.status} />
                      </td>
                      {canEdit && (
                        <td className="align-right">
                          <div className="row-actions">
                            <button className="btn btn-ghost btn-sm" onClick={() => openForm(d)}>
                              <Icon name="edit" size={14} /> Edit
                            </button>
                            {d.employee_count > 0 && (
                              <button
                                className="btn btn-ghost btn-sm"
                                onClick={() => {
                                  setReassigning(d);
                                  setTarget({ department: "", designation: "" });
                                }}
                              >
                                <Icon name="swap" size={14} /> Reassign
                              </button>
                            )}
                            <button className="btn btn-danger-outline btn-sm" onClick={() => setDeleting(d)}>
                              <Icon name="trash" size={14} />
                            </button>
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
      </Card>

      <Modal
        open={formOpen}
        title={editing ? `Edit ${editing.name}` : "New department"}
        onClose={() => setFormOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setFormOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" type="submit" form="department-form" disabled={busy}>
              {busy ? <Spinner size={16} /> : "Save"}
            </button>
          </>
        }
      >
        <form id="department-form" className="form-stack" onSubmit={save} noValidate>
          {formError && <div className="alert alert-error">{formError}</div>}
          <Field label="Name" required error={errors.name}>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={100} />
          </Field>
          <Field label="Code" required error={errors.code} hint="Short unique code, e.g. ENG">
            <input className="input mono" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} maxLength={20} />
          </Field>
          <Field label="Description" error={errors.description}>
            <textarea className="input" rows={3} value={form.description ?? ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </Field>
          <Field label="Status" required>
            <select className="input" value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value as RecordStatus })}>
              <option value="ACTIVE">Active</option>
              <option value="INACTIVE">Inactive</option>
            </select>
          </Field>
        </form>
      </Modal>

      <ConfirmDialog
        open={!!deleting}
        title={`Delete ${deleting?.name ?? ""}?`}
        message={
          deleting && deleting.employee_count > 0
            ? `${deleting.employee_count} employee(s) are assigned. You will be asked to reassign them first.`
            : "This also removes its designations. This cannot be undone."
        }
        confirmLabel="Delete"
        busy={busy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />

      <Modal
        open={!!reassigning}
        title={`Reassign employees of ${reassigning?.name ?? ""}`}
        onClose={() => setReassigning(null)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setReassigning(null)}>
              Cancel
            </button>
            <button className="btn btn-primary" disabled={busy || !target.department} onClick={doReassign}>
              {busy ? <Spinner size={16} /> : "Move employees"}
            </button>
          </>
        }
      >
        <div className="form-stack">
          <p className="muted">
            All {reassigning?.employee_count ?? 0} employee(s) will move to the selected department.
          </p>
          <Field label="Target department" required>
            <select className="input" value={target.department} onChange={(e) => setTarget({ department: e.target.value, designation: "" })}>
              <option value="">Select…</option>
              {departments.data
                ?.filter((d) => d.id !== reassigning?.id && d.status === "ACTIVE")
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Target designation" hint="Optional — otherwise their designation is cleared">
            <select
              className="input"
              value={target.designation}
              disabled={!target.department}
              onChange={(e) => setTarget({ ...target, designation: e.target.value })}
            >
              <option value="">None</option>
              {targetDesignations.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </Field>
        </div>
      </Modal>
    </>
  );
}
