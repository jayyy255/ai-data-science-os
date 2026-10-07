import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import api, { errorMessage } from '../api';
export default function MonitoringPage() {
  const { getActiveProject, triggerTraining } = useProjectStore();
  const project = getActiveProject();
  const [result, setResult] = useState(null);
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => { setResult(null); setFile(null); setError(''); let alive=true; api.get(`/projects/${project.id}/monitor`).then(r=>{ if(alive) setResult(r.data); }).catch(e=>{ if(alive) setError(errorMessage(e)); }); return()=>{alive=false;}; }, [project.id]);
  const compare = async () => {
    setBusy(true); setError('');
    try { const form=new FormData(); form.append('file', file); const {data}=await api.post(`/projects/${project.id}/monitor`,form); setResult(data); }
    catch(e) { setError(errorMessage(e)); } finally { setBusy(false); }
  };
  const retrain = async () => { setBusy(true); try { await triggerTraining(project.id); } catch(e) { setError(errorMessage(e)); } finally { setBusy(false); } };
  return <div className="space-y-6">
    <h1 className="text-3xl font-bold">Model Monitoring & Drift</h1>
    <p className="text-zinc-400">Compare a new dataset with the uploaded baseline using Population Stability Index (PSI).</p>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <section className="p-6 bg-brand-dark-surface rounded-xl border border-brand-dark-border space-y-4">
      <label className="block">Monitoring dataset (CSV)<input aria-label="Monitoring dataset" type="file" accept=".csv" onChange={e=>setFile(e.target.files[0] || null)} className="block mt-3" /></label>
      <button disabled={!file || busy} onClick={compare} className="bg-brand-primary disabled:opacity-50 rounded-lg px-4 py-2">{busy ? 'Processing...' : 'Compare Dataset'}</button>
    </section>
    {result ? <section className="p-6 bg-brand-dark-surface rounded-xl border border-brand-dark-border space-y-4">
      <h2 className="font-bold">{result.driftStatus}</h2><p>Maximum PSI: {result.driftPsi.toFixed(4)} · {result.rows} observations · Alert threshold: 0.20</p>
      <table className="w-full text-left"><thead><tr><th className="py-2">Feature</th><th>PSI</th><th>Status</th></tr></thead><tbody>{result.features.map(f=><tr key={f.feature} className="border-t border-brand-dark-border"><td className="py-3">{f.feature}</td><td>{f.psi.toFixed(4)}</td><td>{f.psi > .2 ? 'Drift detected' : 'Stable'}</td></tr>)}</tbody></table>
      {result.driftPsi > .2 && <button disabled={busy || project.status === 'Training'} onClick={retrain} className="bg-brand-primary rounded-lg px-4 py-2">Retrain on Original Dataset</button>}
      <p className="text-sm text-zinc-400">PSI measures feature distribution changes. Production accuracy requires labeled outcomes and is not inferred from PSI.</p>
    </section> : <p className="text-zinc-400">No monitoring data yet. Upload a CSV containing the original predictor columns.</p>}
  </div>;
}
