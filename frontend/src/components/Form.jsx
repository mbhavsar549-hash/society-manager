import { useEffect, useState } from "react";
import { api } from "../api.js";
import { refLabel } from "../resources.js";

export function Modal({ title, onClose, children, wide }) {
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={"modal" + (wide ? " wide" : "")}>
        <div className="modal-head">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Loads the option lists for every `ref` field: returns { "/flats": [...], ... } */
export function useRefs(fields) {
  const [refs, setRefs] = useState({});
  const key = fields.filter((f) => f.type === "ref").map((f) => f.ref).join("|");
  useEffect(() => {
    const endpoints = [...new Set(fields.filter((f) => f.type === "ref").map((f) => f.ref))];
    Promise.all(endpoints.map((e) => api(e).then((d) => [e, d]).catch(() => [e, []]))).then((pairs) =>
      setRefs(Object.fromEntries(pairs))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return refs;
}

export function FieldInput({ f, value, onChange, refs = {} }) {
  const v = value ?? "";
  switch (f.type) {
    case "textarea":
      return <textarea rows={3} value={v} onChange={(e) => onChange(e.target.value)} />;
    case "checkbox":
      return <input type="checkbox" checked={!!value} onChange={(e) => onChange(e.target.checked)} />;
    case "select":
      return (
        <select value={v} onChange={(e) => onChange(e.target.value)}>
          <option value="">— select —</option>
          {f.options.map((o) => (
            <option key={o} value={o}>{o}</option>
          ))}
        </select>
      );
    case "ref":
      return (
        <select value={v} onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}>
          <option value="">— select —</option>
          {(refs[f.ref] || []).map((item) => (
            <option key={item.id} value={item.id}>{refLabel(f.ref, item)}</option>
          ))}
        </select>
      );
    case "number":
      return <input type="number" step="any" value={v} onChange={(e) => onChange(e.target.value)} />;
    case "date":
      return <input type="date" value={String(v).slice(0, 10)} onChange={(e) => onChange(e.target.value)} />;
    case "time":
      return <input type="time" value={v} onChange={(e) => onChange(e.target.value)} />;
    case "password":
      return <input type="password" autoComplete="new-password" value={v} onChange={(e) => onChange(e.target.value)} />;
    default:
      return <input type="text" value={v} onChange={(e) => onChange(e.target.value)} />;
  }
}

export function FormFields({ fields, values, setValues, refs }) {
  return (
    <div className="form-grid">
      {fields.map((f) => (
        <label key={f.name} className={"field" + (f.type === "textarea" ? " full" : "") + (f.type === "checkbox" ? " check" : "")}>
          <span>{f.label}{f.required && " *"}</span>
          <FieldInput f={f} value={values[f.name]} refs={refs} onChange={(val) => setValues((s) => ({ ...s, [f.name]: val }))} />
        </label>
      ))}
    </div>
  );
}

export function Badge({ tone = "gray", children }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function statusTone(s) {
  return (
    { overdue: "red", due_soon: "amber", ok: "green", paid: "green", pending: "amber", open: "red", in_progress: "amber",
      resolved: "green", closed: "gray", approved: "green", rejected: "red", in: "blue", out: "gray", cancelled: "gray",
      high: "red", medium: "amber", low: "gray", emergency: "red", unscheduled: "gray" }[s] || "gray"
  );
}
