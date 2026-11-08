import { useEffect, useState } from "react";
import { api, fmtDateTime } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Badge, FormFields, Modal, statusTone } from "../components/Form.jsx";

const NEW_FIELDS = [
  { name: "title", label: "What is the problem?", type: "text", required: true },
  { name: "category", label: "Category", type: "select", options: ["plumbing", "electrical", "lift", "water", "noise", "cleanliness", "security", "parking", "other"] },
  { name: "priority", label: "Priority", type: "select", options: ["low", "medium", "high"] },
  { name: "description", label: "Details", type: "textarea" },
];
const MANAGE_FIELDS = [
  { name: "status", label: "Status", type: "select", options: ["open", "in_progress", "resolved", "closed"] },
  { name: "priority", label: "Priority", type: "select", options: ["low", "medium", "high"] },
  { name: "assigned_to", label: "Assigned to", type: "text" },
  { name: "resolution", label: "Resolution notes", type: "textarea" },
];

export default function Complaints() {
  const { user, can } = useAuth();
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("");
  const [error, setError] = useState("");
  const [form, setForm] = useState(null);
  const handler = can(["secretary", "committee", "staff"]);

  const load = () => api("/complaints" + (filter ? `?status=${filter}` : "")).then(setRows).catch((e) => setError(e.message));
  useEffect(() => { load(); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  async function save(e) {
    e.preventDefault();
    try {
      if (form.complaint) await api(`/complaints/${form.complaint.id}`, { method: "PUT", body: form.values });
      else await api("/complaints", { method: "POST", body: form.values });
      setForm(null);
      load();
    } catch (err) { setError(err.message); }
  }

  async function rate(c) {
    const r = prompt("Rate the resolution from 1 (poor) to 5 (excellent):");
    if (!r) return;
    await api(`/complaints/${c.id}/rate`, { method: "POST", body: { rating: Number(r) } }).catch((e) => setError(e.message));
    load();
  }

  return (
    <div>
      <div className="page-head">
        <h1>📣 Complaints & helpdesk</h1>
        <div className="row">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All statuses</option>
            {["open", "in_progress", "resolved", "closed"].map((s) => <option key={s}>{s}</option>)}
          </select>
          <button className="btn primary" onClick={() => setForm({ complaint: null, values: { priority: "medium" } })}>+ Raise complaint</button>
        </div>
      </div>
      {error && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      <div className="card table-wrap">
        <table>
          <thead><tr><th>#</th><th>Complaint</th><th>Flat</th><th>Priority</th><th>Status</th><th>Raised</th><th>Assigned</th><th></th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.id} className={c.sla_breached ? "row-red" : ""}>
                <td>{c.id}</td>
                <td><strong>{c.title}</strong><div className="muted small">{c.category} · {c.raised_by_name}</div>
                  {c.description && <div className="small">{c.description}</div>}
                  {c.resolution && <div className="small">✅ {c.resolution}</div>}
                  {c.rating && <div className="small">⭐ {c.rating}/5</div>}</td>
                <td>{c.flat_number || "—"}</td>
                <td><Badge tone={statusTone(c.priority)}>{c.priority}</Badge></td>
                <td><Badge tone={statusTone(c.status)}>{c.status}</Badge>
                  {c.sla_breached && <div className="small" style={{ color: "var(--red)" }}>SLA breached ({c.sla_hours}h)</div>}</td>
                <td>{fmtDateTime(c.created_at)}</td>
                <td>{c.assigned_to || "—"}</td>
                <td className="actions">
                  {handler && <button className="btn small" onClick={() => setForm({ complaint: c, values: { ...c } })}>Update</button>}
                  {c.raised_by === user.id && ["resolved", "closed"].includes(c.status) && !c.rating &&
                    <button className="btn small" onClick={() => rate(c)}>Rate</button>}
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={8} className="empty">No complaints.</td></tr>}
          </tbody>
        </table>
      </div>
      {form && (
        <Modal title={form.complaint ? `Update complaint #${form.complaint.id}` : "Raise a complaint"} onClose={() => setForm(null)}>
          <form onSubmit={save}>
            <FormFields fields={form.complaint ? MANAGE_FIELDS : NEW_FIELDS} values={form.values}
              setValues={(fn) => setForm((f) => ({ ...f, values: typeof fn === "function" ? fn(f.values) : fn }))} />
            <div className="modal-foot">
              <button type="button" className="btn" onClick={() => setForm(null)}>Cancel</button>
              <button className="btn primary">Save</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
