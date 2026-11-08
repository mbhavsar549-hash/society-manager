import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import CrudPage from "./components/CrudPage.jsx";
import { RESOURCES } from "./resources.js";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Maintenance from "./pages/Maintenance.jsx";
import Complaints from "./pages/Complaints.jsx";
import Billing from "./pages/Billing.jsx";
import Visitors from "./pages/Visitors.jsx";
import Bookings from "./pages/Bookings.jsx";
import Polls from "./pages/Polls.jsx";
import Notifications from "./pages/Notifications.jsx";

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center-screen">Loading…</div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={user ? <Layout /> : <Navigate to="/login" replace />}>
        <Route index element={<Dashboard />} />
        <Route path="maintenance" element={<Maintenance />} />
        <Route path="complaints" element={<Complaints />} />
        <Route path="billing" element={<Billing />} />
        <Route path="visitors" element={<Visitors />} />
        <Route path="bookings" element={<Bookings />} />
        <Route path="polls" element={<Polls />} />
        <Route path="notifications" element={<Notifications />} />
        {RESOURCES.map((r) => (
          <Route key={r.key} path={`r/${r.key}`} element={<CrudPage key={r.key} cfg={r} />} />
        ))}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
