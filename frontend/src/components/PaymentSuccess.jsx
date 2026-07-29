import { useState, useEffect } from 'react';
import api from '../services/api';

export default function PaymentSuccess({ onReturnHome }) {
  const [contract, setContract] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reference, setReference] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ref = params.get('reference') || params.get('trxref');
    
    if (ref) {
      setReference(ref);
      verifyAndLoadContract(ref);
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      setLoading(false);
    }
  }, []);

  const verifyAndLoadContract = async (refString) => {
    try {
      // Calls our smart verification endpoint to auto-fund localhost deals
      const res = await api.post('contracts/verify/', {
        reference: refString
      });
      setContract(res.data);
    } catch (err) {
      console.error("Failed to verify payment details:", err);
      setError("Could not verify contract details with server.");
    } finally {
      setLoading(false);
    }
  };

  const clearUrlParamsAndReturn = () => {
    window.history.replaceState({}, document.title, window.location.pathname);
    onReturnHome();
  };

  if (loading) {
    return <div className="p-12 text-center text-slate-500 font-medium">Verifying payment and locking escrow funds...</div>;
  }

  return (
    <div className="max-w-md mx-auto bg-white border border-slate-200/80 rounded-2xl p-8 shadow-sm text-center animate-in zoom-in-95 duration-200">
      <div className="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl font-black">
        ✓
      </div>

      <span className="text-xs font-bold uppercase tracking-widest text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
        Payment Successful
      </span>

      <h2 className="text-2xl font-black text-slate-900 mt-4">
        You paid ₦{contract ? Number(contract.total_escrow).toLocaleString() : '---'} to Covalent
      </h2>

      <p className="text-sm text-slate-500 mt-2">
        Your funds are safely locked in our escrow vault. The seller has been notified to dispatch your package.
      </p>

      {error && <div className="mt-4 p-3 bg-red-50 text-red-600 rounded-lg text-xs">{error}</div>}

      {/* Receipt Breakdown Box */}
      <div className="my-6 p-4 bg-slate-50 border border-slate-200/80 rounded-xl text-left space-y-2 font-mono text-xs">
        <div className="flex justify-between text-slate-500">
          <span>Reference:</span>
          <span className="font-bold text-slate-900">{reference || 'COVA-VERIFIED'}</span>
        </div>
        {contract && (
          <>
            <div className="flex justify-between text-slate-500">
              <span>Item Title:</span>
              <span className="font-bold text-slate-900 truncate max-w-[180px]">{contract.item_title}</span>
            </div>
            <div className="flex justify-between text-slate-500">
              <span>Seller Email:</span>
              <span className="font-bold text-slate-900">{contract.vendor_email}</span>
            </div>
            <div className="flex justify-between text-slate-500 border-t border-slate-200 pt-2">
              <span>Status:</span>
              <span className="text-emerald-600 font-bold">LOCKED IN ESCROW 🔒</span>
            </div>
          </>
        )}
      </div>

      <button
        onClick={clearUrlParamsAndReturn}
        className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3.5 rounded-xl transition shadow-sm"
      >
        Go to Active Deals & Track Delivery
      </button>
    </div>
  );
}