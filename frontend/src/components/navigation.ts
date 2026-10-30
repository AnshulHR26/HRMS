import type { RoleName } from "../types";
import type { IconName } from "./Icon";

export interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  roles: RoleName[];
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

// Future phases (Attendance, Leave, Payroll, Performance) add entries here.
export const NAV_SECTIONS: NavSection[] = [
  {
    title: "Overview",
    items: [
      { to: "/dashboard/admin", label: "Admin Dashboard", icon: "dashboard", roles: ["ADMIN"] },
      { to: "/dashboard/hr", label: "HR Dashboard", icon: "activity", roles: ["ADMIN", "HR"] },
      { to: "/dashboard/me", label: "My Dashboard", icon: "dashboard", roles: ["EMPLOYEE"] },
    ],
  },
  {
    title: "People",
    items: [
      { to: "/employees", label: "Employee Directory", icon: "users", roles: ["ADMIN", "HR"] },
      { to: "/employees/new", label: "Add Employee", icon: "plus", roles: ["ADMIN", "HR"] },
    ],
  },
  {
    title: "Organization",
    items: [
      { to: "/departments", label: "Departments", icon: "building", roles: ["ADMIN", "HR"] },
      { to: "/designations", label: "Designations", icon: "briefcase", roles: ["ADMIN", "HR"] },
    ],
  },
  {
    title: "Administration",
    items: [{ to: "/users", label: "User Management", icon: "shield", roles: ["ADMIN"] }],
  },
  {
    title: "Account",
    items: [{ to: "/profile", label: "My Profile", icon: "user", roles: ["ADMIN", "HR", "EMPLOYEE"] }],
  },
];

export function homePathFor(role: RoleName): string {
  if (role === "ADMIN") return "/dashboard/admin";
  if (role === "HR") return "/dashboard/hr";
  return "/dashboard/me";
}
