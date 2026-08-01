import { useState, useEffect } from 'react';
import Login from './components/Login';
import KYCModal from './components/KYCModal';
import WalletDashboard from './components/WalletDashboard';
import AIContractBuilder from './components/AIContractBuilder';
import PaymentSuccess from './components/PaymentSuccess';
import LawyerDashboard from './components/LawyerDashboard';
import ActiveContracts from './components/ActiveContracts';
import AdminDashboard from './components/AdminDashboard';
import DevPortal from './components/DevPortal';
import api from './services/api';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isKycModalOpen, setIsKycModalOpen] = useState(false);
  
  // Tab State: 'wallet', 'create_contract', 'active_deals', 'payment_success', 'lawyer_chamber', 'admin_center', 'dev_portal'
  const [activeTab, setActiveTab] = useState('wallet');

  // Helper function to determine default tab based on role
  const routeUserByRole = (userData, overrideTab = null) => {
    if (overrideTab) {
      setActiveTab(overrideTab);
    } else if (userData.is_lawyer) {
      setActiveTab('lawyer_chamber');
    } else if (userData.is_superuser || userData.is_staff) {
      setActiveTab('admin_center');
    } else {
      setActiveTab('wallet');
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    let urlTab = null;
    if (params.get('reference') || params.get('trxref')) {
      urlTab = 'payment_success';
    }

    const token = localStorage.getItem('access_token');
    if (token) {
      api.get('profile/')
        .then((res) => {
          setUser(res.data);
          if (!res.data.is_kyc_verified) setIsKycModalOpen(true);
          // Auto-route on page refresh based on role!
          routeUserByRole(res.data, urlTab);
        })
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    if (!userData.is_kyc_verified) {
      setIsKycModalOpen(true);
    }
    // Auto-route immediately upon login!
    routeUserByRole(userData);
  };

  const handleLogout = () => {
    localStorage.clear();
    setUser(null);
    setActiveTab('wallet'); // Reset default
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-slate-500 font-medium">Loading Covalent...</div>;
  }

  if (!user) {
    return <Login onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-100 pb-6 mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Covalent Escrow</h1>
            <p className="text-sm text-slate-500">Welcome back, {user.first_name} {user.last_name}</p>
          </div>
          <button
            onClick={handleLogout}
            className="px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg font-medium transition"
          >
            Sign Out
          </button>
        </div>

        {/* 3-Column Stat Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60">
            <span className="text-xs font-semibold text-slate-500 uppercase">Trust Tier</span>
            <div className="text-lg font-bold text-slate-900 mt-1">{user.trust_tier}</div>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60">
            <span className="text-xs font-semibold text-slate-500 uppercase">Trust Score</span>
            <div className="text-lg font-bold text-slate-900 mt-1">{user.trust_score} / 100</div>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/60">
            <span className="text-xs font-semibold text-slate-500 uppercase">KYC Status</span>
            <div className="mt-1">
              {user.is_kyc_verified ? (
                <span className="px-2.5 py-1 bg-emerald-100 text-emerald-800 text-xs font-bold rounded-full">Verified</span>
              ) : (
                <button 
                  onClick={() => setIsKycModalOpen(true)}
                  className="text-xs font-bold text-amber-600 underline hover:text-amber-700"
                >
                  Pending (Click to Verify)
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex flex-wrap gap-2 border-b border-slate-200 mb-6">
          {/* Admin / Command Center Tab */}
          {(user.is_superuser || user.is_staff) && (
            <button
              onClick={() => setActiveTab('admin_center')}
              className={`pb-3 px-4 text-sm font-bold border-b-2 transition flex items-center gap-1 ${
                activeTab === 'admin_center' ? 'border-purple-600 text-purple-900' : 'border-transparent text-purple-400 hover:text-purple-700'
              }`}
            >
              <span>🛡️</span> Command Center
            </button>
          )}

          {/* Lawyer ONLY: Governance Chamber Tab */}
          {user.is_lawyer && (
            <button
              onClick={() => setActiveTab('lawyer_chamber')}
              className={`pb-3 px-4 text-sm font-bold border-b-2 transition flex items-center gap-1 ${
                activeTab === 'lawyer_chamber' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-700'
              }`}
            >
              <span className="text-amber-500">⚖️</span> Governance Chamber
            </button>
          )}

          {/* Non-Lawyer ONLY: Consumer & Developer Tabs */}
          {!user.is_lawyer && (
            <>
              <button
                onClick={() => setActiveTab('wallet')}
                className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
                  activeTab === 'wallet' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-700'
                }`}
              >
                💳 Wallet & Bank Setup
              </button>
              
              <button
                onClick={() => setActiveTab('create_contract')}
                className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
                  activeTab === 'create_contract' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-700'
                }`}
              >
                🤖 AI Contract Builder
              </button>

              <button
                onClick={() => setActiveTab('active_deals')}
                className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
                  activeTab === 'active_deals' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-700'
                }`}
              >
                📦 Active Pipeline
              </button>

              <button
                onClick={() => setActiveTab('dev_portal')}
                className={`pb-3 px-4 text-sm font-bold border-b-2 transition ${
                  activeTab === 'dev_portal' ? 'border-slate-900 text-slate-900' : 'border-transparent text-slate-400 hover:text-slate-700'
                }`}
              >
                🛠️ Developer API
              </button>
            </>
          )}
        </div>

        {/* Tab Content Rendering Block */}
        <div className="mt-6">
          {activeTab === 'wallet' && <WalletDashboard onBankLinked={() => api.get('profile/').then(res => setUser(res.data))} />}
          {activeTab === 'create_contract' && <AIContractBuilder onContractFunded={() => setActiveTab('active_deals')} />}
          {activeTab === 'active_deals' && <ActiveContracts currentUser={user} onStatusChanged={() => api.get('profile/').then(res => setUser(res.data))} />}
          {activeTab === 'payment_success' && <PaymentSuccess onReturnHome={() => setActiveTab('active_deals')} />}
          {activeTab === 'lawyer_chamber' && <LawyerDashboard />}
          {activeTab === 'admin_center' && <AdminDashboard />}
          {activeTab === 'dev_portal' && <DevPortal />}
        </div>
      </div>

      <KYCModal
        isOpen={isKycModalOpen}
        onClose={() => setIsKycModalOpen(false)}
        onVerified={(updatedUser) => setUser(updatedUser)}
      />
    </div>
  );
}