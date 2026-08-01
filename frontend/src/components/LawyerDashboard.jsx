import { useState, useEffect } from "react";
import api from '../services/api';

// Reusable primitive
function SectionLabel({ children }) {
  return <p className="text-[10px] font-semibold tracking-widest text-slate-400 uppercase mb-3">{children}</p>;
}

export default function LawyerDashboard() {
  const [activeTab, setActiveTab] = useState("docket"); // "docket" or "invitations"
  
  const [disputes, setDisputes] = useState([]);
  const [invitations, setInvitations] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [selectedCase, setSelectedCase] = useState(null);
  const [selectedInvitation, setSelectedInvitation] = useState(null);
  
  const [justification, setJustification] = useState("");
  const [ruled, setRuled] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [successMessage, setSuccessMessage] = useState("");
  const [error, setError] = useState("");

  const fmtNGN = (n) => "₦" + Number(n).toLocaleString("en-NG");

  const fetchChamberData = () => {
    setLoading(true);
    // Fetch both active accepted cases and pending drafts concurrently
    Promise.all([
      api.get('escrow/disputes/'), // Adjust endpoint to your active cases route
      api.get('escrow/assignments/pending/') // Adjust to your pending assignments route
    ])
      .then(([disputesRes, invRes]) => {
        setDisputes(disputesRes.data);
        setInvitations(invRes.data);
        
        if (activeTab === "docket" && disputesRes.data.length > 0 && !selectedCase) {
          setSelectedCase(disputesRes.data[0]);
        }
      })
      .catch((err) => console.error("Failed to load governance chamber:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchChamberData();
  }, [activeTab]);

  // Handle Accept/Decline Action for Drafts
  const handleAssignmentResponse = (assignmentId, action) => {
    setSubmitting(true);
    setError("");

    api.post(`escrow/assignments/${assignmentId}/respond/`, { action })
      .then((res) => {
        setSuccessMessage(res.data.message || `Assignment ${action.toLowerCase()}ed successfully.`);
        setTimeout(() => setSuccessMessage(''), 5000);
        setSelectedInvitation(null);
        fetchChamberData();
        
        // Auto-switch to docket if they accepted so they can start working
        if (action === "ACCEPT") {
          setActiveTab("docket");
        }
      })
      .catch((err) => {
        setError(err.response?.data?.detail || `Failed to ${action.toLowerCase()} assignment.`);
      })
      .finally(() => setSubmitting(false));
  };

  // Voting Logic for Active Cases
  const handleRule = (side) => {
    if (justification.trim().length < 80) return;
    
    setSubmitting(true);
    setError("");

    api.post(`escrow/disputes/${selectedCase.id}/vote/`, {
      ruling: side,
      justification: justification,
    })
      .then((res) => {
        setSuccessMessage(res.data.message || 'Verdict submitted successfully and logged to Audit Trail.');
        setRuled(side);
        
        setTimeout(() => setSuccessMessage(''), 5000);
        fetchChamberData();
      })
      .catch((err) => {
        setError(err.response?.data?.detail || 'Failed to submit verdict.');
      })
      .finally(() => setSubmitting(false));
  };

  if (loading && disputes.length === 0 && invitations.length === 0) {
    return <div className="py-12 text-center text-slate-500 font-medium">Loading Governance Chamber...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 py-6 relative">
      
      {/* Floating Success Toast */}
      {successMessage && (
        <div className="fixed top-6 right-6 z-50 animate-in slide-in-from-top-4 fade-in duration-300">
          <div className="flex items-center gap-3 bg-emerald-900 border border-emerald-700 text-emerald-100 px-6 py-4 rounded-2xl shadow-2xl text-sm font-medium">
            <span className="text-xl">⚖️</span>
            <span>{successMessage}</span>
            <button onClick={() => setSuccessMessage('')} className="ml-4 text-emerald-400 hover:text-white font-bold">✕</button>
          </div>
        </div>
      )}

      {/* Header & Tabs */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6 border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center">
            <svg className="w-5 h-5 text-amber-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3" />
            </svg>
          </div>
          <div>
            <h2 className="text-slate-900 font-semibold text-base">Governance Chamber</h2>
            <p className="text-slate-500 text-xs">Arbitration workspace — Dispute Resolution</p>
          </div>
        </div>

        {/* Tab Toggle */}
        <div className="flex items-center bg-slate-100 p-1 rounded-lg">
          <button
            onClick={() => { setActiveTab("invitations"); setSelectedCase(null); }}
            className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all ${
              activeTab === "invitations" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Pending Drafts {invitations.length > 0 && <span className="ml-1.5 bg-red-500 text-white px-1.5 py-0.5 rounded-full text-[9px]">{invitations.length}</span>}
          </button>
          <button
            onClick={() => { setActiveTab("docket"); setSelectedInvitation(null); }}
            className={`px-4 py-1.5 text-xs font-bold rounded-md transition-all ${
              activeTab === "docket" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
            }`}
          >
            Active Docket ({disputes.length})
          </button>
        </div>
      </div>

      <div className="flex flex-col md:flex-row gap-4">
        
        {/* Left Pane: Dynamic List based on Active Tab */}
        <div className="md:w-72 flex-shrink-0">
          <SectionLabel>{activeTab === "invitations" ? "System Drafts" : "Case Docket"}</SectionLabel>
          <div className="flex flex-col gap-2">
            
            {/* INVITATIONS LIST */}
            {activeTab === "invitations" && (
              invitations.length === 0 ? (
                <div className="text-center p-6 bg-white border border-slate-200 rounded-xl text-slate-500 text-sm">
                  No pending drafts.
                </div>
              ) : (
                invitations.map(inv => (
                  <button
                    key={inv.id}
                    onClick={() => { setSelectedInvitation(inv); setError(""); }}
                    className={`text-left p-3.5 rounded-xl border transition-all ${
                      selectedInvitation?.id === inv.id ? "bg-purple-50 border-purple-200 shadow-sm" : "bg-white border-slate-200/80 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1.5">
                      <span className="text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider bg-slate-100 text-slate-600">NEW DRAFT</span>
                      <span className="text-[10px] text-slate-400 font-mono">12h Left</span>
                    </div>
                    <p className="text-sm font-medium text-slate-800 truncate">{inv.dispute?.contract?.item_title || "Escrow Dispute"}</p>
                    <p className="font-mono text-xs text-slate-600 font-semibold mt-2">{fmtNGN(inv.dispute?.contract?.total_escrow || 0)}</p>
                  </button>
                ))
              )
            )}

            {/* DOCKET LIST */}
            {activeTab === "docket" && (
              disputes.length === 0 ? (
                <div className="text-center p-6 bg-white border border-slate-200 rounded-xl text-slate-500 text-sm">
                  No active disputes. The docket is clear.
                </div>
              ) : (
                disputes.map(c => (
                  <button
                    key={c.id}
                    onClick={() => { setSelectedCase(c); setRuled(null); setJustification(""); setError(""); }}
                    className={`text-left p-3.5 rounded-xl border transition-all ${
                      selectedCase?.id === c.id
                        ? "bg-amber-50 border-amber-200 shadow-sm"
                        : "bg-white border-slate-200/80 hover:border-slate-300"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2 mb-1.5">
                      <p className="font-mono text-xs font-semibold text-slate-700">#{c.contract?.paystack_reference || c.id}</p>
                      <span className="text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider bg-red-50 text-red-700 border border-red-200">
                        HIGH
                      </span>
                    </div>
                    <p className="text-sm font-medium text-slate-800 truncate">{c.contract?.item_title || "Escrow Dispute"}</p>
                    <div className="flex items-center justify-between mt-2">
                      <p className="font-mono text-xs text-slate-600 font-semibold">{fmtNGN(c.contract?.total_escrow || 0)}</p>
                      <p className="text-[10px] text-slate-400">Due in 48h</p>
                    </div>
                  </button>
                ))
              )
            )}
          </div>
        </div>

        {/* Right Pane: Dynamic Workspace based on Active Tab */}
        <div className="flex-1 min-w-0">
          
          {/* INVITATION WORKSPACE */}
          {activeTab === "invitations" && selectedInvitation && (
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm animate-in fade-in">
              <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-4">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" /></svg>
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-2">You have been drafted.</h3>
              <p className="text-sm text-slate-600 mb-6 leading-relaxed">
                The Covalent consensus engine has randomly selected you to arbitrate a dispute over a <strong>{fmtNGN(selectedInvitation.dispute?.contract?.total_escrow || 0)}</strong> escrow contract. By accepting, you commit to reviewing the evidence impartially.
              </p>

              {error && <div className="mb-4 text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-200">{error}</div>}

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => handleAssignmentResponse(selectedInvitation.id, "ACCEPT")}
                  disabled={submitting}
                  className="py-3 rounded-xl font-bold text-sm bg-slate-900 hover:bg-slate-800 text-white transition-all disabled:opacity-50"
                >
                  Accept Case
                </button>
                <button
                  onClick={() => handleAssignmentResponse(selectedInvitation.id, "DECLINE")}
                  disabled={submitting}
                  className="py-3 rounded-xl font-bold text-sm bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-red-600 transition-all disabled:opacity-50"
                >
                  Decline (Pass to Next)
                </button>
              </div>
            </div>
          )}

          {/* DOCKET WORKSPACE */}
          {activeTab === "docket" && selectedCase && (
            ruled ? (
              <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center animate-in zoom-in-95">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 ${ruled === "buyer" ? "bg-blue-50" : "bg-emerald-50"}`}>
                  <svg className={`w-8 h-8 ${ruled === "buyer" ? "text-blue-600" : "text-emerald-600"}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="font-semibold text-slate-900 text-lg mb-1">Ruling Submitted</h3>
                <p className="text-slate-500 text-sm mb-4">
                  {ruled === "buyer" ? "Refund ruled for buyer." : "Funds ruled for release to vendor."} Case #{selectedCase.id} vote logged on-chain.
                </p>
                <button 
                  onClick={() => {
                    setRuled(null); 
                    setSelectedCase(disputes.length > 0 ? disputes[0] : null);
                  }} 
                  className="text-sm text-slate-500 hover:text-slate-800 underline underline-offset-4"
                >
                  Review next case
                </button>
              </div>
            ) : (
              <div className="animate-in fade-in">
                {/* Case file */}
                <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-4">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-mono text-sm font-bold text-slate-700">#{selectedCase.contract?.paystack_reference || selectedCase.id}</p>
                        <span className="text-[9px] text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded font-semibold tracking-wider">HIGH PRIORITY</span>
                      </div>
                      <h3 className="text-base font-semibold text-slate-900">{selectedCase.contract?.item_title || "Contract Dispute"}</h3>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Escrow Value</p>
                      <p className="font-mono text-lg font-bold text-slate-900">{fmtNGN(selectedCase.contract?.total_escrow || 0)}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-4">
                    {[
                      { label: "Claimant (Buyer)", value: selectedCase.buyer_email || "Buyer Anonymized" },
                      { label: "Respondent (Vendor)", value: selectedCase.vendor_email || "Vendor Anonymized" },
                    ].map(row => (
                      <div key={row.label} className="bg-slate-50 rounded-xl p-3">
                        <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-0.5">{row.label}</p>
                        <p className="text-sm font-semibold text-slate-700 font-mono truncate">{row.value}</p>
                      </div>
                    ))}
                  </div>

                  <div className="bg-slate-50 rounded-xl p-3.5">
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mb-1.5">Case Summary</p>
                    <p className="text-sm text-slate-700 leading-relaxed">
                      {selectedCase.description || "Parties could not reach an agreement regarding the fulfillment of this contract. Arbitration requested by system protocol."}
                    </p>
                  </div>
                </div>

                {/* Evidence inspection */}
                <div className="bg-white rounded-2xl border border-slate-200 p-5 mb-4">
                  <div className="flex items-center gap-2 mb-4">
                    <p className="text-[10px] font-semibold tracking-widest text-slate-400 uppercase">Evidence Locker</p>
                    <span className="text-[9px] bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded font-semibold">EXIF / Metadata Scrubbed</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {[
                      { type: "Document", name: "contract-scope.pdf", flag: "Anonymized", size: "890 KB" },
                      { type: "Image", name: "proof-of-delivery.png", flag: "EXIF stripped", size: "540 KB" },
                    ].map((ev, i) => {
                      const icons = { Image: "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z", Document: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" };
                      return (
                        <div key={i} className="flex items-center gap-3 p-3 rounded-xl border border-slate-100 hover:border-slate-200 hover:bg-slate-50 cursor-pointer transition-all group">
                          <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0 group-hover:bg-slate-200 transition-colors">
                            <svg className="w-4.5 h-4.5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.75}>
                              <path strokeLinecap="round" strokeLinejoin="round" d={icons[ev.type]} />
                            </svg>
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold text-slate-800 truncate">{ev.name}</p>
                            <p className="text-[10px] text-slate-400">{ev.size} · <span className="text-emerald-600 font-semibold">{ev.flag}</span></p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Justification + Ruling */}
                <div className="bg-white rounded-2xl border border-slate-200 p-5">
                  <p className="text-[10px] font-semibold tracking-widest text-slate-400 uppercase mb-3">Legal Justification (Required)</p>
                  {error && <div className="mb-3 text-xs text-red-600 bg-red-50 p-2 rounded-lg border border-red-200">{error}</div>}
                  <textarea
                    value={justification}
                    onChange={e => setJustification(e.target.value)}
                    disabled={submitting}
                    placeholder="Enter your legal reasoning for the ruling. This will be logged immutably and shared with both parties..."
                    className="w-full h-24 text-sm text-slate-800 placeholder-slate-300 bg-slate-50 border border-slate-200 rounded-xl px-3.5 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-amber-300 focus:border-amber-400 transition-all disabled:opacity-50"
                  />
                  <p className="text-[10px] text-slate-400 mb-4 mt-1">{justification.trim().length} chars — minimum 80 required for submission.</p>

                  <div className="grid grid-cols-2 gap-3">
                    <button
                      onClick={() => handleRule("buyer")}
                      disabled={justification.trim().length < 80 || submitting}
                      className={`py-3.5 rounded-xl font-semibold text-sm transition-all ${
                        justification.trim().length >= 80 && !submitting
                          ? "bg-blue-600 hover:bg-blue-700 text-white"
                          : "bg-blue-100 text-blue-300 cursor-not-allowed"
                      }`}
                    >
                      Rule for Buyer
                      <span className="block text-[10px] font-normal opacity-80 mt-0.5">Refund escrowed funds</span>
                    </button>
                    <button
                      onClick={() => handleRule("vendor")}
                      disabled={justification.trim().length < 80 || submitting}
                      className={`py-3.5 rounded-xl font-semibold text-sm transition-all ${
                        justification.trim().length >= 80 && !submitting
                          ? "bg-emerald-600 hover:bg-emerald-700 text-white"
                          : "bg-emerald-100 text-emerald-300 cursor-not-allowed"
                      }`}
                    >
                      Rule for Vendor
                      <span className="block text-[10px] font-normal opacity-80 mt-0.5">Release to vendor</span>
                    </button>
                  </div>
                </div>
              </div>
            )
          )}
          
          {/* Empty State when tab has no selection */}
          {((activeTab === "invitations" && !selectedInvitation) || (activeTab === "docket" && !selectedCase)) && (
            <div className="h-full flex items-center justify-center border-2 border-dashed border-slate-200 rounded-2xl text-slate-400 text-sm font-medium min-h-[300px]">
              Select an item from the list to view details
            </div>
          )}

        </div>
      </div>
    </div>
  );
}