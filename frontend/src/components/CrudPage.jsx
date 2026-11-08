import { useEffect, useState } from "react";
import { api, fmtDate, fmtDateTime, money } from "../api.js";
import { useAuth } from "../auth.jsx";
import { Badge, FormFields, Modal, statusTone, useRefs } from "./Form.jsx";

export default function CrudPage({ cfg }) {
  const { can } = useAuth();
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null); // null | {} (new) | row
  const [values, setValues] = useState({});
  const [search, setSearch] = useState("");
  const refs = useRefs(cfg.fields);

  const writable = !cfg.readOnly && can(cfg.write);
  const formFields = cfg.fields.filter((f) => !f.readOnly);
  const columns = cfg.fields.filter((f) => f.list);

  const load = () => {
    setLoading(true);
    api(cfg.endpoint)
      .then((d) => { setRows(d); setError(""); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };
  useEffect(load, [cfg.endpoint]); // eslint-disable-line react-hooks/exhaustive-deps

  function openForm(row) {
    setEditing(row || {});
    setValues(row ? { ...row, password: "" } : Object.fromEntries(cfg.fields.filter((f) => f.type === "checkbox").map((f) => [f.name, true])));
  }

  async function save(e) {
    e.preventDefault();
    for (const f of formFields) {
      if (f.required && (values[f.name] === undefined || values[f.name] === "" || values[f.name] === null) && !(f.writeOnly && editing.id)) {
        return setError(`${f.label} is required`);
      }
    }
    try {
      if (editing.id) await api(`${cfg.endpoint}/${editing.id}`, { method: "PUT", body: values });
      else await api(cfg.endpoint, { method: "POST", body: values });
      setEditing(null);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(row) {
    if (!confirm("Delete this record?")) return;
    try {
      await api(`${cfg.endpoint}/${row.id}`, { method: "DELETE" });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  function cell(f, row) {
    const v = row[f.name];
    if (f.type === "ref") {
      const item = (refs[f.ref] || []).find((x) => x.id === v);
      return item ? (f.ref === "/flats" ? item.number : item.name || item.title) : v ?? "—";
    }
    if (f.type === "date") return fmtDate(v);
    if (f.name === "created_at" || f.name === "reported_on") return fmtDateTime(v);
    if (f.type === "checkbox") return v ? "Yes" : "No";
    if (f.money) return money(v);
    if (f.name === "status" || f.name === "type" && f.options) return v ? <Badge tone={statusTone(v)}>{v}</Badge> : "—";
    return v === null || v === undefined || v === "" ? "—" : String(v);
  }

  const shown = rows.filter((r) => !search || JSON.stringify(r).toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <div className="page-head">
        <h1>{cfg.icon} {cfg.label}</h1>
        <div className="row">
          <input className="search" placeholder="Search…" value={search} onChange={(e) => setSearch(e.target.value)} />
          {writable && <button className="btn primary" onClick={() => openForm(null)}>+ Add</button>}
        </div>
      </div>
      {error && <div className="alert error" onClick={() => setError("")}>{error}</div>}
      <div className="card table-wrap">
        <table>
          <thead>
            <tr>
              {columns.map((f) => <th key={f.name}>{f.label}</th>)}
              {writable && <th style={{ width: 120 }}></th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.id}>
                {columns.map((f) => <td key={f.name}>{cell(f, r)}</td>)}
                {writable && (
                  <td className="actions">
                    <button className="btn small" onClick={() => openForm(r)}>Edit</button>
                    <button className="btn small danger" onClick={() => remove(r)}>Delete</button>
                  </td>
                )}
              </tr>
            ))}
            {!loading && shown.length === 0 && (
              <tr><td colSpan={columns.length + 1} className="empty">Nothing here yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {editing && (
        <Modal title={(editing.id ? "Edit " : "Add ") + cfg.label.toLowerCase()} onClose={() => setEditing(null)} wide>
          <form onSubmit={save}>
            <FormFields fields={formFields} values={values} setValues={setValues} refs={refs} />
            <div className="modal-foot">
              <button type="button" className="btn" onClick={() => setEditing(null)}>Cancel</button>
              <button className="btn primary">Save</button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
