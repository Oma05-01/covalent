import { useState, useEffect } from 'react';
import api from '../services/api';

// Reusable primitive
function SectionLabel({ children }) {
  return <p className="text-[10px] font-semibold tracking-widest text-slate-400 uppercase mb-3">{children}</p>;
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const [analyticsRes, usersRes] = await Promise.all([
        api.get('admin/analytics/'),
        api.get('admin/users/')
      ]);
      setMetrics(analyticsRes.data);
      setUsers(usersRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load admin telemetry. Superuser rights required.");
    } finally {
      setLoading(false);
    }
  };

  const handleUserAction = async (userId, actionType) => {
    setActionLoading(`${userId}-${actionType}`);
    try {
      await api.patch(`admin/users/${userId}/action/`, { action: actionType });
      await fetchAdminData();
    } catch (err) {
      alert("Action failed: " + (err.response?.data?.detail || "Unknown error"));
    } finally {
      setActionLoading('');
    }
  };

  const fmtNGN = (n) => "₦" + Number(n).toLocaleString("en-NG");

  if (loading) return <div className="p-12 text-center text-slate-500 font-medium">Loading platform telemetry...</div>;
  if (error) return <div className="p-6 bg-red-50 text-red-600 border border-red-200 rounded-xl font-bold max-w-2xl mx-auto mt-8">{error}</div>;

  // Map live backend data to the design's stat cards
  const stats = [
    { label: "Total GMV", value: fmtNGN(metrics?.financials?.total_gmv || 0), sub: "Cumulative volume", icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6", color: "text-slate-900" },
    { label: "Escrow Vault", value: fmtNGN(metrics?.financials?.locked_vault || 0), sub: "Currently locked", icon: "M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z", color: "text-emerald-700" },
    { label: "Covalent Revenue (5%)", value: fmtNGN(metrics?.financials?.platform_revenue || 0), sub: "Platform earnings", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z", color: "text-amber-700" },
    { label: "Open Disputes", value: metrics?.governance?.active_disputes || 0, sub: "Pending arbitration", icon: "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z", color: "text-red-600" },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-slate-900 font-semibold text-base">Command Center</h2>
            <span className="text-[9px] font-bold uppercase tracking-widest bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full border border-purple-200">
              Phase 7: Founder Control
            </span>
          </div>
          <p className="text-slate-500 text-xs mt-0.5">Real-time revenue telemetry & trust governance</p>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-slate-500 font-medium">Live</span>
        </div>
      </div>

      {/* Financial KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {stats.map(s => (
          <div key={s.label} className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold leading-tight">{s.label}</p>
              <div className="w-7 h-7 rounded-lg bg-slate-50 flex items-center justify-center">
                <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={s.icon} />
                </svg>
              </div>
            </div>
            <p className={`font-mono text-xl md:text-2xl font-bold leading-tight ${s.color}`}>{s.value}</p>
            <p className="text-[10px] text-slate-400 mt-1">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Governance Stats Bar */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-4 mb-6 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-6">
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mb-1">Total Users</p>
            <p className="font-mono text-lg font-bold text-slate-900">{metrics?.governance?.total_users || 0}</p>
          </div>
          <div className="w-px h-8 bg-slate-100"></div>
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mb-1">Avg Trust</p>
            <p className="font-mono text-lg font-bold text-slate-900">{metrics?.governance?.avg_trust_score || 0}<span className="text-xs text-slate-400 font-normal">/100</span></p>
          </div>
          <div className="w-px h-8 bg-slate-100"></div>
          <div>
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mb-1">Verified Lawyers</p>
            <p className="font-mono text-lg font-bold text-purple-700">{metrics?.governance?.verified_lawyers || 0}</p>
          </div>
        </div>
      </div>

      {/* User Management Table */}
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm">
        <div className="px-5 py-4 flex items-center justify-between border-b border-slate-100">
          <SectionLabel>Live User Registry & Trust Override</SectionLabel>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold border-b border-slate-100">
                <th className="text-left px-5 py-3">User</th>
                <th className="text-left px-4 py-3">Role</th>
                <th className="text-left px-4 py-3">KYC</th>
                <th className="text-left px-4 py-3">Trust</th>
                <th className="text-left px-4 py-3 hidden md:table-cell">Balance</th>
                <th className="text-right px-5 py-3">Admin Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => {
                const isLoading = actionLoading.startsWith(u.id.toString());
                return (
                  <tr key={u.id} className={`border-b border-slate-50 hover:bg-slate-50/80 transition-colors ${i === users.length - 1 ? "border-none" : ""}`}>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-slate-100 flex items-center justify-center text-[10px] font-bold text-slate-600 flex-shrink-0 uppercase">
                          {u.name ? u.name.slice(0, 2) : u.email.slice(0,2)}
                        </div>
                        <div>
                          <p className="font-medium text-slate-800 text-xs whitespace-nowrap">{u.name || 'Unnamed'}</p>
                          <p className="text-[10px] text-slate-400 font-mono">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-md ${
                        u.is_lawyer ? "bg-purple-50 text-purple-700" : "bg-blue-50 text-blue-700"
                      }`}>
                        {u.is_lawyer ? 'Arbitrator' : 'Standard'}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      {u.is_kyc_verified
                        ? <span className="text-emerald-600 text-[10px] font-semibold px-2 py-0.5 bg-emerald-50 rounded border border-emerald-100">✓ Verified</span>
                        : <span className="text-amber-600 text-[10px] font-semibold">Pending</span>}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`font-mono text-xs font-bold ${
                        u.trust_score >= 80 ? "text-emerald-700" : u.trust_score >= 50 ? "text-amber-700" : "text-red-600"
                      }`}>
                        {u.trust_score}
                      </span>
                    </td>
                    <td className="px-4 py-3.5 hidden md:table-cell">
                      <span className="font-mono text-xs font-semibold text-slate-700">
                        ₦{Number(u.wallet_balance || 0).toLocaleString()}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => handleUserAction(u.id, 'toggle_lawyer')}
                          disabled={isLoading}
                          className="text-[10px] font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1.5 rounded transition-colors disabled:opacity-50"
                        >
                          {u.is_lawyer ? 'Revoke Lawyer' : '+ Make Lawyer'}
                        </button>
                        <button
                          onClick={() => handleUserAction(u.id, 'boost_trust')}
                          disabled={isLoading}
                          className="text-[10px] font-semibold bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 px-2 py-1.5 rounded transition-colors disabled:opacity-50"
                        >
                          +10 Trust
                        </button>
                        <button
                          onClick={() => handleUserAction(u.id, 'penalize_trust')}
                          disabled={isLoading}
                          className="text-[10px] font-semibold bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 px-2 py-1.5 rounded transition-colors disabled:opacity-50"
                        >
                          -15 Trust
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}