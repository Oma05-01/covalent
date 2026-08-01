import { useState, useEffect } from 'react';
import api from '../services/api';

// Reusable primitive from the new design
function SectionLabel({ children }) {
  return <p className="text-[10px] font-semibold tracking-widest text-slate-400 uppercase mb-3">{children}</p>;
}

export default function WalletDashboard({ onBankLinked }) {
  const [walletData, setWalletData] = useState(null);
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);

  // Form State
  const [selectedBank, setSelectedBank] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [resolvedName, setResolvedName] = useState('');
  const [resolving, setResolving] = useState(false);
  const [linking, setLinking] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchWalletAndBanks();
  }, []);

  const fetchWalletAndBanks = async () => {
    try {
      const [walletRes, banksRes] = await Promise.all([
        api.get('wallet/'),
        api.get('banks/')
      ]);
      setWalletData(walletRes.data);
      setBanks(banksRes.data);
    } catch (err) {
      console.error("Failed to load wallet data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAccountChange = async (val, bankCode) => {
    const cleaned = val.replace(/\D/g, '');
    setAccountNumber(cleaned);
    setResolvedName('');
    setError('');

    if (cleaned.length === 10 && bankCode) {
      setResolving(true);
      try {
        const res = await api.post('wallet/resolve/', {
          account_number: cleaned,
          bank_code: bankCode
        });
        setResolvedName(res.data.account_name);
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not verify account number.');
      } finally {
        setResolving(false);
      }
    }
  };

  const handleLinkBank = async (e) => {
    e.preventDefault();
    if (!resolvedName) return;
    setLinking(true);
    setError('');

    const bankObj = banks.find(b => b.code === selectedBank);
    try {
      await api.post('wallet/link/', {
        bank_code: selectedBank,
        bank_name: bankObj?.name || '',
        account_number: accountNumber,
        account_name: resolvedName
      });
      await fetchWalletAndBanks();
      if (onBankLinked) onBankLinked();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to link account.');
    } finally {
      setLinking(false);
    }
  };

  if (loading || !walletData) {
    return <div className="p-12 text-center text-slate-500 font-medium">Loading ledger data...</div>;
  }

  const { wallet, bank_info } = walletData;

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-6 py-6">
      
      {/* Ledger Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        
        {/* Dark Hero Card for Available Balance */}
        <div className="bg-slate-900 rounded-2xl p-5 relative overflow-hidden shadow-lg shadow-slate-900/20">
          <div className="absolute inset-0 opacity-5" style={{
            backgroundImage: "repeating-linear-gradient(0deg,transparent,transparent 24px,rgba(255,255,255,.3) 24px,rgba(255,255,255,.3) 25px),repeating-linear-gradient(90deg,transparent,transparent 24px,rgba(255,255,255,.3) 24px,rgba(255,255,255,.3) 25px)"
          }} />
          <div className="relative">
            <div className="flex items-center justify-between mb-2">
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">Available Balance</p>
              <div className="w-6 h-6 rounded-md bg-slate-800 flex items-center justify-center">
                <svg className="w-3.5 h-3.5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <p className="font-mono text-white text-3xl font-bold tracking-tight">
              ₦{Number(wallet.available_balance).toLocaleString()}
            </p>
            <p className="text-slate-400 text-xs mt-1.5 font-medium">Ready for instant payout</p>
          </div>
        </div>

        {/* Locked Escrow Card */}
        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">Locked in Escrow</p>
            <div className="w-6 h-6 rounded-md bg-amber-50 flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </div>
          </div>
          <p className="font-mono text-slate-900 text-3xl font-bold tracking-tight">
            ₦{Number(wallet.locked_escrow_balance).toLocaleString()}
          </p>
          <p className="text-amber-600 text-xs mt-1.5 font-medium">Awaiting buyer inspection</p>
        </div>

        {/* Penalty Card */}
        <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold">Penalty Balance</p>
            <div className={`w-6 h-6 rounded-md flex items-center justify-center ${Number(wallet.penalty_balance) < 0 ? 'bg-red-50' : 'bg-slate-50'}`}>
              <svg className={`w-3.5 h-3.5 ${Number(wallet.penalty_balance) < 0 ? 'text-red-600' : 'text-slate-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
          </div>
          <p className={`font-mono text-3xl font-bold tracking-tight ${Number(wallet.penalty_balance) < 0 ? 'text-red-600' : 'text-slate-900'}`}>
            ₦{Number(wallet.penalty_balance).toLocaleString()}
          </p>
          <p className="text-slate-500 text-xs mt-1.5 font-medium">Dispute deductions (Must be ₦0 to sell)</p>
        </div>
      </div>

      {/* Bank Account Linking Section */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm max-w-2xl">
        <SectionLabel>Settlement Bank Account</SectionLabel>
        <p className="text-sm text-slate-500 mb-6">
          Where Paystack automatically wires your funds when an escrow deal completes.
        </p>

        {bank_info.is_linked ? (
          <div className="flex items-center justify-between p-5 bg-emerald-50/50 border border-emerald-200 rounded-xl">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center text-emerald-600">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
                </svg>
              </div>
              <div>
                <div className="text-base font-bold text-slate-900">{bank_info.account_name}</div>
                <div className="text-xs text-slate-500 font-mono mt-0.5">{bank_info.account_number} • {bank_info.bank_name}</div>
              </div>
            </div>
            <span className="px-3 py-1 bg-emerald-100 text-emerald-700 border border-emerald-200 text-[10px] font-bold tracking-wider rounded-full uppercase">
              Verified
            </span>
          </div>
        ) : (
          <form onSubmit={handleLinkBank} className="space-y-4">
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-50 text-red-700 border border-red-200 rounded-xl text-xs font-medium animate-in fade-in">
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                {error}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">Select Bank</label>
                <select
                  required
                  value={selectedBank}
                  onChange={(e) => {
                    setSelectedBank(e.target.value);
                    if (accountNumber.length === 10) handleAccountChange(accountNumber, e.target.value);
                  }}
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-slate-900 focus:border-slate-900 outline-none text-slate-900 bg-white transition-all appearance-none"
                >
                  <option value="">-- Choose a Nigerian Bank --</option>
                  {banks.map((b, index) => (
                    <option key={`${b.code}-${index}`} value={b.code}>{b.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">10-Digit Account Number</label>
                <input
                  type="text"
                  maxLength="10"
                  required
                  value={accountNumber}
                  onChange={(e) => handleAccountChange(e.target.value, selectedBank)}
                  placeholder="0123456789"
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 focus:ring-2 focus:ring-slate-900 focus:border-slate-900 outline-none font-mono text-slate-900 transition-all"
                />
              </div>
            </div>

            {resolving && (
              <div className="text-xs text-amber-600 font-medium animate-pulse flex items-center gap-2">
                <span className="w-3 h-3 rounded-full border-2 border-amber-600 border-t-transparent animate-spin"></span>
                Verifying NUBAN with Paystack...
              </div>
            )}

            {resolvedName && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl animate-in slide-in-from-top-2">
                <span className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold block mb-0.5">Resolved Account Name</span>
                <span className="text-sm font-bold text-slate-900">{resolvedName}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!resolvedName || linking}
              className="w-full bg-slate-900 hover:bg-slate-800 text-white text-sm font-semibold py-3 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed mt-2"
            >
              {linking ? 'Generating Subaccount...' : 'Confirm & Link Bank Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}