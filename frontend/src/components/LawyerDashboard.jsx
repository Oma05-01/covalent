import { useState, useEffect } from 'react';
import api from '../services/api';

export default function LawyerDashboard() {
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState('');
  const [error, setError] = useState('');
  const [justification, setJustification] = useState({});

  useEffect(() => {
    fetchQueue();
  }, []);

  const fetchQueue = async () => {
    try {
      const res = await api.get('governance/queue/');
      // Safely ensure we always set an array even if backend returns null
      setDisputes(Array.isArray(res.data) ? res.data : res.data?.results || []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load arbitration queue. Verify endpoints are active.");
    } finally {
      setLoading(false);
    }
  };

  const handleVote = async (disputeId, rulingType) => {
    const text = justification[disputeId] || "";
    if (!text.trim()) {
      alert("Please provide a brief legal justification for your ruling before submitting.");
      return;
    }

    setActionLoading(`${disputeId}-${rulingType}`);
    setError('');
    try {
      const res = await api.post(`governance/vote/${disputeId}/`, {
        ruling: rulingType,
        justification: text
      });
      alert(res.data.message || "Vote recorded successfully.");
      setJustification(prev => ({ ...prev, [disputeId]: '' })); // Clear input
      await fetchQueue();
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit vote.");
    } finally {
      setActionLoading('');
    }
  };

  if (loading) return <div className="p-8 text-center text-slate-400">Loading anonymized case files...</div>;

  return (
    <div className="space-y-6">
      <div className="bg-slate-900 text-white p-6 rounded-2xl flex justify-between items-center shadow-sm">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-widest bg-emerald-500/20 text-emerald-400 px-2.5 py-1 rounded-full">
            Governance Engine
          </span>
          <h2 className="text-xl font-bold mt-2">Anonymous Arbitration Chamber</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Review scrubbed evidence and rule on contract disputes. Identities are strictly masked to ensure impartiality.
          </p>
        </div>
        <div className="text-right font-mono">
          <div className="text-2xl font-bold text-amber-400">{disputes.length}</div>
          <div className="text-xs text-slate-400">Pending Reviews</div>
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-bold">{error}</div>}

      {disputes.length === 0 ? (
        <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center text-slate-500">
          <div className="text-3xl mb-2">⚖️</div>
          <div className="font-bold text-slate-800">The Arbitration Queue is Clean</div>
          <p className="text-xs mt-1">There are no open disputes requiring review at this time.</p>
        </div>
      ) : (
        disputes.map((d) => (
          <div key={d.id || d.contract_id} className="bg-white border border-slate-200/80 rounded-2xl p-6 shadow-sm space-y-4">
            <div className="flex justify-between items-start border-b border-slate-100 pb-3">
              <div>
                <span className="text-xs font-mono text-slate-400">CASE FILE #{d.id || d.contract_id}</span>
                <h3 className="text-lg font-bold text-slate-900 mt-0.5">{d.item_title}</h3>
                <p className="text-xs text-red-600 font-bold mt-1">Claim: "{d.reason || 'Doorstep Rejection / Breach of Terms'}"</p>
              </div>
              <div className="text-right font-mono">
                <span className="text-xs text-slate-400 block">Escrow Pool</span>
                <span className="text-base font-bold text-slate-900">₦{Number(d.total_escrow || 0).toLocaleString()}</span>
              </div>
            </div>

            {/* Contract & Dispute Details */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-4 rounded-xl text-xs text-slate-700">
              <div>
                <span className="font-bold text-slate-900 block mb-1">Binding AI Contract Terms:</span>
                <p className="italic text-slate-600">{d.plain_language_summary || "Standard delivery and verification terms apply."}</p>
              </div>
              <div>
                <span className="font-bold text-slate-900 block mb-1">Dispute Explanation:</span>
                <p className="text-slate-600">{d.description || "Buyer rejected package upon arrival or vendor failed to deliver."}</p>
              </div>
            </div>

            {/* Anonymized Evidence Viewer - SAFEGUARDED AGAINST NULL ARRAYS */}
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 block mb-2">
                Scrubbed Visual Evidence ({(d.evidence_files || []).length} files attached)
              </span>
              
              {(d.evidence_files || []).length === 0 ? (
                <div className="text-xs text-slate-400 italic py-2">No multimedia evidence uploaded for this dispute.</div>
              ) : (
                <div className="flex gap-3 overflow-x-auto pb-2">
                  {(d.evidence_files || []).map((file, idx) => (
                    <div key={file.id || idx} className="border border-slate-200 rounded-lg overflow-hidden bg-slate-900 w-48 h-32 flex-shrink-0 flex items-center justify-center relative group">
                      {file.file_url ? (
                        file.file_type === 'IMAGE' ? (
                          <img src={file.file_url} alt="Evidence" className="w-full h-full object-cover" />
                        ) : (
                          <video src={file.file_url} controls className="w-full h-full object-cover" />
                        )
                      ) : (
                        <span className="text-[10px] text-slate-400">Processing Media...</span>
                      )}
                      <span className="absolute bottom-1 right-1 bg-black/70 text-white text-[9px] px-1.5 py-0.5 rounded font-mono">
                        {file.file_type || 'FILE'} (EXIF/Audio Scrubbed)
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Voting Justification & Actions */}
            <div className="pt-3 border-t border-slate-100 space-y-3">
              <input
                type="text"
                placeholder="Enter legal justification for your ruling (required)..."
                value={justification[d.id || d.contract_id] || ''}
                onChange={(e) => setJustification({ ...justification, [d.id || d.contract_id]: e.target.value })}
                className="w-full px-3.5 py-2 text-xs rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => handleVote(d.id || d.contract_id, 'BUYER')}
                  disabled={!!actionLoading}
                  className="flex-1 bg-red-50 hover:bg-red-100 text-red-700 border border-red-200 py-3 rounded-xl text-xs font-bold transition disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {actionLoading === `${d.id || d.contract_id}-BUYER` ? 'Recording...' : '⚖️ Rule for Buyer (Refund Escrow)'}
                </button>
                <button
                  onClick={() => handleVote(d.id || d.contract_id, 'VENDOR')}
                  disabled={!!actionLoading}
                  className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white py-3 rounded-xl text-xs font-bold transition disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  {actionLoading === `${d.id || d.contract_id}-VENDOR` ? 'Recording...' : '⚖️ Rule for Vendor (Release Escrow)'}
                </button>
              </div>
            </div>

          </div>
        ))
      )}
    </div>
  );
}