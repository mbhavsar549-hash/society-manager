import { useEffect, useState } from "react";
import { api, fmtDate, fmtDateTime, money } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Badge, FormFields, Modal, statusTone, useRefs } from "../components/Form.jsx";

const TASK_FIELDS = [
  { name: "title", label: "Task", type: "text", required: true },
  { name: "category", label: "Category", type: "select", options: ["water_tank", "lift", "generator", "fire", "pest", "stp", "cctv", "intercom", "garbage", "cleaning", "other"] },
  { name: "frequency_days", label: "Repeat every (days)", type: "number", required: true },
  { name: "reminder_days", label: "Remind before (days)", type: "number" },
  { name: "last_done", label: "Last done", type: "date" },
  { name: "next_due", label: "Next due (blank = auto)", type: "date" },
  { name: "vendor_id", label: "Vendor", type: "ref", ref: "/vendors" },
  { name: "assigned_to", label: "Assigned to", type: "text" },
  { name: "checklist", label: "Checklist (one per line)", type: "textarea" },
  { name: "notes", label: "Notes", type: "textarea" },
];
const DONE_FIELDS = [
  { name: "done_on", label: "Done on", type: "date" },
  { name: "done_by", label: "Done by", type: "text" },
  { name: "cost", label: "Cost (₹)", type: "number" },
  { name: "remarks", label: "Remarks", type: "textarea" },
];
const label = (s) => ({ overdue: "Overdue", due_soon: "Due soon", ok: "On track", unscheduled: "Unscheduled" }[s] || s);

export default function Maintenance() {
  const { can } = useAuth();
  const [tab, setTab] = useState("tasks");
  const [tasks, setTasks] = useState([]);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(null); // {mode:"task"|"done", task, values}
  const refs = useRefs(TASK_FIELDS);
  const manage = can(["secretary", "committee", "treasurer"]);
  const execute = can(["secretary", "committee", "staff", "vendor"]);

  const load = () => {
    api("/maintenance/tasks").then(setTasks).catch((e) => setError(e.message));
    api("/maintenance/logs").then(setLogs).catch(() => {});
  };
  useEffect(load, []);

  async function save(e) {
    e.preventDefault();
    try {
      if (form.mode === "done") {
        await api(`/maintenance/tasks/${form.task.id}/complete`, { method: "POST", body: form.values });
      } else if (form.task?.id) {
        await api(`/maintenance/tasks/${form.task.id}`, { method: "PUT", body: form.values });
      } else {
        await api("/maintenance/tasks", { method: "POST", body: form.values });
      }
      setForm(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(t) {
    if (!confirm(`Delete "${t.title}" and its history?`)) return;
    await api(`/maintenance/tasks/${t.id}`, { method: "DELETE" }).catch((e) => setError(e.message));
    load();
  }

  async function runChecks() {
    const r = await api("/maintenance/run-checks", { method: "POST" }).catch((e) => setError(e.message));
    if (r) alert(`Checks done: ${r.notifications_created} new alerts, ${r.escalated} escalated.`);
  }

  const counts = tasks.reduce((a, t) => ({ ...a, [t.status]: (a[t.status] || 0) + 1 }), {});

  return (
    <div>
      <div className="page-head">
        <h1>🛠️ Maintenance schedule</h1>
        <div className="row">
          {can(["secretary"]) && <button className="btn" onClick={runChecks}>Run reminder checks</button>}
          {manage && <button className="btn primary" onClick={() => setForm({ mode: "task", task: null, values: { frequency_days: 30, reminder_days: 7 } })}>+ Add task</button>}
        </div>
      </div>
      {error && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      <div className="tabs">
        <button className={tab === "tasks" ? "active" : ""} onClick={() => setTab("tasks")}>
          Tasks {counts.overdue ? <Badge tone="red">{counts.overdue} overdue</Badge> : null}
        </button>
        <button className={tab === "logs" ? "active" : ""} onClick={() => setTab("logs")}>History</button>
      </div>

      {tab === "tasks" ? (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>Task</th><th>Status</th><th>Last done</th><th>Next due</th><th>Every</th><th>Vendor</th><th></th></tr></thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className={t.status === "overdue" ? "row-red" : ""}>
                  <td><strong>{t.title}</strong>{t.escalated && <Badge tone="red">escalated</Badge>}
                    {t.checklist && <div className="muted small pre">{t.checklist}</div>}</td>
                  <td>
                    <Badge tone={statusTone(t.status)}>{label(t.status)}</Badge>
                    {t.days_left !== null && <div className="muted small">{t.days_left < 0 ? `${-t.days_left} days late` : `${t.days_left} days left`}</div>}
                  </td>
                  <td className="nowrap">{fmtDate(t.last_done)}</td>
                  <td className="nowrap">{fmtDate(t.next_due)}</td>
                  <td>{t.frequency_days}d</td>
                  <td>{t.vendor_name || t.assigned_to || "—"}</td>
                  <td className="actions">
                    {execute && <button className="btn small primary" onClick={() => setForm({ mode: "done", task: t, values: { done_on: new Date().toISOString().slice(0, 10) } })}>Mark done</button>}
                    {manage && <button className="btn small" onClick={() => setForm({ mode: "task", task: t, values: { ...t } })}>Edit</button>}
                    {manage && <button className="btn small danger" onClick={() => remove(t)}>✕</button>}
                  </td>
                </tr>
              ))}
              {tasks.length === 0 && <tr><td colSpan={7} className="empty">No maintenance tasks yet.</td></tr>}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card table-wrap">
          <table>
            <thead><tr><th>Task</th><th>Done on</th><th>Done by</th><th>Cost</th><th>Remarks</th><th>Logged</th></tr></thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id}><td>{l.task_title}</td><td>{fmtDate(l.done_on)}</td><td>{l.done_by}</td><td>{money(l.cost)}</td><td>{l.remarks || "—"}</td><td>{fmtDateTime(l.created_at)}</td></tr>
              ))}
              {logs.length === 0 && <tr><td colSpan={6} className="empty">No history yet.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {form && (
        <Modal title={form.mode === "done" ? `Mark done: ${form.task.title}` : form.task ? "Edit task" : "Add task"} onClose={() => setForm(null)} wide>
          <form onSubmit={save}>
            <FormFields fields={form.mode === "done" ? DONE_FIELDS : TASK_FIELDS} refs={refs} values={form.values}
              setValues={(fn) => setForm((f) => ({ ...f, values: typeof fn === "function" ? fn(f.values) : fn }))} />
            {form.mode === "done" && <p className="muted small">The next due date is calculated automatically, and any cost is booked as an expense.</p>}
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
