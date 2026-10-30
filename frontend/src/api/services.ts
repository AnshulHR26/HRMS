import { api } from "./client";
import type {
  AdminDashboardData,
  Department,
  DepartmentInput,
  Designation,
  DesignationInput,
  Employee,
  EmployeeCreateInput,
  EmployeeDashboardData,
  EmployeeListItem,
  EmployeeProfileInput,
  EmployeeQuery,
  EmploymentStatus,
  HRDashboardData,
  Page,
  RecordStatus,
  Role,
  RoleName,
  TokenResponse,
  User,
} from "../types";

/** Drop empty filter values so they are not sent as `?search=`. */
function clean<T extends object>(params: T): Partial<T> {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== undefined && value !== null && value !== ""),
  ) as Partial<T>;
}

export const authApi = {
  login: (user_id: string, password: string) =>
    api.post<TokenResponse>("/auth/login", { user_id, password }).then((r) => r.data),
  me: () => api.get<User>("/auth/me").then((r) => r.data),
  logout: () => api.post("/auth/logout"),
  changePassword: (current_password: string, new_password: string) =>
    api.post("/auth/change-password", { current_password, new_password }),
};

export const employeesApi = {
  list: (query: EmployeeQuery) =>
    api.get<Page<EmployeeListItem>>("/employees", { params: clean(query) }).then((r) => r.data),
  get: (employeeId: string) => api.get<Employee>(`/employees/${employeeId}`).then((r) => r.data),
  me: () => api.get<Employee>("/employees/me").then((r) => r.data),
  create: (data: EmployeeCreateInput) => api.post<Employee>("/employees", data).then((r) => r.data),
  update: (employeeId: string, data: EmployeeProfileInput) =>
    api.put<Employee>(`/employees/${employeeId}`, data).then((r) => r.data),
  setStatus: (employeeId: string, employment_status: EmploymentStatus) =>
    api.patch<Employee>(`/employees/${employeeId}/status`, { employment_status }).then((r) => r.data),
  updateMe: (data: { phone_number?: string | null; address?: string | null }) =>
    api.patch<Employee>("/employees/me", data).then((r) => r.data),
};

export const usersApi = {
  list: (query: { page?: number; page_size?: number; search?: string; role?: RoleName; is_active?: boolean }) =>
    api.get<Page<User>>("/users", { params: clean(query) }).then((r) => r.data),
  create: (data: { user_id: string; password: string; role: RoleName; is_active: boolean }) =>
    api.post<User>("/users", data).then((r) => r.data),
  rename: (id: number, user_id: string) => api.patch<User>(`/users/${id}`, { user_id }).then((r) => r.data),
  setRole: (id: number, role: RoleName) => api.patch<User>(`/users/${id}/role`, { role }).then((r) => r.data),
  setStatus: (id: number, is_active: boolean) =>
    api.patch<User>(`/users/${id}/status`, { is_active }).then((r) => r.data),
  resetPassword: (id: number, new_password: string) =>
    api.post(`/users/${id}/reset-password`, { new_password }),
};

export const rolesApi = {
  list: () => api.get<Role[]>("/roles").then((r) => r.data),
};

export const departmentsApi = {
  list: (params: { status?: RecordStatus; search?: string } = {}) =>
    api.get<Department[]>("/departments", { params: clean(params) }).then((r) => r.data),
  create: (data: DepartmentInput) => api.post<Department>("/departments", data).then((r) => r.data),
  update: (id: number, data: DepartmentInput) =>
    api.put<Department>(`/departments/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/departments/${id}`),
  reassign: (id: number, target_department_id: number, target_designation_id: number | null) =>
    api
      .post<{ moved_employees: number }>(`/departments/${id}/reassign-employees`, {
        target_department_id,
        target_designation_id,
      })
      .then((r) => r.data),
};

export const designationsApi = {
  list: (params: { department_id?: number; status?: RecordStatus; search?: string } = {}) =>
    api.get<Designation[]>("/designations", { params: clean(params) }).then((r) => r.data),
  create: (data: DesignationInput) => api.post<Designation>("/designations", data).then((r) => r.data),
  update: (id: number, data: DesignationInput) =>
    api.put<Designation>(`/designations/${id}`, data).then((r) => r.data),
  remove: (id: number) => api.delete(`/designations/${id}`),
  reassign: (id: number, target_designation_id: number) =>
    api
      .post<{ moved_employees: number }>(`/designations/${id}/reassign-employees`, { target_designation_id })
      .then((r) => r.data),
};

export const dashboardApi = {
  admin: () => api.get<AdminDashboardData>("/dashboard/admin").then((r) => r.data),
  hr: () => api.get<HRDashboardData>("/dashboard/hr").then((r) => r.data),
  me: () => api.get<EmployeeDashboardData>("/dashboard/me").then((r) => r.data),
};
