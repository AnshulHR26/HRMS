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
import type { Designation, RecordStatus } from "../types";
import { useAsync } from "../utils/useAsync";

interface FormState {
  name: string;
  code: string;
  description: string;
  department_id: string;
  status: RecordStatus;
}

const EMPTY: FormState = { name: "", code: "", description: "", department_id: "", status: "ACTIVE" };

export default function DesignationManagement() {
  const { hasRole } = useAuth();
  const canEdit = hasRole("ADMIN");
  const toast = useToast();
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [search, setSearch] = useState("");
  const departments = useAsync(() => departmentsApi.list(), []);
  const designations = useAsync(
    () =>
      designationsApi.list({
        department_id: departmentFilter ? Number(departmentFilter) : undefined,
        search: search.trim() || undefined,
      }),
    [departmentFilter, search],
  );
  const allDesignations = useAsync(() => designationsApi.list({ status: "ACTIVE" }), []);

  const [editing, setEditing] = useState<Designation | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState<Designation | null>(null);
  const [reassigning, setReassigning] = useState<Designation | null>(null);
  const [target, setTarget] = useState("");

  const openForm = (designation: Designation | null) => {
    setEditing(designation);
    setForm(
      designation
        ? {
            name: designation.name,
            code: designation.code,
            description: designation.description ?? "",
            department_id: String(designation.department_id),
            status: designation.status,
          }
        : { ...EMPTY, department_id: departmentFilter },
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
    if (!form.department_id) clientErrors.department_id = "Select a department";
    setErrors(clientErrors);
    if (Object.keys(clientErrors).length) return;

    const payload = {
      name: form.name.trim(),
      code: form.code.trim(),
      description: form.description.trim() || null,
      department_id: Number(form.department_id),
      status: form.status,
    };
    setBusy(true);
    setFormError(null);
    try {
      if (editing) await designationsApi.update(editing.id, payload);
      else await designationsApi.create(payload);
      toast.success(editing ? "Designation updated." : "Designation created.");
      setFormOpen(false);
      designations.reload();
      allDesignations.reload();
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
      await designationsApi.remove(deleting.id);
      toast.success(`Designation ${deleting.name} deleted.`);
      setDeleting(null);
      designations.reload();
      allDesignations.reload();
    } catch (err) {
      if (axios.isAxiosError(err) && err.response?.status === 409) {
        setReassigning(deleting);
        setTarget("");
        setDeleting(null);
        toast.info("Reassign the employees holding this designation first.");
      } else {
        toast.error(getErrorMessage(err));
      }
    } finally {
      setBusy(false);
    }
  };

  const doReassign = async () => {
    if (!reassigning || !target) return;
    setBusy(true);
    try {
      const result = await designationsApi.reassign(reassigning.id, Number(target));
      toast.success(`${result.moved_employees} employee(s) moved.`);
      setReassigning(null);
      designations.reload();
    } catch (err) {
      toast.error(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Designations"
        subtitle={canEdit ? "Job titles within each department" : "Job titles within each department (read-only for HR)"}
        actions={
          canEdit && (
            <button className="btn btn-primary" onClick={() => openForm(null)}>
              <Icon name="plus" size={16} /> New designation
            </button>
          )
        }
      />
      <Card>
        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={16} />
            <input className="input" placeholder="Search title or code" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select className="input" value={departmentFilter} onChange={(e) => setDepartmentFilter(e.target.value)}>
            <option value="">All departments</option>
            {departments.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
        {designations.error && <ErrorState message={designations.error} onRetry={designations.reload} />}
        {designations.loading && !designations.data && <SectionLoader />}
        {designations.data &&
          (designations.data.length === 0 ? (
            <EmptyState title="No designations" />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Designation</th>
                    <th>Code</th>
                    <th>Department</th>
                    <th>Employees</th>
                    <th>Status</th>
                    {canEdit && <th className="align-right">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {designations.data.map((d) => (
                    <tr key={d.id}>
                      <td>
                        <div className="person-name">{d.name}</div>
                        {d.description && <div className="muted small">{d.description}</div>}
                      </td>
                      <td className="mono">{d.code}</td>
                      <td>{d.department.name}</td>
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
                                  setTarget("");
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
        title={editing ? `Edit ${editing.name}` : "New designation"}
        onClose={() => setFormOpen(false)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setFormOpen(false)}>
              Cancel
            </button>
            <button className="btn btn-primary" type="submit" form="designation-form" disabled={busy}>
              {busy ? <Spinner size={16} /> : "Save"}
            </button>
          </>
        }
      >
        <form id="designation-form" className="form-stack" onSubmit={save} noValidate>
          {formError && <div className="alert alert-error">{formError}</div>}
          <Field label="Title" required error={errors.name}>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} maxLength={100} />
          </Field>
          <Field label="Code" required error={errors.code} hint="Unique code, e.g. ENG-SE">
            <input className="input mono" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} maxLength={20} />
          </Field>
          <Field label="Department" required error={errors.department_id}>
            <select className="input" value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })}>
              <option value="">Select…</option>
              {departments.data
                ?.filter((d) => d.status === "ACTIVE" || String(d.id) === form.department_id)
                .map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Description" error={errors.description}>
            <textarea className="input" rows={3} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
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
            ? `${deleting.employee_count} employee(s) hold this designation. You will be asked to reassign them first.`
            : "This cannot be undone."
        }
        confirmLabel="Delete"
        busy={busy}
        onConfirm={confirmDelete}
        onCancel={() => setDeleting(null)}
      />

      <Modal
        open={!!reassigning}
        title={`Reassign holders of ${reassigning?.name ?? ""}`}
        onClose={() => setReassigning(null)}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setReassigning(null)}>
              Cancel
            </button>
            <button className="btn btn-primary" disabled={busy || !target} onClick={doReassign}>
              {busy ? <Spinner size={16} /> : "Move employees"}
            </button>
          </>
        }
      >
        <Field label="Target designation" required hint="Employees also move to the target's department">
          <select className="input" value={target} onChange={(e) => setTarget(e.target.value)}>
            <option value="">Select…</option>
            {allDesignations.data
              ?.filter((d) => d.id !== reassigning?.id)
              .map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} · {d.department.name}
                </option>
              ))}
          </select>
        </Field>
      </Modal>
    </>
  );
}
