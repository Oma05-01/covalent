import { useState } from 'react';
import api from '../services/api';

export default function AIContractBuilder({ onContractFunded }) {
  const [prompt, setPrompt] = useState('');
  const [vendorEmail, setVendorEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Generated Contract State
  const [contract, setContract] = useState(null);
  const [paying, setPaying] = useState(false);

  // Field-level Editing State
  const [isEditing, setIsEditing] = useState(false);
  const [editFormData, setEditFormData] = useState({});
  const [savingEdits, setSavingEdits] = useState(false);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setContract(null);
    setIsEditing(false);

    try {
      const res = await api.post('contracts/generate/', {
        prompt,
        vendor_email: vendorEmail
      });
      setContract(res.data);
      // Pre-fill the edit form with the exact terms returned by the AI
      setEditFormData(res.data.terms);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate contract.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveEdits = async () => {
    setSavingEdits(true);
    setError('');
    try {
      // Send a PATCH request to update only the changed fields
      await api.patch(`contracts/${contract.contract_id}/`, {
        item_title: editFormData.item_title,
        item_description: editFormData.item_description,
        item_amount: editFormData.item_amount,
        delivery_fee: editFormData.delivery_fee,
        delivery_days: editFormData.delivery_days
      });
      
      // Update the local React state with the new values
      const newTotalEscrow = Number(editFormData.item_amount) + Number(editFormData.delivery_fee);
      setContract({
        ...contract,
        terms: editFormData,
        total_escrow: newTotalEscrow
      });
      setIsEditing(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update contract terms.');
    } finally {
      setSavingEdits(false);
    }
  };

  const handleFundEscrow = async () => {
    setPaying(true);
    setError('');
    try {
      const res = await api.post('contracts/pay/', {
        contract_id: contract.contract_id
      });
      // Redirect buyer to official Paystack checkout modal/page
      window.location.href = res.data.authorization_url;
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not initiate Paystack checkout.');
      setPaying(false);
    }
  };

  return (
    <div className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Create Escrow Contract</h2>
        <p className="text-sm text-slate-500 mt-1">
          Describe your deal in plain text. Our AI mediator will draft binding terms automatically.
        </p>
      </div>

      {/* Floating Pill Error Modal */}
      {error && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <div className="flex items-center gap-3 bg-slate-900 border border-slate-700 text-white px-5 py-3 rounded-full shadow-2xl text-sm font-medium">
            <span className="flex-h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
            <span>{error}</span>
            <button 
              onClick={() => setError(null)}
              className="ml-2 text-slate-400 hover:text-white font-bold px-1.5 py-0.5 rounded-full hover:bg-slate-800 transition text-xs"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {!contract ? (
        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Vendor's Email Address</label>
            <input
              type="email"
              required
              value={vendorEmail}
              onChange={(e) => setVendorEmail(e.target.value)}
              placeholder="vendor@instagram.com"
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none text-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Deal Description</label>
            <textarea
              rows="4"
              required
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="e.g., I am buying a UK-used iPhone 13 Pro (256GB, Sierra Blue, 88% battery health) from this vendor for 850k. Delivery is 5k to Lekki Phase 1 by tomorrow afternoon."
              className="w-full px-4 py-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none text-slate-900 text-sm"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !prompt || !vendorEmail}
            className="w-full bg-slate-900 hover:bg-slate-800 text-white font-medium py-3 rounded-lg transition disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {loading ? (
              <><span>Drafting Contract with AI...</span></>
            ) : (
              'Generate Binding Contract'
            )}
          </button>
        </form>
      ) : isEditing ? (
        
        /* ------------------------------------------------ */
        /* FIELD-LEVEL EDITING FORM                         */
        /* ------------------------------------------------ */
        <div className="border-2 border-slate-900 rounded-xl p-5 bg-white space-y-4 animate-in fade-in duration-200">
          <h3 className="font-bold text-lg text-slate-900 border-b border-slate-200 pb-2">Edit Contract Terms</h3>
          
          <div className="space-y-3">
            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Item Title</label>
              <input 
                value={editFormData.item_title}
                onChange={(e) => setEditFormData({...editFormData, item_title: e.target.value})}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 outline-none text-slate-900"
              />
            </div>
            
            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Specifications</label>
              <textarea 
                rows="2"
                value={editFormData.item_description}
                onChange={(e) => setEditFormData({...editFormData, item_description: e.target.value})}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 outline-none text-slate-900 text-sm"
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="col-span-1">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Amount (₦)</label>
                <input 
                  type="number"
                  value={editFormData.item_amount}
                  onChange={(e) => setEditFormData({...editFormData, item_amount: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 outline-none text-slate-900"
                />
              </div>
              <div className="col-span-1">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Delivery (₦)</label>
                <input 
                  type="number"
                  value={editFormData.delivery_fee}
                  onChange={(e) => setEditFormData({...editFormData, delivery_fee: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 outline-none text-slate-900"
                />
              </div>
              <div className="col-span-1">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">Days</label>
                <input 
                  type="number"
                  value={editFormData.delivery_days}
                  onChange={(e) => setEditFormData({...editFormData, delivery_days: e.target.value})}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-900 outline-none text-slate-900"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-3">
            <button 
              onClick={() => setIsEditing(false)}
              className="px-4 py-2.5 text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg font-bold transition"
            >
              Cancel
            </button>
            <button 
              onClick={handleSaveEdits}
              disabled={savingEdits}
              className="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg font-bold transition flex-1"
            >
              {savingEdits ? 'Saving Updates...' : 'Save Updates'}
            </button>
          </div>
        </div>

      ) : (
        /* ------------------------------------------------ */
        /* SUMMARY CARD                                     */
        /* ------------------------------------------------ */
        <div className="border-2 border-slate-900 rounded-xl p-5 bg-slate-50 space-y-4 animate-in fade-in duration-200">
          <div className="flex justify-between items-start border-b border-slate-200 pb-3">
            <div>
              <span className="text-xs font-bold bg-slate-900 text-white px-2 py-0.5 rounded uppercase">AI Drafted Deal</span>
              <h3 className="text-lg font-bold text-slate-900 mt-1">{contract.terms.item_title}</h3>
            </div>
            <div className="flex flex-col items-end gap-2">
               <button onClick={() => setIsEditing(true)} className="text-xs font-bold text-blue-600 hover:text-blue-800 hover:underline">
                 Edit Fields
               </button>
               {/* Note: Assuming you have a handle API call to actually delete the contract in your delete button */}
               <button onClick={() => setContract(null)} className="text-xs text-red-500 hover:text-red-700 hover:underline">
                 Discard Draft
               </button>
            </div>
          </div>

          <div className="space-y-2 text-sm text-slate-700">
            <div><span className="font-bold text-slate-900">Specifications:</span> {contract.terms.item_description}</div>
            <div><span className="font-bold text-slate-900">Estimated Delivery:</span> Within {contract.terms.delivery_days} days</div>
            <div className="p-3 bg-amber-50/60 border border-amber-200/80 rounded-lg text-xs text-amber-900">
              <span className="font-bold block mb-1">⚖️ Plain Language Safeguard:</span>
              {contract.terms.plain_language_summary}
            </div>
          </div>

          <div className="border-t border-slate-200 pt-3 flex justify-between items-center font-mono">
            <div className="text-xs text-slate-500">
              Item: ₦{Number(contract.terms.item_amount).toLocaleString()} + Delivery: ₦{Number(contract.terms.delivery_fee).toLocaleString()}
            </div>
            <div className="text-lg font-bold text-slate-900">
              Total Escrow: ₦{Number(contract.total_escrow).toLocaleString()}
            </div>
          </div>

          <button
            onClick={handleFundEscrow}
            disabled={paying}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3.5 rounded-xl transition shadow-sm disabled:opacity-50 text-base"
          >
            {paying ? 'Connecting to Paystack...' : `Accept Terms & Lock ₦${Number(contract.total_escrow).toLocaleString()} in Escrow`}
          </button>
        </div>
      )}
    </div>
  );
}