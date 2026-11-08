import { useState } from "react";
import { useAuth } from "../auth.jsx";

const DEMO = [
  ["Admin", "admin@society.com", "admin123"],
  ["Secretary", "secretary@society.com", "secretary123"],
  ["Treasurer", "treasurer@society.com", "treasurer123"],
  ["Security guard", "guard@society.com", "guard123"],
  ["Resident (flat 101)", "resident@society.com", "resident123"],
];

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "", phone: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={submit}>
        <h1>🏙️ Society Manager</h1>
        <p className="muted">{mode === "login" ? "Sign in to continue" : "Create a resident account"}</p>
        {error && <div className="alert error">{error}</div>}
        {mode === "register" && (
          <>
            <label className="field"><span>Full name</span><input value={form.name} onChange={set("name")} required /></label>
            <label className="field"><span>Phone</span><input value={form.phone} onChange={set("phone")} /></label>
          </>
        )}
        <label className="field"><span>Email</span><input type="email" value={form.email} onChange={set("email")} required /></label>
        <label className="field"><span>Password</span><input type="password" value={form.password} onChange={set("password")} required minLength={6} /></label>
        <button className="btn primary block" disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Sign in" : "Register"}</button>
        <button type="button" className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
          {mode === "login" ? "New resident? Register" : "Have an account? Sign in"}
        </button>
        {mode === "login" && (
          <div className="demo">
            <small>Demo accounts (click to fill):</small>
            {DEMO.map(([label, email, pw]) => (
              <button type="button" key={email} className="chip" onClick={() => setForm((f) => ({ ...f, email, password: pw }))}>
                {label}
              </button>
            ))}
          </div>
        )}
      </form>
    </div>
  );
}
