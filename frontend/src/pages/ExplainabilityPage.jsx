import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import api, { errorMessage } from '../api';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function ExplainabilityPage() {
  const project = useProjectStore(state => state.getActiveProject());
  const [row, setRow] = useState('0');
  const [local, setLocal] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');
  const [prediction, setPrediction] = useState(null);
  useEffect(() => {
    setLocal(null); setPrediction(null); setError(''); setRow('0');
    setInput(JSON.stringify([Object.fromEntries(project.features.filter(f => f.name !== project.targetVariable).map(f => [f.name, f.type.includes('int') || f.type.includes('float') ? Number.isFinite(Number(f.sample)) ? Number(f.sample) : null : f.sample]))], null, 2));
  }, [project.id, project.features, project.targetVariable]);
  const explainRow = async () => {
    setLoading(true); setError('');
    try { const { data } = await api.get(`/projects/${project.id}/explain/${row}`); setLocal(data); }
    catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  };
  const predict = async () => {
    setLoading(true); setError('');
    try { const { data } = await api.post(`/projects/${project.id}/predict`, { rows: JSON.parse(input) }); setPrediction(data); }
    catch (err) { setError(errorMessage(err)); }
    finally { setLoading(false); }
  };
  if (!project.modelPath) return <div className="space-y-4"><h1 className="text-3xl font-bold">Explainability & Predictions</h1><p className="text-zinc-400">Train a model to inspect feature importance and make predictions.</p></div>;
  return <div className="space-y-6">
    <h1 className="text-3xl font-bold">Explainability & Predictions</h1>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <section className="p-6 bg-brand-dark-surface border border-brand-dark-border rounded-xl">
      <h2 className="font-bold mb-2">Global Feature Importance</h2>
      <p className="text-sm text-zinc-400 mb-4">{project.shapGlobal[0]?.type || 'Feature importance'}. Magnitudes show influence, not direction.</p>
      <div className="h-80"><ResponsiveContainer width="100%" height="100%"><BarChart data={project.shapGlobal.slice(0,12)} layout="vertical" margin={{ left: 50 }}><XAxis type="number" /><YAxis type="category" dataKey="feature" width={150} /><Tooltip /><Bar dataKey="shap" fill="#8b5cf6" /></BarChart></ResponsiveContainer></div>
    </section>
    <section className="p-6 bg-brand-dark-surface border border-brand-dark-border rounded-xl space-y-4">
      <h2 className="font-bold">Explain a Dataset Row</h2>
      <label className="text-sm text-zinc-400">Row index (0-{project.rowsCount - 1}) <input aria-label="Row index" type="number" min="0" max={project.rowsCount-1} value={row} onChange={e=>setRow(e.target.value)} className="bg-brand-dark-bg border border-brand-dark-border rounded-lg p-2 ml-3" /></label>
      <button disabled={loading} onClick={explainRow} className="bg-brand-primary px-4 py-2 rounded-lg ml-3">Explain Row</button>
      {local && <div className="space-y-3"><p>Prediction: <strong>{local.prediction}</strong>{local.probability != null && ` (confidence ${(local.probability*100).toFixed(1)}%)`}</p><p className="text-zinc-400 text-sm">{local.explanation_method}</p>{local.drivers.map(driver=><div key={driver.feature} className="flex justify-between border-b border-brand-dark-border py-2"><span>{driver.feature}: {driver.value}</span><span>{driver.impact}</span></div>)}</div>}
    </section>
    <section className="p-6 bg-brand-dark-surface border border-brand-dark-border rounded-xl space-y-4">
      <h2 className="font-bold">Predict New Observations</h2><p className="text-sm text-zinc-400">Enter a JSON array of rows using the original dataset columns. The saved model applies its fitted preprocessing.</p>
      <textarea aria-label="Prediction rows" rows={8} value={input} onChange={e=>setInput(e.target.value)} className="w-full bg-brand-dark-bg border border-brand-dark-border rounded-lg p-3 font-mono text-sm" />
      <button disabled={loading} onClick={predict} className="bg-brand-primary px-4 py-2 rounded-lg">Run Prediction</button>
      {prediction && <pre className="overflow-x-auto p-3 text-sm text-emerald-300">{JSON.stringify(prediction,null,2)}</pre>}
    </section>
  </div>;
}
