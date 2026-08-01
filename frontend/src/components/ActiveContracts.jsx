import { useState, useEffect } from 'react';
import api from '../services/api';
import CountdownTimer from './CountdownTimer'; // 🆕 Import the timer component

export default function ActiveContracts({ currentUser, onStatusChanged }) {
  const [contracts, setContracts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [error, setError] = useState('');
  
  // Modals state
  const [confirmModal, setConfirmModal] = useState(null); // Doorstep Rejection
  const [deleteModal, setDeleteModal] = useState(null);   // Delete Draft Confirmation

  useEffect(() => {
    fetchContracts();
  }, []);

  const fetchContracts = async () => {
    try {
      const res = await api.get('contracts/');
      setContracts(res.data);
    } catch (err) {
      console.error("Failed to load contracts", err);
    } finally {
      setLoading(false);
    }
  };

  const handleAction = async (contractId, actionName) => {
    setActionLoading(`${contractId}-${actionName}`);
    setError('');
    setConfirmModal(null);
    
    try {
      await api.post(`contracts/${contractId}/${actionName}/`);
      await fetchContracts();
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      setError(err.response?.data?.detail || 'Action failed. Please check your network or contract status.');
    } finally {
      setActionLoading('');
    }
  };

  const handleDeleteDraft = async (contractId) => {
    setActionLoading(`${contractId}-delete`);
    setError('');
    setDeleteModal(null);

    try {
      await api.delete(`contracts/${contractId}/delete/`);
      await fetchContracts();
      if (onStatusChanged) onStatusChanged();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete draft contract.');
    } finally {
      setActionLoading('');
    }
  };

  if (loading) {
    return <div className="p-6 text-center text-slate-400">Loading active pipeline...</div>;
  }

  if (contracts.length === 0) {
    return (
      <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center text-slate-500 shadow-sm">
        <div className="text-3xl mb-2">📦</div>
        <div className="font-bold text-slate-800">No active escrow deals found</div>
        <p className="text-xs mt-1">Contracts you generate or receive will appear here once drafted.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4 relative">
      
      {/* 🛑 DOORSTEP REJECTION MODAL */}
      {confirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 text-white px-6 py-5 rounded-3xl shadow-2xl max-w-md w-full mx-4 relative animate-in zoom-in-95 duration-200">
            <button 
              onClick={() => setConfirmModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 w-7 h-7 rounded-full flex items-center justify-center text-xs transition"
            >
              ✕
            </button>

            <div className="flex items-center gap-3 mb-2">
              <span className="flex h-3 w-3 rounded-full bg-red-500 animate-pulse"></span>
              <h4 className="font-bold text-sm tracking-wide uppercase text-red-400">Confirm Doorstep Rejection</h4>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-6 pr-4">
              Are you sure you want to reject this item at the door? <strong className="text-white">The vendor will be penalized for dispatch costs</strong> and this case will be sent to the Lawyer Governance Chamber for arbitration.
            </p>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmModal(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => handleAction(confirmModal, 'dispute')}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/30 transition"
              >
                Yes, Reject & Penalize
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 🗑️ DELETE DRAFT CONFIRMATION MODAL */}
      {deleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-xs animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-700 text-white px-6 py-5 rounded-3xl shadow-2xl max-w-md w-full mx-4 relative animate-in zoom-in-95 duration-200">
            <button 
              onClick={() => setDeleteModal(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-white bg-slate-800/60 hover:bg-slate-800 w-7 h-7 rounded-full flex items-center justify-center text-xs transition"
            >
              ✕
            </button>

            <div className="flex items-center gap-3 mb-2">
              <span className="flex h-3 w-3 rounded-full bg-amber-500 animate-pulse"></span>
              <h4 className="font-bold text-sm tracking-wide uppercase text-amber-400">Delete Unfunded Draft</h4>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed mb-6 pr-4">
              Are you sure you want to delete this unfunded draft contract? <strong className="text-white">This action cannot be undone</strong> and will remove the deal from your active pipeline forever.
            </p>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setDeleteModal(null)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
              >
                Keep Draft
              </button>
              <button
                onClick={() => handleDeleteDraft(deleteModal)}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/30 transition"
              >
                Yes, Delete Draft
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Floating Pill Error Toast */}
      {error && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-3 bg-red-950 border border-red-800 text-red-200 px-5 py-3 rounded-full shadow-2xl text-xs font-medium">
            <span>⚠️ {error}</span>
            <button onClick={() => setError('')} className="ml-2 text-red-400 hover:text-white font-bold">✕</button>
          </div>
        </div>
      )}

      {contracts.map((contract) => {
        const isBuyer = currentUser.email !== contract.vendor_email;
        const isVendor = currentUser.email === contract.vendor_email;
        const isDraft = ['DRAFT', 'AWAITING_FUNDING', 'UNFUNDED'].includes(contract.status);

        return (
          <div key={contract.contract_id} className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-sm transition hover:border-slate-300">
            <div className="flex justify-between items-start border-b border-slate-100 pb-3 mb-3">
              <div>
                <span className="text-xs font-mono text-slate-400">#{contract.paystack_reference || 'UNFUNDED'}</span>
                <h3 className="text-base font-bold text-slate-900 mt-0.5">{contract.item_title}</h3>
              </div>
              <span className={`px-2.5 py-1 rounded-full text-xs font-bold ${
                contract.status === 'FUNDED' ? 'bg-blue-100 text-blue-800' :
                contract.status === 'IN_TRANSIT' ? 'bg-purple-100 text-purple-800' :
                contract.status === 'DELIVERED' ? 'bg-amber-100 text-amber-800' : // 🆕 New style for Delivered
                contract.status === 'RELEASED' ? 'bg-emerald-100 text-emerald-800' :
                contract.status === 'DISPUTED' ? 'bg-red-100 text-red-800 animate-pulse' :
                'bg-slate-100 text-slate-600'
              }`}>
                {contract.status.replace('_', ' ')}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs text-slate-600 mb-4 font-mono">
              <div><span className="text-slate-400 block">Item Cost:</span> ₦{Number(contract.item_amount).toLocaleString()}</div>
              <div><span className="text-slate-400 block">Dispatch Fee:</span> ₦{Number(contract.delivery_fee).toLocaleString()}</div>
            </div>

            {/* 🆕 INSPECTION WINDOW TIMER (Shows for both buyer and vendor if DELIVERED) */}
            {contract.status === 'DELIVERED' && contract.auto_release_at && (
              <div className="mb-4 bg-slate-50 border border-slate-200 rounded-xl p-3 flex flex-col items-center justify-center">
                <p className="text-xs text-slate-500 mb-2 font-bold uppercase tracking-wider">
                  Inspection Time Remaining
                </p>
                <CountdownTimer 
                  targetDate={contract.auto_release_at}
                  onExpire={() => fetchContracts()} // Refresh the list when it hits zero
                />
              </div>
            )}

            {/* Role-Based Action Bar */}
            <div className="pt-2 border-t border-slate-100 flex items-center gap-2 flex-wrap">
              
              {/* Vendor Actions: Dispatch */}
              {isVendor && contract.status === 'FUNDED' && (
                <button
                  onClick={() => handleAction(contract.contract_id, 'dispatch')}
                  disabled={!!actionLoading}
                  className="w-full bg-slate-900 hover:bg-slate-800 text-white py-2.5 rounded-xl text-xs font-bold transition disabled:opacity-50"
                >
                  {actionLoading === `${contract.contract_id}-dispatch` ? 'Updating...' : '🚚 Mark Package as Dispatched'}
                </button>
              )}

              {/* 🆕 Vendor Actions: Deliver (Starts the timer) */}
              {isVendor && contract.status === 'IN_TRANSIT' && (
                <button
                  onClick={() => handleAction(contract.contract_id, 'deliver')}
                  disabled={!!actionLoading}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2.5 rounded-xl text-xs font-bold transition disabled:opacity-50 shadow-lg shadow-blue-600/20"
                >
                  {actionLoading === `${contract.contract_id}-deliver` ? 'Updating...' : '📦 Mark as Delivered'}
                </button>
              )}

              {/* Buyer Actions: Confirm or Reject */}
              {isBuyer && ['FUNDED', 'IN_TRANSIT', 'DELIVERED'].includes(contract.status) && (
                <>
                  <button
                    onClick={() => handleAction(contract.contract_id, 'approve')} // Changed from 'confirm' to 'approve' to match your Django view
                    disabled={!!actionLoading}
                    className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-2.5 rounded-xl text-xs font-bold transition disabled:opacity-50"
                  >
                    {actionLoading === `${contract.contract_id}-approve` ? 'Releasing...' : '✅ Approve & Release Funds'}
                  </button>

                  <button
                    onClick={() => setConfirmModal(contract.contract_id)}
                    disabled={!!actionLoading}
                    className="flex-1 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 py-2.5 rounded-xl text-xs font-bold transition disabled:opacity-50"
                  >
                    {actionLoading === `${contract.contract_id}-dispute` ? 'Processing...' : '⚠️ Raise Dispute'}
                  </button>
                </>
              )}

              {/* Completed / Disputed States */}
              {contract.status === 'RELEASED' && (
                <div className="w-full text-center py-1.5 text-xs font-bold text-emerald-600 bg-emerald-50 rounded-lg">
                  Deal completed. Escrow disbursed.
                </div>
              )}

              {contract.status === 'DISPUTED' && (
                <div className="w-full text-center py-1.5 text-xs font-bold text-red-600 bg-red-50 rounded-lg">
                  Case escalated to Governance Chamber.
                </div>
              )}

              {/* Delete Draft */}
              {isDraft && (
                <button
                  onClick={() => setDeleteModal(contract.contract_id)}
                  disabled={!!actionLoading}
                  className="ml-auto text-xs font-bold text-red-600 hover:text-red-700 underline py-1.5 px-2 transition disabled:opacity-50"
                >
                  {actionLoading === `${contract.contract_id}-delete` ? 'Deleting...' : 'Delete Draft'}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
