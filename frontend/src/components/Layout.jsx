import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { COMMITTEE, useAuth } from "../auth.jsx";
import { RESOURCES } from "../resources.js";

const ALL = null;
const CORE = [
  { to: "/", label: "Dashboard", icon: "🏠", roles: ALL, group: "Main" },
  { to: "/maintenance", label: "Maintenance", icon: "🛠️", roles: ALL, group: "Main" },
  { to: "/complaints", label: "Complaints", icon: "📣", roles: ALL, group: "Main" },
  { to: "/billing", label: "Billing", icon: "💳", roles: ["resident", ...COMMITTEE], group: "Main" },
  { to: "/visitors", label: "Visitors", icon: "🚪", roles: ["resident", "security", ...COMMITTEE], group: "Main" },
  { to: "/bookings", label: "Amenity booking", icon: "🏊", roles: ["resident", ...COMMITTEE], group: "Community" },
  { to: "/polls", label: "Polls", icon: "🗳️", roles: ALL, group: "Community" },
];

export default function Layout() {
  const { user, logout, can } = useAuth();
  const nav = useNavigate();
  const loc = useLocation();
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [sosMsg, setSosMsg] = useState("");

  useEffect(() => {
    api("/notifications").then((d) => setUnread(d.unread)).catch(() => {});
    setOpen(false);
  }, [loc.pathname]);

  const items = [
    ...CORE,
    ...RESOURCES.filter((r) => (r.read ? can(r.read) : true)).map((r) => ({
      to: `/r/${r.key}`, label: r.label, icon: r.icon, group: r.group,
    })),
  ].filter((i) => !i.roles || can(i.roles));
  const groups = [...new Set(items.map((i) => i.group))];

  async function sos() {
    const message = prompt("🚨 Send an SOS alert to the whole society?\nOptional: describe the emergency (e.g. fire on 5th floor).");
    if (message === null) return;
    try {
      await api("/sos", { method: "POST", body: { message } });
      setSosMsg("SOS sent. Security and committee have been alerted.");
      setTimeout(() => setSosMsg(""), 6000);
    } catch (e) {
      alert(e.message);
    }
  }

  return (
    <div className="shell">
      <aside className={"sidebar" + (open ? " open" : "")}>
        <div className="brand">🏙️ Society Manager</div>
        {groups.map((g) => (
          <div key={g}>
            <div className="nav-group">{g}</div>
            {items.filter((i) => i.group === g).map((i) => (
              <NavLink key={i.to} to={i.to} end={i.to === "/"} className="nav-item">
                <span>{i.icon}</span> {i.label}
              </NavLink>
            ))}
          </div>
        ))}
      </aside>
      <div className="main">
        <header className="topbar">
          <button className="icon-btn menu" onClick={() => setOpen((o) => !o)}>☰</button>
          <div className="grow" />
          <button className="btn sos" onClick={sos}>🚨 SOS</button>
          <button className="icon-btn bell" onClick={() => nav("/notifications")} title="Notifications">
            🔔{unread > 0 && <b className="dot">{unread > 99 ? "99+" : unread}</b>}
          </button>
          <div className="who">
            <strong>{user.name}</strong>
            <small>{user.role}</small>
          </div>
          <button className="btn small" onClick={() => { logout(); nav("/login"); }}>Logout</button>
        </header>
        {sosMsg && <div className="alert ok">{sosMsg}</div>}
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
