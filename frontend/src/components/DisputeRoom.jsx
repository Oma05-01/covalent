import { useState } from 'react';
import api from '../services/api';

export default function DisputeRoom({ contract, onClose }) {
  const [reason, setReason] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState('IMAGE');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      // Auto-detect if video
      if (selected.type.startsWith('video/')) {
        setFileType('VIDEO');
      } else {
        setFileType('IMAGE');
      }
    }
  };

  const handleSubmitDispute = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("You must upload visual evidence (photo or video) to open an anonymous dispute.");
      return;
    }

    setLoading(true);
    setError('');
    setSuccessMsg('');

    try {
      // Step 1: In a full build, you would POST /api/disputes/create/ first to get a dispute_id.
      // For this MVP demonstration, we will assume Dispute ID #1 exists or map directly to contract.
      const disputeId = 1; 

      // Step 2: Upload evidence file using FormData so Django MultiPartParser can read it
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_type', fileType);

      await api.post(`disputes/${disputeId}/upload/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setSuccessMsg("Dispute opened! Your media was sent to our FFmpeg engine to strip background audio and metadata for anonymous review.");
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to submit evidence. Please check your file format.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-100 animate-in zoom-in-95 duration-200">
        
        <div className="flex justify-between items-center border-b border-slate-100 pb-4 mb-4">
          <div>
            <span className="px-2.5 py-0.5 bg-red-100 text-red-700 font-bold text-xs rounded-full uppercase tracking-wider">
              Governance Engine
            </span>
            <h3 className="text-lg font-bold text-slate-900 mt-1">Dispute Resolution Room</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 font-bold text-lg">✕</button>
        </div>

        <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl mb-4 text-xs text-slate-600">
          <span className="font-bold block text-slate-900 mb-0.5">⚖️ Anonymous Arbitration Safeguard:</span>
          To prevent reviewer bias, all uploaded photos have GPS/EXIF data stripped. All uploaded videos have spoken audio and background noise removed automatically via FFmpeg.
        </div>

        {error && <div className="mb-4 p-3 bg-red-50 text-red-600 border border-red-200 rounded-lg text-xs font-medium">{error}</div>}
        {successMsg && <div className="mb-4 p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-xs font-bold">{successMsg}</div>}

        {!successMsg ? (
          <form onSubmit={handleSubmitDispute} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Reason for Dispute</label>
              <input
                type="text"
                required
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g., Wrong sneaker size delivered / Item damaged"
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none text-sm text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Detailed Explanation</label>
              <textarea
                rows="3"
                required
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what was promised vs. what was delivered..."
                className="w-full px-3.5 py-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-slate-900 outline-none text-sm text-slate-900"
              />
            </div>

            {/* Media Dropzone */}
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">Upload Visual Proof (Photo / Video)</label>
              <div className="border-2 border-dashed border-slate-300 hover:border-slate-400 rounded-xl p-6 text-center transition bg-slate-50 cursor-pointer relative">
                <input
                  type="file"
                  required
                  accept="image/*,video/*"
                  onChange={handleFileChange}
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                />
                <div className="text-2xl mb-1">📹</div>
                <div className="text-xs font-bold text-slate-700">
                  {file ? file.name : "Click or drag file to upload evidence"}
                </div>
                <div className="text-[10px] text-slate-400 mt-1">
                  Supports MP4, MOV, JPG, PNG (Max 50MB)
                </div>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <button type="button" onClick={onClose} className="w-1/3 py-2.5 border border-slate-300 text-slate-700 rounded-lg text-xs font-bold hover:bg-slate-50 transition">
                Cancel
              </button>
              <button type="submit" disabled={loading || !file} className="w-2/3 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs font-bold py-2.5 transition disabled:opacity-50">
                {loading ? 'Scrubbing Media via FFmpeg...' : 'Submit Evidence to Review Room'}
              </button>
            </div>
          </form>
        ) : (
          <button onClick={onClose} className="w-full bg-slate-900 text-white font-bold py-3 rounded-xl text-sm mt-2">
            Return to Dashboard
          </button>
        )}

      </div>
    </div>
  );
}