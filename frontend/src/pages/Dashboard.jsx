import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtDate, money } from "../api.js";
import { Badge, statusTone } from "../components/Form.jsx";

function Stat({ label, value, tone, to }) {
  const body = (
    <div className={"stat " + (tone || "")}>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
  return to ? <Link to={to} className="plain">{body}</Link> : body;
}

function TaskList({ title, tasks, empty }) {
  return (
    <div className="card">
      <h3>{title}</h3>
      {tasks.length === 0 && <p className="muted">{empty}</p>}
      {tasks.map((t) => (
        <div key={t.id} className="list-row">
          <div>
            <strong>{t.title}</strong>
            <div className="muted small">Due {fmtDate(t.next_due)}{t.vendor_name ? ` · ${t.vendor_name}` : ""}</div>
          </div>
          <Badge tone={statusTone(t.status)}>
            {t.days_left < 0 ? `${-t.days_left} days overdue` : `in ${t.days_left} days`}
          </Badge>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const [d, setD] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => { api("/dashboard").then(setD).catch((e) => setError(e.message)); }, []);

  if (error) return <div className="alert error">{error}</div>;
  if (!d) return <p className="muted">Loading…</p>;
  const c = d.counts;

  return (
    <div>
      <div className="page-head"><h1>🏠 Dashboard</h1></div>
      {c.overdue_tasks > 0 && (
        <div className="alert error">
          ⚠️ {c.overdue_tasks} maintenance task{c.overdue_tasks > 1 ? "s are" : " is"} overdue — e.g.{" "}
          <strong>{d.overdue_tasks[0].title}</strong> ({-d.overdue_tasks[0].days_left} days late).{" "}
          <Link to="/maintenance">View all</Link>
        </div>
      )}
      <div className="stats">
        <Stat label="Overdue maintenance" value={c.overdue_tasks} tone={c.overdue_tasks ? "red" : "green"} to="/maintenance" />
        <Stat label="Due soon" value={c.due_soon_tasks} tone={c.due_soon_tasks ? "amber" : ""} to="/maintenance" />
        <Stat label="Open complaints" value={c.open_complaints} to="/complaints" />
        <Stat label={d.role === "resident" ? "My pending dues" : "Pending dues"} value={money(c.pending_dues)} tone={c.pending_dues ? "amber" : "green"} to="/billing" />
        <Stat label="Visitors inside" value={c.visitors_inside} to="/visitors" />
        {c.pending_visitor_approvals > 0 && <Stat label="Visitor approvals pending" value={c.pending_visitor_approvals} tone="amber" to="/visitors" />}
        <Stat label="Flats" value={c.flats} />
        <Stat label="Upcoming bookings" value={c.upcoming_bookings} to="/bookings" />
      </div>
      <div className="grid-2">
        <TaskList title="🔴 Overdue (visible to all residents)" tasks={d.overdue_tasks} empty="Nothing is overdue. 🎉" />
        <TaskList title="🟡 Coming up" tasks={d.upcoming_tasks} empty="Nothing due in the next few days." />
      </div>
      <div className="card">
        <h3>📌 Latest notices</h3>
        {d.recent_notices.length === 0 && <p className="muted">No notices.</p>}
        {d.recent_notices.map((n) => (
          <div key={n.id} className="list-row">
            <div><strong>{n.title}</strong><div className="muted small">{n.body}</div></div>
            <Badge tone={statusTone(n.type)}>{n.type}</Badge>
          </div>
        ))}
      </div>
    </div>
  );
}
