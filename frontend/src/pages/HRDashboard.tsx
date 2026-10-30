import { Link } from "react-router-dom";
import { dashboardApi } from "../api/services";
import { EmployeeTable } from "../components/EmployeeTable";
import { Icon } from "../components/Icon";
import { SectionLoader } from "../components/Spinner";
import { Card, EmptyState, ErrorState, PageHeader, StatCard } from "../components/ui";
import { useAsync } from "../utils/useAsync";

export default function HRDashboard() {
  const { data, loading, error, reload } = useAsync(() => dashboardApi.hr(), []);
  const maxCount = Math.max(1, ...(data?.department_headcount.map((d) => d.employee_count) ?? [1]));

  return (
    <>
      <PageHeader
        title="HR Dashboard"
        subtitle="Workforce at a glance"
        actions={
          <Link className="btn btn-primary" to="/employees/new">
            <Icon name="plus" size={16} /> Add employee
          </Link>
        }
      />
      {loading && !data && <SectionLoader />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <div className="stat-grid stat-grid-3">
            <StatCard label="Total employees" value={data.total_employees} icon="users" tone="blue" />
            <StatCard label="Active employees" value={data.active_employees} icon="check" tone="green" />
            <StatCard label="Inactive employees" value={data.inactive_employees} icon="alert" tone="slate" />
          </div>
          <div className="grid-2">
            <Card title="Department-wise headcount">
              {data.department_headcount.length === 0 ? (
                <EmptyState title="No departments yet" />
              ) : (
                <ul className="bar-list" aria-label="Employees per department">
                  {data.department_headcount.map((row) => (
                    <li key={row.department_id ?? "none"}>
                      <div className="bar-row">
                        <span>{row.department_name}</span>
                        <span className="muted small">
                          <strong className="text-strong">{row.employee_count}</strong> · {row.active_count} active
                        </span>
                      </div>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${(row.employee_count / maxCount) * 100}%` }} />
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card
              title="Employee directory"
              actions={
                <Link to="/employees" className="link">
                  Open full directory →
                </Link>
              }
            >
              {data.recent_employees.length === 0 ? (
                <EmptyState title="No employees yet" />
              ) : (
                <EmployeeTable employees={data.recent_employees} compact />
              )}
            </Card>
          </div>
        </>
      )}
    </>
  );
}
