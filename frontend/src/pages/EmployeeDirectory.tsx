import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { departmentsApi, designationsApi, employeesApi } from "../api/services";
import { EmployeeTable } from "../components/EmployeeTable";
import { Icon } from "../components/Icon";
import { SectionLoader } from "../components/Spinner";
import { Card, EmptyState, ErrorState, PageHeader, Pagination } from "../components/ui";
import type { EmployeeQuery, EmploymentStatus, EmploymentType } from "../types";
import { humanize } from "../utils/format";
import { useAsync } from "../utils/useAsync";

const STATUSES: EmploymentStatus[] = ["ACTIVE", "PROBATION", "NOTICE_PERIOD", "INACTIVE", "TERMINATED"];
const TYPES: EmploymentType[] = ["FULL_TIME", "PART_TIME", "CONTRACT", "INTERN"];
const PAGE_SIZE = 10;

export default function EmployeeDirectory() {
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState<EmployeeQuery>({
    page: 1,
    page_size: PAGE_SIZE,
    sort_by: "created_at",
    sort_order: "desc",
  });

  // Debounce the free-text search so we do not query on every keystroke.
  useEffect(() => {
    const handle = window.setTimeout(() => {
      setQuery((q) => (q.search === (searchInput.trim() || undefined) ? q : { ...q, search: searchInput.trim() || undefined, page: 1 }));
    }, 300);
    return () => window.clearTimeout(handle);
  }, [searchInput]);

  const departments = useAsync(() => departmentsApi.list(), []);
  const designations = useAsync(
    () => (query.department_id ? designationsApi.list({ department_id: query.department_id }) : Promise.resolve([])),
    [query.department_id],
  );
  const employees = useAsync(() => employeesApi.list(query), [JSON.stringify(query)]);

  const update = (patch: Partial<EmployeeQuery>) => setQuery((q) => ({ ...q, ...patch, page: patch.page ?? 1 }));

  const onSort = (field: NonNullable<EmployeeQuery["sort_by"]>) =>
    setQuery((q) => ({
      ...q,
      sort_by: field,
      sort_order: q.sort_by === field && q.sort_order === "asc" ? "desc" : "asc",
      page: 1,
    }));

  const hasFilters = !!(query.search || query.department_id || query.employment_status || query.employment_type);

  return (
    <>
      <PageHeader
        title="Employee Directory"
        subtitle={employees.data ? `${employees.data.total} employee record(s)` : "Search and filter employee records"}
        actions={
          <Link className="btn btn-primary" to="/employees/new">
            <Icon name="plus" size={16} /> Add employee
          </Link>
        }
      />
      <Card>
        <div className="toolbar">
          <div className="search-box">
            <Icon name="search" size={16} />
            <input
              className="input"
              placeholder="Search name, email, employee ID or phone"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              aria-label="Search employees"
            />
          </div>
          <select
            className="input"
            value={query.department_id ?? ""}
            onChange={(e) =>
              update({ department_id: e.target.value ? Number(e.target.value) : undefined, designation_id: undefined })
            }
            aria-label="Filter by department"
          >
            <option value="">All departments</option>
            {departments.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={query.designation_id ?? ""}
            disabled={!query.department_id}
            onChange={(e) => update({ designation_id: e.target.value ? Number(e.target.value) : undefined })}
            aria-label="Filter by designation"
          >
            <option value="">All designations</option>
            {designations.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={query.employment_status ?? ""}
            onChange={(e) => update({ employment_status: (e.target.value || undefined) as EmploymentStatus | undefined })}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {humanize(s)}
              </option>
            ))}
          </select>
          <select
            className="input"
            value={query.employment_type ?? ""}
            onChange={(e) => update({ employment_type: (e.target.value || undefined) as EmploymentType | undefined })}
            aria-label="Filter by employment type"
          >
            <option value="">All types</option>
            {TYPES.map((t) => (
              <option key={t} value={t}>
                {humanize(t)}
              </option>
            ))}
          </select>
          {hasFilters && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={() => {
                setSearchInput("");
                setQuery({ page: 1, page_size: PAGE_SIZE, sort_by: query.sort_by, sort_order: query.sort_order });
              }}
            >
              Clear filters
            </button>
          )}
        </div>

        {employees.error && <ErrorState message={employees.error} onRetry={employees.reload} />}
        {employees.loading && !employees.data && <SectionLoader />}
        {employees.data &&
          (employees.data.items.length === 0 ? (
            <EmptyState
              title="No employees found"
              message={hasFilters ? "Try adjusting your search or filters." : "Add your first employee to get started."}
            />
          ) : (
            <div className={employees.loading ? "is-refreshing" : ""}>
              <EmployeeTable
                employees={employees.data.items}
                sortBy={query.sort_by}
                sortOrder={query.sort_order}
                onSort={onSort}
              />
              <Pagination
                page={employees.data.page}
                pages={employees.data.pages}
                total={employees.data.total}
                pageSize={employees.data.page_size}
                onChange={(page) => setQuery((q) => ({ ...q, page }))}
              />
            </div>
          ))}
      </Card>
    </>
  );
}
