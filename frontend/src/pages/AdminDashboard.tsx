import { Link } from "react-router-dom";
import { dashboardApi } from "../api/services";
import { EmployeeTable } from "../components/EmployeeTable";
import { Icon } from "../components/Icon";
import { SectionLoader } from "../components/Spinner";
import { Card, EmptyState, ErrorState, PageHeader, StatCard } from "../components/ui";
import { useAsync } from "../utils/useAsync";

export default function AdminDashboard() {
  const { data, loading, error, reload } = useAsync(() => dashboardApi.admin(), []);

  return (
    <>
      <PageHeader
        title="Admin Dashboard"
        subtitle="System-wide overview of your organization"
        actions={
          <>
            <Link className="btn btn-secondary" to="/users">
              <Icon name="shield" size={16} /> Manage users
            </Link>
            <Link className="btn btn-primary" to="/employees/new">
              <Icon name="plus" size={16} /> Add employee
            </Link>
          </>
        }
      />
      {loading && !data && <SectionLoader />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <div className="stat-grid">
            <StatCard label="Total employees" value={data.total_employees} icon="users" tone="blue" />
            <StatCard label="Active employees" value={data.active_employees} icon="check" tone="green" />
            <StatCard label="Inactive employees" value={data.inactive_employees} icon="alert" tone="slate" />
            <StatCard label="HR users" value={data.total_hr_users} icon="shield" tone="violet" />
            <StatCard
              label="Departments"
              value={data.department_count}
              icon="building"
              tone="amber"
              hint={`${data.designation_count} designations`}
            />
          </div>
          <Card
            title="Recent employee additions"
            actions={
              <Link to="/employees" className="link">
                View directory →
              </Link>
            }
          >
            {data.recent_employees.length === 0 ? (
              <EmptyState
                title="No employees yet"
                message="Create the first employee record to get started."
                action={<Link className="btn btn-primary" to="/employees/new">Add employee</Link>}
              />
            ) : (
              <EmployeeTable employees={data.recent_employees} compact />
            )}
          </Card>
        </>
      )}
    </>
  );
}
