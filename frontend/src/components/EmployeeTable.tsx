import { useNavigate } from "react-router-dom";
import type { EmployeeListItem } from "../types";
import { formatDate, humanize } from "../utils/format";
import { Avatar, StatusBadge } from "./ui";

interface Props {
  employees: EmployeeListItem[];
  compact?: boolean;
  sortBy?: string;
  sortOrder?: "asc" | "desc";
  onSort?: (field: "employee_id" | "full_name" | "joining_date" | "employment_status") => void;
}

export function EmployeeTable({ employees, compact = false, sortBy, sortOrder, onSort }: Props) {
  const navigate = useNavigate();

  const header = (label: string, field?: "employee_id" | "full_name" | "joining_date" | "employment_status") => {
    if (!field || !onSort) return <th>{label}</th>;
    const active = sortBy === field;
    return (
      <th aria-sort={active ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
        <button className={`sort-btn ${active ? "active" : ""}`} onClick={() => onSort(field)}>
          {label}
          <span className="sort-arrow">{active ? (sortOrder === "asc" ? "▲" : "▼") : "↕"}</span>
        </button>
      </th>
    );
  };

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {header("Employee", "full_name")}
            {header("Employee ID", "employee_id")}
            <th>Department</th>
            {!compact && <th>Designation</th>}
            {!compact && <th>Type</th>}
            {header("Joined", "joining_date")}
            {header("Status", "employment_status")}
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr
              key={employee.id}
              className="clickable"
              tabIndex={0}
              onClick={() => navigate(`/employees/${employee.employee_id}`)}
              onKeyDown={(e) => e.key === "Enter" && navigate(`/employees/${employee.employee_id}`)}
            >
              <td>
                <div className="person-cell">
                  <Avatar name={employee.full_name} size={32} />
                  <div>
                    <div className="person-name">{employee.full_name}</div>
                    <div className="muted small">{employee.email}</div>
                  </div>
                </div>
              </td>
              <td className="mono">{employee.employee_id}</td>
              <td>{employee.department?.name ?? <span className="muted">Unassigned</span>}</td>
              {!compact && <td>{employee.designation?.name ?? <span className="muted">—</span>}</td>}
              {!compact && <td>{humanize(employee.employment_type)}</td>}
              <td>{formatDate(employee.joining_date)}</td>
              <td>
                <StatusBadge status={employee.employment_status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
