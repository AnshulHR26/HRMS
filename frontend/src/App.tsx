import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { homePathFor } from "./components/navigation";
import { FullPageSpinner } from "./components/Spinner";
import AdminDashboard from "./pages/AdminDashboard";
import DepartmentManagement from "./pages/DepartmentManagement";
import DesignationManagement from "./pages/DesignationManagement";
import EmployeeDashboard from "./pages/EmployeeDashboard";
import EmployeeDetails from "./pages/EmployeeDetails";
import EmployeeDirectory from "./pages/EmployeeDirectory";
import EmployeeForm from "./pages/EmployeeForm";
import HRDashboard from "./pages/HRDashboard";
import LoginPage from "./pages/LoginPage";
import MyProfile from "./pages/MyProfile";
import { ForbiddenPage, NotFoundPage } from "./pages/StatusPages";
import UserManagement from "./pages/UserManagement";

function HomeRedirect() {
  const { user, initializing } = useAuth();
  if (initializing) return <FullPageSpinner />;
  return <Navigate to={user ? homePathFor(user.role) : "/login"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<HomeRedirect />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<HomeRedirect />} />
          <Route path="/profile" element={<MyProfile />} />
          <Route path="/forbidden" element={<ForbiddenPage />} />

          <Route element={<ProtectedRoute roles={["EMPLOYEE", "HR", "ADMIN"]} />}>
            <Route path="/dashboard/me" element={<EmployeeDashboard />} />
          </Route>

          <Route element={<ProtectedRoute roles={["ADMIN"]} />}>
            <Route path="/dashboard/admin" element={<AdminDashboard />} />
            <Route path="/users" element={<UserManagement />} />
          </Route>

          <Route element={<ProtectedRoute roles={["ADMIN", "HR"]} />}>
            <Route path="/dashboard/hr" element={<HRDashboard />} />
            <Route path="/employees" element={<EmployeeDirectory />} />
            <Route path="/employees/new" element={<EmployeeForm mode="create" />} />
            <Route path="/employees/:employeeId/edit" element={<EmployeeForm mode="edit" />} />
            <Route path="/departments" element={<DepartmentManagement />} />
            <Route path="/designations" element={<DesignationManagement />} />
          </Route>

          {/* Employees may open their own record; the API enforces ownership. */}
          <Route path="/employees/:employeeId" element={<EmployeeDetails />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
