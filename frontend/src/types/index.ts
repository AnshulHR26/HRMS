// Mirrors the backend Pydantic response/request schemas.

export type RoleName = "ADMIN" | "HR" | "EMPLOYEE";
export type Gender = "MALE" | "FEMALE" | "OTHER" | "PREFER_NOT_TO_SAY";
export type EmploymentType = "FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERN";
export type EmploymentStatus = "ACTIVE" | "PROBATION" | "NOTICE_PERIOD" | "INACTIVE" | "TERMINATED";
export type RecordStatus = "ACTIVE" | "INACTIVE";

export const WORKING_STATUSES: EmploymentStatus[] = ["ACTIVE", "PROBATION", "NOTICE_PERIOD"];

export interface EmployeeLink {
  id: number;
  employee_id: string;
  full_name: string;
}

export interface User {
  id: number;
  user_id: string;
  role: RoleName;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
  employee: EmployeeLink | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Summary {
  id: number;
  name: string;
  code: string;
}

export interface ManagerSummary {
  id: number;
  employee_id: string;
  full_name: string;
}

export interface Employee {
  id: number;
  employee_id: string;
  user_id: string;
  role: RoleName;
  account_active: boolean;
  full_name: string;
  email: string;
  phone_number: string | null;
  gender: Gender | null;
  date_of_birth: string | null;
  address: string | null;
  department: Summary | null;
  designation: Summary | null;
  joining_date: string;
  employment_type: EmploymentType;
  employment_status: EmploymentStatus;
  reporting_manager: ManagerSummary | null;
  created_at: string;
  updated_at: string;
}

export interface EmployeeListItem {
  id: number;
  employee_id: string;
  full_name: string;
  email: string;
  phone_number: string | null;
  department: Summary | null;
  designation: Summary | null;
  joining_date: string;
  employment_type: EmploymentType;
  employment_status: EmploymentStatus;
  created_at: string;
}

export interface EmployeeProfileInput {
  full_name: string;
  email: string;
  phone_number: string | null;
  gender: Gender | null;
  date_of_birth: string | null;
  address: string | null;
  department_id: number | null;
  designation_id: number | null;
  joining_date: string;
  employment_type: EmploymentType;
  reporting_manager_id: number | null;
}

export interface EmployeeCreateInput extends EmployeeProfileInput {
  employment_status: "ACTIVE" | "PROBATION";
  account: { user_id: string; password: string; role: RoleName };
}

export interface EmployeeQuery {
  page?: number;
  page_size?: number;
  search?: string;
  department_id?: number;
  designation_id?: number;
  employment_status?: EmploymentStatus;
  employment_type?: EmploymentType;
  sort_by?: "employee_id" | "full_name" | "email" | "joining_date" | "created_at" | "employment_status";
  sort_order?: "asc" | "desc";
}

export interface Department {
  id: number;
  name: string;
  code: string;
  description: string | null;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
  employee_count: number;
  designation_count: number;
}

export interface DepartmentInput {
  name: string;
  code: string;
  description: string | null;
  status: RecordStatus;
}

export interface Designation {
  id: number;
  name: string;
  code: string;
  description: string | null;
  department_id: number;
  department: Summary;
  status: RecordStatus;
  created_at: string;
  updated_at: string;
  employee_count: number;
}

export interface DesignationInput {
  name: string;
  code: string;
  description: string | null;
  department_id: number;
  status: RecordStatus;
}

export interface Role {
  id: number;
  name: RoleName;
  description: string | null;
}

export interface EmployeeCounts {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
}

export interface DepartmentHeadcount {
  department_id: number | null;
  department_name: string;
  employee_count: number;
  active_count: number;
}

export interface AdminDashboardData extends EmployeeCounts {
  total_hr_users: number;
  department_count: number;
  designation_count: number;
  total_users: number;
  recent_employees: EmployeeListItem[];
}

export interface HRDashboardData extends EmployeeCounts {
  department_headcount: DepartmentHeadcount[];
  recent_employees: EmployeeListItem[];
}

export interface EmployeeDashboardData {
  welcome_message: string;
  employee_name: string;
  employee_id: string;
  department: string | null;
  designation: string | null;
  joining_date: string;
  employment_status: EmploymentStatus;
  reporting_manager: string | null;
}

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details: unknown;
  };
}
