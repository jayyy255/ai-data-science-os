import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import api, { downloadFile, errorMessage } from '../api';
export default function ModelRegistryPage() {
  const {getActiveProject, fetchProjectDetails}=useProjectStore();
  const project=getActiveProject();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [selectionReason,setSelectionReason]=useState('');
  useEffect(()=>{
    if(project.status !== 'Training') return;
    const interval=setInterval(()=>fetchProjectDetails(project.id).catch(()=>{}),3000);
    return()=>clearInterval(interval);
  },[project.id,project.status,fetchProjectDetails]);
  const download=async name=>{setBusy(true);setError('');try{await downloadFile(`/projects/${project.id}/download-model?model_name=${encodeURIComponent(name)}`,`${project.id}_${name.replaceAll(' ','_')}.pkl`);}catch(e){setError(errorMessage(e));}finally{setBusy(false);}};
  const champion=async name=>{setBusy(true);setError('');try{await api.post(`/projects/${project.id}/champion`,{model_name:name,reason:selectionReason.trim() || null});await fetchProjectDetails(project.id);setSelectionReason('');}catch(e){setError(errorMessage(e));}finally{setBusy(false);}};
  const models=Object.entries(project.modelsComparison || {});
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Model Registry</h1><p className="text-zinc-400">Compare trained pipelines, download model artifacts, and select the model used for predictions.</p>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <label className="block text-sm text-zinc-300">Reason for changing champion (optional)
      <input className="block w-full mt-2 p-3 rounded-xl border border-brand-dark-border" value={selectionReason} onChange={event=>setSelectionReason(event.target.value)} maxLength={1000} disabled={busy} placeholder="For example, prefer a smaller model for faster predictions" />
      <span className="block mt-2 text-xs text-zinc-400">Saved in the project timeline so the assistant can explain your choice.</span>
    </label>
    <section className="p-6 bg-brand-dark-surface border border-brand-dark-border rounded-xl overflow-x-auto" role="region" aria-label="Scrollable model registry" tabIndex={0}>
      {models.length ? <table className="w-full min-w-[720px] text-left text-sm [&_th]:px-3 [&_td]:px-3 [&_th]:whitespace-nowrap [&_td]:whitespace-nowrap"><thead><tr><th className="py-3">Algorithm</th><th>Status</th><th>{project.problemType === 'classification' ? 'Test F1 (weighted)' : 'Test MSE'}</th>{project.problemType === 'classification' && <th>Test Accuracy</th>}<th>Actions</th></tr></thead><tbody>{models.map(([name, model])=><tr key={name} className="border-t border-brand-dark-border"><td className="py-4 font-semibold">{name}{project.bestModel === name && <span className="text-emerald-400 ml-2">Champion</span>}</td><td title={model.error}>{model.status}</td><td className="font-mono">{model.metric?.toFixed(4) ?? 'Pending'}</td>{project.problemType === 'classification' && <td>{model.accuracy != null ? `${(model.accuracy*100).toFixed(1)}%` : 'N/A'}</td>}<td><div className="flex gap-2"><button disabled={busy || model.status !== 'Trained'} onClick={()=>download(name)} className="bg-zinc-800 disabled:opacity-40 px-3 py-2 rounded-lg">Download {name}</button>{project.bestModel !== name && <button disabled={busy || model.status !== 'Trained' || project.status === 'Training'} onClick={()=>champion(name)} className="bg-brand-primary disabled:opacity-40 px-3 py-2 rounded-lg">Set Champion</button>}</div>{model.error && <p className="text-red-400 text-xs mt-2">{model.error}</p>}</td></tr>)}</tbody></table> : <p className="text-zinc-400">Train models to populate the registry.</p>}
    </section></div>;
}
