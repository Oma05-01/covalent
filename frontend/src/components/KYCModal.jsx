import { useState } from 'react';
import api from '../services/api';

export default function KYCModal({ isOpen, onClose, onVerified }) {
  const [nin, setNin] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!/^\d{11}$/.test(nin)) {
      setError('NIN must be exactly 11 digits.');
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('kyc/verify/', { nin });
      onVerified(response.data.user);
      onClose();
    } catch (err) {
      const apiErrors = err.response?.data;
      setError(apiErrors?.nin?.[0] || apiErrors?.detail || 'Verification failed. Please check your NIN.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-50 px-4">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-100 animate-in fade-in zoom-in duration-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold text-slate-900">Identity Verification Required</h3>
          <span className="px-2.5 py-0.5 bg-amber-100 text-amber-800 text-xs font-semibold rounded-full">
            Mandatory
          </span>
        </div>

        <p className="text-sm text-slate-600 mb-6">
          To protect buyers and enforce accountability, Covalent requires all vendors to verify their National Identity Number (NIN) before creating escrow contracts.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 text-xs rounded-lg">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              11-Digit NIN
            </label>
            <input
              type="text"
              maxLength="11"
              required
              value={nin}
              onChange={(e) => setNin(e.target.value.replace(/\D/g, ''))}
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none text-slate-900 font-mono tracking-widest text-center text-lg"
              placeholder="12345678901"
            />
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="w-1/3 py-2.5 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition"
            >
              Later
            </button>
            <button
              type="submit"
              disabled={loading || nin.length !== 11}
              className="w-2/3 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium py-2.5 transition disabled:opacity-50"
            >
              {loading ? 'Verifying...' : 'Verify Identity'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}