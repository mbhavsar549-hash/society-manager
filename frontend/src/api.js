const BASE = import.meta.env.VITE_API_URL || "/api";

export async function api(path, { method = "GET", body } = {}) {
  const token = localStorage.getItem("token");
  const res = await fetch(BASE + path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401 && !path.startsWith("/auth/login")) {
    localStorage.removeItem("token");
    if (!location.pathname.startsWith("/login")) location.href = "/login";
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const d = data?.detail;
    const msg = typeof d === "string" ? d : Array.isArray(d) ? d.map((x) => x.msg).join(", ") : res.statusText;
    throw new Error(msg || "Request failed");
  }
  return data;
}

export const money = (n) => "₹" + Number(n || 0).toLocaleString("en-IN", { maximumFractionDigits: 0 });
export const fmtDate = (d) => (d ? String(d).slice(0, 10) : "—");
export const fmtDateTime = (d) => (d ? String(d).replace("T", " ").slice(0, 16) : "—");
