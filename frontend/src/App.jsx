import { HashRouter, Routes, Route, Navigate } from "react-router-dom";

import Nav from "./navbar/nav";
import Grade from "./grades/grade";
import Notifications from "./notifications/notifications";

import NavAdmin from "./navbar/navAdmin";
import DeadlineAndReminders from "./admin/deadlineAndReminders";
import ManageAccounts from "./admin/manageAccounts";
import GradeComponents from "./admin/gradeComponents";
import ViewGrade from "./admin/viewGrade";

import Login from "./login/login";
import { getToken, getUser, homePathForRole } from "./auth/auth";

// Front-end gate only: sends logged-out people to /login and keeps each role
// on its own pages. The backend still has to enforce access.
function RequireAuth({ role, children }) {
  const token = getToken();
  const user = getUser();

  if (!token || !user) {
    return <Navigate to="/login" replace />;
  }

  const isAdmin = user.role === "Admin" || user.role === "SuperAdmin";
  const allowed = role === "admin" ? isAdmin : user.role === "Teacher";

  if (!allowed) {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }

  return children;
}

function App() {
  return (
    <HashRouter>
      <Routes>
        {/* The bare root goes to the login page */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        <Route path="/login" element={<Login />} />

        {/* Redirect bare /admin to the first admin page */}
        <Route path="/admin" element={<Navigate to="/admin/manage-accounts" replace />} />

        {/* ===================== TEACHER ===================== */}

        {/* Grade is now the only grading page (formerly GradeV2, v1 retired) */}
        <Route
          path="/teacher"
          element={
            <RequireAuth role="teacher">
              <Nav />
              <Grade />
            </RequireAuth>
          }
        />

        {/* Notification ni Rene */}
        <Route
          path="/teacher/notifications"
          element={
            <RequireAuth role="teacher">
              <Notifications />
            </RequireAuth>
          }
        />

        {/* ===================== ADMIN ===================== */}

        {/* ADMIN Manage Accounts */}
        <Route
          path="/admin/manage-accounts"
          element={
            <RequireAuth role="admin">
              <NavAdmin />
              <ManageAccounts />
            </RequireAuth>
          }
        />

        {/* ADMIN Deadline And Reminders */}
        <Route
          path="/admin/deadlines"
          element={
            <RequireAuth role="admin">
              <NavAdmin />
              <DeadlineAndReminders />
            </RequireAuth>
          }
        />

        {/* ADMIN Grade Components */}
        <Route
          path="/admin/grade-components"
          element={
            <RequireAuth role="admin">
              <NavAdmin />
              <GradeComponents />
            </RequireAuth>
          }
        />

        {/* ADMIN View Grade */}
        <Route
          path="/admin/view-grades"
          element={
            <RequireAuth role="admin">
              <NavAdmin />
              <ViewGrade />
            </RequireAuth>
          }
        />

        {/* Anything else goes back to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </HashRouter>
  );
}

export default App;