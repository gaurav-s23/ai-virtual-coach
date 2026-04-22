import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const adminToken = localStorage.getItem("admin_token");

  // Check if admin token is valid and not expired
  const validateAdminToken = (token) => {
    if (!token) return false;
    
    try {
      // Basic JWT validation for admin token
      const parts = token.split('.');
      if (parts.length !== 3) return false;
      
      const payload = JSON.parse(atob(parts[1]));
      const currentTime = Date.now() / 1000;
      
      // Check if token has admin role and is not expired
      return payload.isAdmin === true && payload.exp > currentTime;
    } catch (error) {
      console.error('Token validation failed:', error);
      return false;
    }
  };

  const [isAdmin, setIsAdmin] = useState(false);
  const [tokenValid, setTokenValid] = useState(false);

  useEffect(() => {
    const isValid = validateAdminToken(adminToken);
    setTokenValid(isValid);
    setIsAdmin(isValid);
    
    if (!isValid) {
      localStorage.removeItem("admin_token");
      navigate("/admin/login");
    }
  }, [adminToken, navigate]);

  const handleAuthError = (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      localStorage.removeItem("admin_token");
      navigate("/admin/login");
      return true;
    }
    return false;
  };

  useEffect(() => {
    if (!tokenValid || !isAdmin) {
      return;
    }
    const headers = { Authorization: `Bearer ${adminToken}` };
    Promise.all([
      api.get("/api/admin/stats", { headers }),
      api.get(`/api/admin/users?limit=${pageSize}&offset=${page * pageSize}`, { headers }),
    ])
      .then(([statsRes, usersRes]) => {
        setStats(statsRes.data);
        setUsers(usersRes.data || []);
      })
      .catch((error) => {
        if (!handleAuthError(error)) {
          setStats(null);
          setUsers([]);
        }
      })
      .finally(() => setLoading(false));
  }, [tokenValid, isAdmin, adminToken, navigate, page, pageSize]);

  const logout = () => {
    localStorage.removeItem("admin_token");
    navigate("/admin/login");
  };

  const viewDetails = async (userId) => {
    if (!adminToken) return;
    const headers = { Authorization: `Bearer ${adminToken}` };
    try {
      const res = await api.get(`/api/admin/users/${userId}`, { headers });
      setSelected(userId);
      setDetail(res.data);
    } catch (error) {
      handleAuthError(error);
    }
  };

  if (!adminToken) {
    return null;
  }

  if (loading) {
    return <div className="min-h-screen bg-[#020617] text-white p-8">Loading admin dashboard...</div>;
  }

  return (
    <div className="min-h-screen bg-[#020617] text-slate-200 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-black tracking-tight text-white">Admin Dashboard</h1>
          <button onClick={logout} className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 text-white font-bold">
            Logout
          </button>
        </div>
        <div className="mt-4 flex gap-3">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="px-3 py-1 rounded-lg bg-white/10 disabled:opacity-50"
          >
            Prev
          </button>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={users.length < pageSize}
            className="px-3 py-1 rounded-lg bg-white/10 disabled:opacity-50"
          >
            Next
          </button>
        </div>

        <div className="grid md:grid-cols-4 gap-4 mb-8">
          <Card title="Total Users" value={stats?.total_users ?? 0} />
          <Card title="Total Interviews" value={stats?.total_interviews ?? 0} />
          <Card title="Total Mocks" value={stats?.total_mocks ?? 0} />
          <Card title="Total English Sessions" value={stats?.total_english ?? 0} />
        </div>

        <div className="bg-white/[0.03] border border-white/10 rounded-2xl overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-black/30 text-cyan-400">
              <tr>
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Email</th>
                <th className="text-left px-4 py-3">Readiness%</th>
                <th className="text-left px-4 py-3">Interviews</th>
                <th className="text-left px-4 py-3">Mocks</th>
                <th className="text-left px-4 py-3">English Sessions</th>
                <th className="text-left px-4 py-3">Joined Date</th>
                <th className="text-left px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-t border-white/5">
                  <td className="px-4 py-3">{u.id}</td>
                  <td className="px-4 py-3">{u.name}</td>
                  <td className="px-4 py-3">{u.email}</td>
                  <td className="px-4 py-3">{u.readiness_score}</td>
                  <td className="px-4 py-3">{u.total_interviews}</td>
                  <td className="px-4 py-3">{u.total_mocks}</td>
                  <td className="px-4 py-3">{u.total_english_sessions}</td>
                  <td className="px-4 py-3">{String(u.created_at).slice(0, 10)}</td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => viewDetails(u.id)}
                      className="px-3 py-1 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold"
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selected && detail ? (
          <div className="mt-8 bg-black/30 border border-white/10 rounded-2xl p-6">
            <h2 className="text-2xl font-bold mb-4 text-cyan-400">User Detail: {detail.user?.name}</h2>
            <p className="mb-4 text-sm">Email: {detail.user?.email} | Readiness: {detail.user?.readiness_score}</p>
            <Section title="Interviews" items={detail.interviews} keyA="role" keyB="score" />
            <Section title="Mocks" items={detail.mocks} keyA="category" keyB="score" />
            <Section title="English Sessions" items={detail.english} keyA="topic" keyB="rating" />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Card({ title, value }) {
  return (
    <div className="bg-white/[0.03] border border-white/10 rounded-2xl p-5">
      <p className="text-cyan-400 text-xs uppercase tracking-widest mb-2">{title}</p>
      <p className="text-3xl font-black text-white">{value}</p>
    </div>
  );
}

function Section({ title, items, keyA, keyB }) {
  return (
    <div className="mb-4">
      <h3 className="font-bold text-white mb-2">{title}</h3>
      <div className="space-y-2">
        {(items || []).map((it) => (
          <div key={it.id} className="bg-white/[0.02] border border-white/5 rounded-xl px-3 py-2 text-sm">
            #{it.id} | {it[keyA]} | {keyB}: {it[keyB]} | {String(it.created_at).slice(0, 19)}
          </div>
        ))}
      </div>
    </div>
  );
}
