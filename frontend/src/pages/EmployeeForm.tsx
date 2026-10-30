import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getErrorMessage, getFieldErrors } from "../api/client";
import { departmentsApi, designationsApi, employeesApi } from "../api/services";
import { useAuth } from "../auth/AuthContext";
import { Icon } from "../components/Icon";
import { SectionLoader, Spinner } from "../components/Spinner";
import { useToast } from "../components/Toast";
import { Card, ErrorState, Field, PageHeader } from "../components/ui";
import type { EmploymentType, Gender, RoleName } from "../types";
import { humanize } from "../utils/format";
import { useAsync } from "../utils/useAsync";

interface FormState {
  full_name: string;
  email: string;
  phone_number: string;
  gender: Gender | "";
  date_of_birth: string;
  address: string;
  department_id: string;
  designation_id: string;
  joining_date: string;
  employment_type: EmploymentType;
  reporting_manager_id: string;
  employment_status: "ACTIVE" | "PROBATION";
  user_id: string;
  password: string;
  role: RoleName;
}

const EMPTY: FormState = {
  full_name: "",
  email: "",
  phone_number: "",
  gender: "",
  date_of_birth: "",
  address: "",
  department_id: "",
  designation_id: "",
  joining_date: new Date().toISOString().slice(0, 10),
  employment_type: "FULL_TIME",
  reporting_manager_id: "",
  employment_status: "ACTIVE",
  user_id: "",
  password: "",
  role: "EMPLOYEE",
};

const GENDERS: Gender[] = ["MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"];
const TYPES: EmploymentType[] = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERN"];
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const USER_ID_RE = /^[A-Za-z0-9._-]{3,50}$/;
const PASSWORD_RE = /^(?=.*[A-Za-z])(?=.*\d).{8,128}$/;
const PHONE_RE = /^\+?[0-9][0-9\s\-()]{5,18}$/;

function validate(form: FormState, mode: "create" | "edit"): Record<string, string> {
  const errors: Record<string, string> = {};
  if (form.full_name.trim().length < 2) errors.full_name = "Full name must be at least 2 characters";
  if (!EMAIL_RE.test(form.email.trim())) errors.email = "Enter a valid email address";
  if (form.phone_number && !PHONE_RE.test(form.phone_number.trim())) errors.phone_number = "Enter a valid phone number";
  if (!form.joining_date) errors.joining_date = "Joining date is required";
  if (form.date_of_birth && form.date_of_birth >= new Date().toISOString().slice(0, 10))
    errors.date_of_birth = "Date of birth must be in the past";
  if (form.designation_id && !form.department_id) errors.department_id = "Select a department for this designation";
  if (mode === "create") {
    if (!USER_ID_RE.test(form.user_id.trim())) errors.user_id = "3–50 letters, digits, dot, underscore or hyphen";
    if (!PASSWORD_RE.test(form.password)) errors.password = "8+ characters with at least one letter and one digit";
  }
  return errors;
}

export default function EmployeeForm({ mode }: { mode: "create" | "edit" }) {
  const { employeeId = "" } = useParams();
  const { hasRole } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const existing = useAsync(
    () => (mode === "edit" ? employeesApi.get(employeeId) : Promise.resolve(null)),
    [mode, employeeId],
  );
  const departments = useAsync(() => departmentsApi.list(), []);
  const designations = useAsync(
    () => (form.department_id ? designationsApi.list({ department_id: Number(form.department_id) }) : Promise.resolve([])),
    [form.department_id],
  );
  const managers = useAsync(
    () => employeesApi.list({ page_size: 100, employment_status: "ACTIVE", sort_by: "full_name", sort_order: "asc" }),
    [],
  );

  useEffect(() => {
    const e = existing.data;
    if (!e) return;
    setForm({
      ...EMPTY,
      full_name: e.full_name,
      email: e.email,
      phone_number: e.phone_number ?? "",
      gender: e.gender ?? "",
      date_of_birth: e.date_of_birth ?? "",
      address: e.address ?? "",
      department_id: e.department ? String(e.department.id) : "",
      designation_id: e.designation ? String(e.designation.id) : "",
      joining_date: e.joining_date,
      employment_type: e.employment_type,
      reporting_manager_id: e.reporting_manager ? String(e.reporting_manager.id) : "",
    });
  }, [existing.data]);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setForm((f) => ({ ...f, [key]: value, ...(key === "department_id" ? { designation_id: "" } : {}) }));
    setErrors((errs) => ({ ...errs, [key]: "" }));
  };

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const clientErrors = validate(form, mode);
    setErrors(clientErrors);
    if (Object.values(clientErrors).some(Boolean)) return;

    const profile = {
      full_name: form.full_name.trim(),
      email: form.email.trim(),
      phone_number: form.phone_number.trim() || null,
      gender: form.gender || null,
      date_of_birth: form.date_of_birth || null,
      address: form.address.trim() || null,
      department_id: form.department_id ? Number(form.department_id) : null,
      designation_id: form.designation_id ? Number(form.designation_id) : null,
      joining_date: form.joining_date,
      employment_type: form.employment_type,
      reporting_manager_id: form.reporting_manager_id ? Number(form.reporting_manager_id) : null,
    };

    setSubmitting(true);
    setFormError(null);
    try {
      const saved =
        mode === "create"
          ? await employeesApi.create({
              ...profile,
              employment_status: form.employment_status,
              account: { user_id: form.user_id.trim(), password: form.password, role: form.role },
            })
          : await employeesApi.update(employeeId, profile);
      toast.success(mode === "create" ? `Employee ${saved.employee_id} created.` : "Employee updated.");
      navigate(`/employees/${saved.employee_id}`, { replace: true });
    } catch (err) {
      setErrors(getFieldErrors(err));
      setFormError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (mode === "edit" && existing.loading) return <SectionLoader />;
  if (mode === "edit" && existing.error) return <ErrorState message={existing.error} onRetry={existing.reload} />;

  const managerOptions = (managers.data?.items ?? []).filter((m) => m.employee_id !== employeeId);
  const activeDepartments = (departments.data ?? []).filter(
    (d) => d.status === "ACTIVE" || String(d.id) === form.department_id,
  );
  const activeDesignations = (designations.data ?? []).filter(
    (d) => d.status === "ACTIVE" || String(d.id) === form.designation_id,
  );
  const roleOptions: RoleName[] = hasRole("ADMIN") ? ["EMPLOYEE", "HR", "ADMIN"] : ["EMPLOYEE"];

  return (
    <>
      <PageHeader
        title={mode === "create" ? "Create Employee" : `Edit ${existing.data?.full_name ?? "Employee"}`}
        subtitle={
          mode === "create"
            ? "Creates the employee profile and its login account. The Employee ID is generated automatically."
            : `Employee ID ${employeeId} · identifiers, role and status cannot be changed here`
        }
        actions={
          <Link className="btn btn-secondary" to={mode === "create" ? "/employees" : `/employees/${employeeId}`}>
            Cancel
          </Link>
        }
      />
      <form onSubmit={onSubmit} noValidate className="form-stack">
        {formError && (
          <div className="alert alert-error" role="alert">
            <Icon name="alert" size={16} /> {formError}
          </div>
        )}

        <Card title="Personal information">
          <div className="form-grid">
            <Field label="Full name" required error={errors.full_name}>
              <input className="input" value={form.full_name} onChange={(e) => set("full_name", e.target.value)} maxLength={150} />
            </Field>
            <Field label="Email address" required error={errors.email}>
              <input className="input" type="email" value={form.email} onChange={(e) => set("email", e.target.value)} maxLength={255} />
            </Field>
            <Field label="Phone number" error={errors.phone_number} hint="e.g. +91 98765 43210">
              <input className="input" value={form.phone_number} onChange={(e) => set("phone_number", e.target.value)} maxLength={20} />
            </Field>
            <Field label="Gender" error={errors.gender}>
              <select className="input" value={form.gender} onChange={(e) => set("gender", e.target.value as Gender | "")}>
                <option value="">Not specified</option>
                {GENDERS.map((g) => (
                  <option key={g} value={g}>
                    {humanize(g)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Date of birth" error={errors.date_of_birth}>
              <input className="input" type="date" value={form.date_of_birth} onChange={(e) => set("date_of_birth", e.target.value)} />
            </Field>
            <Field label="Address" error={errors.address}>
              <textarea className="input" rows={2} value={form.address} onChange={(e) => set("address", e.target.value)} maxLength={1000} />
            </Field>
          </div>
        </Card>

        <Card title="Employment details">
          <div className="form-grid">
            <Field label="Department" error={errors.department_id}>
              <select className="input" value={form.department_id} onChange={(e) => set("department_id", e.target.value)}>
                <option value="">Unassigned</option>
                {activeDepartments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.code})
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Designation" error={errors.designation_id} hint={form.department_id ? undefined : "Select a department first"}>
              <select
                className="input"
                value={form.designation_id}
                disabled={!form.department_id}
                onChange={(e) => set("designation_id", e.target.value)}
              >
                <option value="">None</option>
                {activeDesignations.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Joining date" required error={errors.joining_date}>
              <input className="input" type="date" value={form.joining_date} onChange={(e) => set("joining_date", e.target.value)} />
            </Field>
            <Field label="Employment type" required error={errors.employment_type}>
              <select className="input" value={form.employment_type} onChange={(e) => set("employment_type", e.target.value as EmploymentType)}>
                {TYPES.map((t) => (
                  <option key={t} value={t}>
                    {humanize(t)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Reporting manager" error={errors.reporting_manager_id}>
              <select className="input" value={form.reporting_manager_id} onChange={(e) => set("reporting_manager_id", e.target.value)}>
                <option value="">No manager</option>
                {managerOptions.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.full_name} · {m.employee_id}
                  </option>
                ))}
              </select>
            </Field>
            {mode === "create" && (
              <Field label="Initial status" required>
                <select
                  className="input"
                  value={form.employment_status}
                  onChange={(e) => set("employment_status", e.target.value as "ACTIVE" | "PROBATION")}
                >
                  <option value="ACTIVE">Active</option>
                  <option value="PROBATION">Probation</option>
                </select>
              </Field>
            )}
          </div>
        </Card>

        {mode === "create" && (
          <Card title="Login account">
            <div className="form-grid">
              <Field label="User ID" required error={errors.user_id} hint="Used to sign in, e.g. jane.doe">
                <input className="input" autoComplete="off" value={form.user_id} onChange={(e) => set("user_id", e.target.value)} maxLength={50} />
              </Field>
              <Field label="Initial password" required error={errors.password} hint="8+ characters, letters and digits">
                <input
                  className="input"
                  type="password"
                  autoComplete="new-password"
                  value={form.password}
                  onChange={(e) => set("password", e.target.value)}
                  maxLength={128}
                />
              </Field>
              <Field label="Role" required error={errors.role} hint={hasRole("ADMIN") ? undefined : "HR can create EMPLOYEE accounts only"}>
                <select className="input" value={form.role} onChange={(e) => set("role", e.target.value as RoleName)} disabled={roleOptions.length === 1}>
                  {roleOptions.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </Field>
            </div>
          </Card>
        )}

        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? <Spinner size={16} /> : mode === "create" ? "Create employee" : "Save changes"}
          </button>
        </div>
      </form>
    </>
  );
}
