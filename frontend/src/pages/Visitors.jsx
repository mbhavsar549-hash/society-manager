import { useEffect, useState } from "react";
import { api, fmtDateTime } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Badge, FormFields, Modal, statusTone, useRefs } from "../components/Form.jsx";

export default function Visitors() {
  const { user, can } = useAuth();
  const isResident = user.role === "resident";
  const gate = can(["security", "secretary"]);
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [form, setForm] = useState(null);
  const [code, setCode] = useState("");

  const fields = [
    { name: "name", label: "Visitor name", type: "text", required: true },
    { name: "phone", label: "Phone", type: "text" },
    { name: "kind", label: "Type", type: "select", options: ["guest", "delivery", "cab", "service"] },
    ...(isResident ? [] : [{ name: "flat_id", label: "Visiting flat", type: "ref", ref: "/flats", required: true }]),
    { name: "purpose", label: "Purpose", type: "text" },
    { name: "vehicle_no", label: "Vehicle no.", type: "text" },
    ...(isResident ? [{ name: "expected_on", label: "Expected on", type: "date" }] : []),
  ];
  const refs = useRefs(fields);

  const load = () => api("/visitors").then(setRows).catch((e) => setError(e.message));
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []); // eslint-disable-line

  const act = (id, action) => api(`/visitors/${id}/${action}`, { method: "POST" }).then(load).catch((e) => setError(e.message));

  async function create(e) {
    e.preventDefault();
    try {
      const v = await api("/visitors", { method: "POST", body: form });
      setForm(null);
      setInfo(isResident ? `Pre-approved. Share this gate pass code with ${v.name}: ${v.pass_code}` : `Sent to flat ${v.flat_number} for approval.`);
      load();
    } catch (err) { setError(err.message); }
  }

  async function verify(e) {
    e.preventDefault();
    try {
      const v = await api("/visitors/verify", { method: "POST", body: { pass_code: code } });
      if (confirm(`Valid pass: ${v.name} → flat ${v.flat_number}.\nCheck in now?`)) await act(v.id, "checkin");
      setCode("");
    } catch (err) { setError(err.message); }
  }

  return (
    <div>
      <div className="page-head">
        <h1>🚪 Visitors</h1>
        <button className="btn primary" onClick={() => setForm({ kind: "guest" })}>{isResident ? "+ Pre-approve visitor" : "+ Log visitor"}</button>
      </div>
      {error && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      {info && <div className="alert ok" onClick={() => setInfo("")}>{info}</div>}

      {gate && (
        <form className="card row" onSubmit={verify} style={{ marginBottom: 12 }}>
          <strong>Gate pass check:</strong>
          <input placeholder="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={6} />
          <button className="btn primary">Verify</button>
        </form>
      )}

      <div className="card table-wrap">
        <table>
          <thead><tr><th>Visitor</th><th>Flat</th><th>Type</th><th>Status</th><th>Pass code</th><th>In</th><th>Out</th><th></th></tr></thead>
          <tbody>
            {rows.map((v) => (
              <tr key={v.id}>
                <td><strong>{v.name}</strong><div className="muted small">{v.phone} {v.vehicle_no}</div></td>
                <td>{v.flat_number}</td><td>{v.kind}</td>
                <td><Badge tone={statusTone(v.status)}>{v.status}</Badge></td>
                <td>{v.pass_code || "—"}</td><td>{fmtDateTime(v.in_time)}</td><td>{fmtDateTime(v.out_time)}</td>
                <td className="actions">
                  {v.status === "pending" && can(["resident", "secretary", "committee"]) && <>
                    <button className="btn small primary" onClick={() => act(v.id, "approve")}>Approve</button>
                    <button className="btn small danger" onClick={() => act(v.id, "reject")}>Reject</button></>}
                  {v.status === "approved" && gate && <button className="btn small primary" onClick={() => act(v.id, "checkin")}>Check in</button>}
                  {v.status === "in" && gate && <button className="btn small" onClick={() => act(v.id, "checkout")}>Check out</button>}
                </td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={8} className="empty">No visitors.</td></tr>}
          </tbody>
        </table>
      </div>

      {form && (
        <Modal title={isResident ? "Pre-approve a visitor" : "Log a visitor at the gate"} onClose={() => setForm(null)}>
          <form onSubmit={create}>
            <FormFields fields={fields} refs={refs} values={form} setValues={setForm} />
            <div className="modal-foot"><button type="button" className="btn" onClick={() => setForm(null)}>Cancel</button><button className="btn primary">Save</button></div>
          </form>
        </Modal>
      )}
    </div>
  );
}
