import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await api.post("/api/admin/login", { email, password });
      localStorage.setItem("admin_token", res.data.admin_token);
      navigate("/admin");
    } catch (_err) {
      setError("Invalid admin credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#020617] text-white flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white/[0.03] border border-white/10 rounded-3xl p-8">
        <h1 className="text-3xl font-black tracking-tight mb-2">Admin Login</h1>
        <p className="text-cyan-400 text-xs uppercase tracking-widest mb-6">AI Virtual Coach</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Admin Email"
            className="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 outline-none focus:border-cyan-500"
          />
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Admin Password"
            className="w-full px-4 py-3 rounded-xl bg-black/30 border border-white/10 outline-none focus:border-cyan-500"
          />
          {error ? <p className="text-red-400 text-sm">{error}</p> : null}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 py-3 rounded-xl font-bold"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}
