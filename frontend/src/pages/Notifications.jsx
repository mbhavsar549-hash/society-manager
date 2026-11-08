import { useEffect, useState } from "react";
import { api, fmtDateTime } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function Notifications() {
  const { can } = useAuth();
  const [data, setData] = useState({ items: [], unread: 0 });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const load = () => api("/notifications").then(setData).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const markAll = () => api("/notifications/read-all", { method: "POST" }).then(load);

  async function broadcast(e) {
    e.preventDefault();
    try {
      await api("/notifications/broadcast", { method: "POST", body: { message: msg, level: "warning" } });
      setMsg("");
      load();
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <div className="page-head">
        <h1>🔔 Notifications</h1>
        {data.unread > 0 && <button className="btn" onClick={markAll}>Mark all read ({data.unread})</button>}
      </div>
      {error && <div className="alert error">{error}</div>}
      {can(["secretary", "committee"]) && (
        <form className="card row" onSubmit={broadcast} style={{ marginBottom: 12 }}>
          <input className="grow" placeholder="Broadcast an alert to all residents (e.g. water shutdown 2–4 PM)" value={msg} onChange={(e) => setMsg(e.target.value)} required />
          <button className="btn primary">Send alert</button>
        </form>
      )}
      <div className="card">
        {data.items.map((n) => (
          <div key={n.id} className={"list-row notif " + n.level + (n.read ? " read" : "")}>
            <div>{!n.read && <b className="unread-dot" />}{n.message}</div>
            <small className="muted">{fmtDateTime(n.created_at)}</small>
          </div>
        ))}
        {data.items.length === 0 && <p className="muted">You're all caught up.</p>}
      </div>
    </div>
  );
}
