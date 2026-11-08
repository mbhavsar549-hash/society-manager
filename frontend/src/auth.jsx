import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api.js";

const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export const COMMITTEE = ["admin", "secretary", "treasurer", "committee"];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem("token"));

  useEffect(() => {
    if (!localStorage.getItem("token")) return;
    api("/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setLoading(false));
  }, []);

  async function login(email, password) {
    const data = await api("/auth/login", { method: "POST", body: { email, password } });
    localStorage.setItem("token", data.access_token);
    setUser(data.user);
  }

  async function register(form) {
    const data = await api("/auth/register", { method: "POST", body: form });
    localStorage.setItem("token", data.access_token);
    setUser(data.user);
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
  }

  const can = (roles) => !roles || user?.role === "admin" || roles.includes(user?.role);

  return <AuthCtx.Provider value={{ user, loading, login, register, logout, can }}>{children}</AuthCtx.Provider>;
}
