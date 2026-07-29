import { useState, useEffect } from 'react';
import api from '../services/api';

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

  if (loading) return <div className="p-12 text-center text-slate-500 font-mono">Loading platform telemetry...</div>;
  if (error) return <div className="p-6 bg-red-50 text-red-600 border border-red-200 rounded-xl font-bold">{error}</div>;

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      
      {/* Header Banner */}
      <div className="bg-slate-900 text-white p-6 rounded-2xl flex justify-between items-center shadow-lg border border-slate-800">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest bg-purple-500/20 text-purple-400 px-3 py-1 rounded-full border border-purple-500/30">
            Phase 7: Founder Control
          </span>
          <h2 className="text-2xl font-black mt-2">Platform Command Center</h2>
          <p className="text-xs text-slate-400 mt-0.5">Real-time revenue telemetry, escrow vault monitoring, and trust governance.</p>
        </div>
        <div className="text-right font-mono">
          <span className="text-xs text-slate-400 block">Total Active Users</span>
          <span className="text-2xl font-bold text-white">{metrics?.governance?.total_users || 0}</span>
        </div>
      </div>

      {/* Financial Telemetry Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Covalent 5% Revenue Card */}
        <div className="bg-gradient-to-br from-purple-900 to-slate-900 text-white p-5 rounded-2xl shadow-sm border border-purple-800/50 relative overflow-hidden">
          <div className="text-xs font-bold text-purple-300 uppercase tracking-wider">Covalent Net Revenue (5%)</div>
          <div className="text-2xl font-black font-mono mt-2 text-emerald-400">
            ₦{Number(metrics?.financials?.platform_revenue || 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-slate-300 mt-2">
            Captured from ₦{Number(metrics?.financials?.total_gmv || 0).toLocaleString()} Total GMV
          </div>
        </div>

        {/* Locked Vault Card */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80">
          <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Locked Escrow Vault</div>
          <div className="text-2xl font-black font-mono mt-2 text-slate-900">
            ₦{Number(metrics?.financials?.locked_vault || 0).toLocaleString()}
          </div>
          <div className="text-[11px] text-slate-500 mt-2">
            Currently held in active pipeline deals
          </div>
        </div>

        {/* Governance Health Card */}
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-200/80 flex justify-between flex-col">
          <div>
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider">Governance Health</div>
            <div className="flex justify-between items-baseline mt-2">
              <span className="text-2xl font-black font-mono text-slate-900">{metrics?.governance?.avg_trust_score} <span className="text-xs font-normal text-slate-400">Avg Trust</span></span>
              <span className="text-sm font-bold text-amber-600 bg-amber-50 px-2.5 py-0.5 rounded-full">{metrics?.governance?.active_disputes} Open Disputes</span>
            </div>
          </div>
          <div className="text-[11px] text-slate-500 mt-2 border-t border-slate-100 pt-2 flex justify-between">
            <span>Verified Lawyers: <strong className="text-slate-700">{metrics?.governance?.verified_lawyers}</strong></span>
            <span>System Status: <strong className="text-emerald-600">Optimal</strong></span>
          </div>
        </div>

      </div>

      {/* God-Mode User Management Table */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm overflow-hidden">
        <h3 className="text-base font-bold text-slate-900 mb-4">Live User Registry & Trust Override</h3>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                <th className="pb-3">User Account</th>
                <th className="pb-3">Trust Score</th>
                <th className="pb-3">Roles & Status</th>
                <th className="pb-3">Available Balance</th>
                <th className="pb-3 text-right">Admin Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs font-mono">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/80 transition">
                  <td className="py-3.5">
                    <div className="font-bold text-slate-900">{u.name || 'Unnamed'}</div>
                    <div className="text-[11px] text-slate-400">{u.email}</div>
                  </td>
                  <td className="py-3.5">
                    <span className={`px-2 py-0.5 rounded font-bold ${u.trust_score < 50 ? 'bg-red-100 text-red-700' : 'bg-slate-100 text-slate-700'}`}>
                      {u.trust_score} / 100
                    </span>
                  </td>
                  <td className="py-3.5 space-x-1">
                    {u.is_kyc_verified && <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full font-sans text-[10px] font-bold">KYC</span>}
                    {u.is_lawyer && <span className="px-2 py-0.5 bg-purple-100 text-purple-800 rounded-full font-sans text-[10px] font-bold">Lawyer</span>}
                    {!u.is_kyc_verified && !u.is_lawyer && <span className="text-slate-400 font-sans text-xs">Standard User</span>}
                  </td>
                  <td className="py-3.5 font-bold text-slate-700">
                    ₦{Number(u.wallet_balance).toLocaleString()}
                  </td>
                  <td className="py-3.5 text-right space-x-1 font-sans">
                    <button
                      onClick={() => handleUserAction(u.id, 'toggle_lawyer')}
                      disabled={!!actionLoading}
                      className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-bold text-[11px] transition"
                      title="Toggle verified lawyer status for arbitration"
                    >
                      {u.is_lawyer ? 'Revoke Lawyer' : '+ Make Lawyer'}
                    </button>
                    <button
                      onClick={() => handleUserAction(u.id, 'boost_trust')}
                      disabled={!!actionLoading}
                      className="px-2.5 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded font-bold text-[11px] transition"
                    >
                      +10 Trust
                    </button>
                    <button
                      onClick={() => handleUserAction(u.id, 'penalize_trust')}
                      disabled={!!actionLoading}
                      className="px-2.5 py-1 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded font-bold text-[11px] transition"
                    >
                      -15 Trust
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

      </div>

    </div>
  );
}