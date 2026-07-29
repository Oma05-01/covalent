import { useState, useEffect } from 'react';
import api from '../services/api';

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

  // Auto-resolve when 10 digits are typed and a bank is selected
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
    return <div className="p-6 text-center text-slate-400">Loading wallet ledger...</div>;
  }

  const { wallet, bank_info } = walletData;

  return (
    <div className="space-y-6">
      {/* Ledger Balance Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 bg-slate-900 text-white rounded-2xl shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">Available Balance</span>
          <div className="text-2xl font-bold mt-1">₦{Number(wallet.available_balance).toLocaleString()}</div>
          <p className="text-xs text-slate-400 mt-2">Ready for instant payout</p>
        </div>

        <div className="p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Locked in Escrow</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">₦{Number(wallet.locked_escrow_balance).toLocaleString()}</div>
          <p className="text-xs text-amber-600 font-medium mt-2">Awaiting buyer inspection</p>
        </div>

        <div className="p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">Penalty Balance</span>
          <div className={`text-2xl font-bold mt-1 ${Number(wallet.penalty_balance) < 0 ? 'text-red-600' : 'text-slate-900'}`}>
            ₦{Number(wallet.penalty_balance).toLocaleString()}
          </div>
          <p className="text-xs text-slate-400 mt-2">Dispute deductions (Must be ₦0 to sell)</p>
        </div>
      </div>

      {/* Bank Account Linking Section */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm">
        <h3 className="text-lg font-bold text-slate-900 mb-1">Settlement Bank Account</h3>
        <p className="text-sm text-slate-500 mb-6">
          Where Paystack automatically wires your funds when an escrow deal completes.
        </p>

        {bank_info.is_linked ? (
          <div className="flex items-center justify-between p-4 bg-emerald-50/50 border border-emerald-200 rounded-xl">
            <div>
              <div className="text-xs font-bold text-emerald-800 uppercase tracking-wider mb-0.5">Verified Payout Account</div>
              <div className="text-base font-bold text-slate-900">{bank_info.account_name}</div>
              <div className="text-sm text-slate-600 font-mono mt-0.5">{bank_info.account_number} • {bank_info.bank_name}</div>
            </div>
            <span className="px-3 py-1 bg-emerald-600 text-white text-xs font-bold rounded-full">Linked</span>
          </div>
        ) : (
          <form onSubmit={handleLinkBank} className="max-w-md space-y-4">
            {error && <div className="p-3 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs">{error}</div>}

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Select Bank</label>
              <select
                required
                value={selectedBank}
                onChange={(e) => {
                  setSelectedBank(e.target.value);
                  if (accountNumber.length === 10) handleAccountChange(accountNumber, e.target.value);
                }}
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none text-slate-900 bg-white"
              >
                <option value="">-- Choose a Nigerian Bank --</option>
                {banks.map((b, index) => (
                  <option key={`${b.code}-${index}`} value={b.code}>{b.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">10-Digit Account Number</label>
              <input
                type="text"
                maxLength="10"
                required
                value={accountNumber}
                onChange={(e) => handleAccountChange(e.target.value, selectedBank)}
                placeholder="0123456789"
                className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none font-mono text-slate-900"
              />
            </div>

            {resolving && <div className="text-xs text-amber-600 font-medium animate-pulse">Verifying NUBAN with Paystack...</div>}

            {resolvedName && (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <span className="text-xs text-slate-500 block">Resolved Account Name:</span>
                <span className="text-sm font-bold text-slate-900">{resolvedName}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={!resolvedName || linking}
              className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-lg transition disabled:opacity-40"
            >
              {linking ? 'Generating Subaccount...' : 'Confirm & Link Bank Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}