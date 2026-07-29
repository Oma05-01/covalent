import { useState, useEffect } from 'react';
import api from '../services/api';

export default function DevPortal() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [newKeyName, setNewKeyName] = useState('');

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    const res = await api.get('dev/keys/');
    setKeys(res.data);
    setLoading(false);
  };

  const createKey = async () => {
    const res = await api.post('dev/keys/', { name: newKeyName });
    setKeys([...keys, res.data]);
    setNewKeyName('');
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-300">
      <div className="bg-slate-900 text-white p-6 rounded-2xl">
        <h2 className="text-xl font-bold">Developer Toolkit</h2>
        <p className="text-xs text-slate-400 mt-1">Generate API Keys to connect your store to Covalent Escrow.</p>
      </div>

      {/* API Key Generator */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6">
        <h3 className="font-bold text-slate-900 mb-4">Create New API Key</h3>
        <div className="flex gap-2">
          <input 
            className="flex-1 px-4 py-2 border rounded-lg text-sm"
            placeholder="e.g. My Shopify Store"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
          />
          <button onClick={createKey} className="bg-slate-900 text-white px-6 py-2 rounded-lg text-sm font-bold">
            Generate Key
          </button>
        </div>
      </div>

      {/* Keys Table */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6">
        <h3 className="font-bold text-slate-900 mb-4">Your Active Keys</h3>
        <div className="space-y-3">
          {keys.map((k) => (
            <div key={k.id} className="flex justify-between items-center p-4 bg-slate-50 rounded-xl font-mono text-xs">
              <div>
                <span className="font-bold block text-slate-900">{k.name}</span>
                <span className="text-slate-500">{k.key}</span>
              </div>
              <button 
                onClick={() => navigator.clipboard.writeText(k.key)}
                className="text-emerald-600 font-bold hover:underline"
              >
                Copy
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Integration Snippet */}
      <div className="bg-slate-800 text-slate-300 p-6 rounded-2xl text-xs font-mono">
        <div className="mb-2 text-emerald-400 font-bold uppercase">Integration Example (Node.js)</div>
        <pre>{`fetch('http://localhost:8000/api/v1/checkout/', {
  method: 'POST',
  headers: { 'X-Covalent-API-Key': 'YOUR_KEY_HERE' },
  body: JSON.stringify({
    vendor_email: 'shop@example.com',
    price: 50000,
    item_name: 'Custom Sneakers'
  })
});`}</pre>
      </div>
    </div>
  );
}