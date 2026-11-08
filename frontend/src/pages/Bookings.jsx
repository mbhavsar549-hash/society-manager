import { useEffect, useState } from "react";
import { api, fmtDate, money } from "../api.js";
import { Badge, FormFields, Modal, statusTone, useRefs } from "../components/Form.jsx";
import { useAuth } from "../auth.jsx";

const FIELDS = [
  { name: "amenity_id", label: "Facility", type: "ref", ref: "/amenities", required: true },
  { name: "date", label: "Date", type: "date", required: true },
  { name: "start_time", label: "From", type: "time", required: true },
  { name: "end_time", label: "To", type: "time", required: true },
];

export default function Bookings() {
  const { user, can } = useAuth();
  const [rows, setRows] = useState([]);
  const [form, setForm] = useState(null);
  const [error, setError] = useState("");
  const refs = useRefs(FIELDS);

  const load = () => api("/bookings").then(setRows).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function save(e) {
    e.preventDefault();
    try {
      await api("/bookings", { method: "POST", body: form });
      setForm(null);
      setError("");
      load();
    } catch (err) { setError(err.message); }
  }

  const cancel = (b) => confirm("Cancel this booking?") && api(`/bookings/${b.id}/cancel`, { method: "POST" }).then(load).catch((e) => setError(e.message));
  const amenity = (refs["/amenities"] || []).find((a) => a.id === form?.amenity_id);

  return (
    <div>
      <div className="page-head">
        <h1>🏊 Amenity booking</h1>
        <button className="btn primary" onClick={() => setForm({})}>+ Book a facility</button>
      </div>
      {error && !form && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      <div className="card table-wrap">
        <table>
          <thead><tr><th>Facility</th><th>Date</th><th>Time</th><th>Flat</th><th>Fee</th><th>Status</th><th></th></tr></thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.id}>
                <td>{b.amenity_name}</td><td>{fmtDate(b.date)}</td><td>{b.start_time} – {b.end_time}</td>
                <td>{b.flat_number || "—"}</td><td>{money(b.fee)}</td>
                <td><Badge tone={statusTone(b.status)}>{b.status}</Badge></td>
                <td className="actions">{b.status === "approved" && (b.booked_by === user.id || can(["secretary", "treasurer", "committee"])) &&
                  <button className="btn small danger" onClick={() => cancel(b)}>Cancel</button>}</td>
              </tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={7} className="empty">No bookings.</td></tr>}
          </tbody>
        </table>
      </div>
      {form && (
        <Modal title="Book a facility" onClose={() => { setForm(null); setError(""); }}>
          <form onSubmit={save}>
            {error && <div className="alert error">{error}</div>}
            <FormFields fields={FIELDS} refs={refs} values={form} setValues={setForm} />
            {amenity && <p className="muted small">Open {amenity.open_time}–{amenity.close_time} · Fee {money(amenity.fee)}</p>}
            <div className="modal-foot"><button type="button" className="btn" onClick={() => setForm(null)}>Cancel</button><button className="btn primary">Book</button></div>
          </form>
        </Modal>
      )}
    </div>
  );
}
