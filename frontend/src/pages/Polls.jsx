import { useEffect, useState } from "react";
import { api, fmtDate } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Badge, FormFields, Modal } from "../components/Form.jsx";

const FIELDS = [
  { name: "question", label: "Question", type: "text", required: true },
  { name: "options", label: "Options (one per line)", type: "textarea", required: true },
  { name: "closes_on", label: "Closes on", type: "date" },
];

export default function Polls() {
  const { can } = useAuth();
  const [polls, setPolls] = useState([]);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const load = () => api("/polls").then(setPolls).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  const vote = (p, option) => api(`/polls/${p.id}/vote`, { method: "POST", body: { option } }).then(load).catch((e) => setError(e.message));
  const remove = (p) => confirm("Delete this poll?") && api(`/polls/${p.id}`, { method: "DELETE" }).then(load);

  async function create(e) {
    e.preventDefault();
    try { await api("/polls", { method: "POST", body: form }); setForm(null); load(); } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <div className="page-head">
        <h1>🗳️ Polls & voting</h1>
        {can(["secretary", "committee"]) && <button className="btn primary" onClick={() => setForm({})}>+ New poll</button>}
      </div>
      {error && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      <div className="grid-2">
        {polls.map((p) => (
          <div className="card" key={p.id}>
            <div className="list-row">
              <h3>{p.question}</h3>
              {p.closed ? <Badge tone="gray">closed</Badge> : p.closes_on ? <Badge tone="blue">until {fmtDate(p.closes_on)}</Badge> : null}
            </div>
            {p.options_list.map((o) => {
              const n = p.counts[o] || 0;
              const pct = p.total_votes ? Math.round((100 * n) / p.total_votes) : 0;
              return (
                <button key={o} disabled={p.closed} className={"poll-opt" + (p.my_vote === o ? " mine" : "")} onClick={() => vote(p, o)}>
                  <span className="bar" style={{ width: pct + "%" }} />
                  <span className="txt">{o}{p.my_vote === o ? " ✓" : ""}</span>
                  <span className="num">{n} · {pct}%</span>
                </button>
              );
            })}
            <div className="muted small">{p.total_votes} vote{p.total_votes === 1 ? "" : "s"}</div>
            {can(["secretary"]) && <button className="btn small danger" onClick={() => remove(p)}>Delete</button>}
          </div>
        ))}
        {polls.length === 0 && <p className="muted">No polls yet.</p>}
      </div>
      {form && (
        <Modal title="New poll" onClose={() => setForm(null)}>
          <form onSubmit={create}>
            <FormFields fields={FIELDS} values={form} setValues={setForm} />
            <div className="modal-foot"><button type="button" className="btn" onClick={() => setForm(null)}>Cancel</button><button className="btn primary">Create</button></div>
          </form>
        </Modal>
      )}
    </div>
  );
}
