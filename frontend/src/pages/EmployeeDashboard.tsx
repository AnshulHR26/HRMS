import axios from "axios";
import { Link } from "react-router-dom";
import { dashboardApi } from "../api/services";
import { Icon } from "../components/Icon";
import { SectionLoader } from "../components/Spinner";
import { Card, DetailItem, EmptyState, ErrorState, StatusBadge } from "../components/ui";
import { formatDate, tenure } from "../utils/format";
import { useAsync } from "../utils/useAsync";

export default function EmployeeDashboard() {
  const { data, loading, error, reload } = useAsync(
    () =>
      dashboardApi.me().catch((err) => {
        if (axios.isAxiosError(err) && err.response?.status === 404) return null;
        throw err;
      }),
    [],
  );

  if (loading && !data) return <SectionLoader />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (!data)
    return (
      <EmptyState
        title="No employee profile linked"
        message="This account is not linked to an employee record."
      />
    );

  return (
    <>
      <div className="welcome-banner">
        <div>
          <h1>{data.welcome_message}</h1>
          <p>
            {data.designation ?? "Team member"}
            {data.department ? ` · ${data.department}` : ""}
          </p>
        </div>
        <Link className="btn btn-light" to="/profile">
          <Icon name="user" size={16} /> View my profile
        </Link>
      </div>

      <div className="stat-grid stat-grid-4">
        <div className="info-tile">
          <span className="muted small">Employee ID</span>
          <strong className="mono">{data.employee_id}</strong>
        </div>
        <div className="info-tile">
          <span className="muted small">Joined</span>
          <strong>{formatDate(data.joining_date)}</strong>
        </div>
        <div className="info-tile">
          <span className="muted small">Tenure</span>
          <strong>{tenure(data.joining_date)}</strong>
        </div>
        <div className="info-tile">
          <span className="muted small">Status</span>
          <StatusBadge status={data.employment_status} />
        </div>
      </div>

      <Card title="My employment">
        <dl className="detail-grid">
          <DetailItem label="Name" value={data.employee_name} />
          <DetailItem label="Employee ID" value={<span className="mono">{data.employee_id}</span>} />
          <DetailItem label="Department" value={data.department} />
          <DetailItem label="Designation" value={data.designation} />
          <DetailItem label="Joining date" value={formatDate(data.joining_date)} />
          <DetailItem label="Employment status" value={<StatusBadge status={data.employment_status} />} />
          <DetailItem label="Reporting manager" value={data.reporting_manager} />
        </dl>
      </Card>
    </>
  );
}
