import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import api, { downloadFile, errorMessage } from '../api';
export default function ModelRegistryPage() {
  const {getActiveProject, fetchProjectDetails}=useProjectStore();
  const project=getActiveProject();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  useEffect(()=>{
    if(project.status !== 'Training') return;
    const interval=setInterval(()=>fetchProjectDetails(project.id).catch(()=>{}),3000);
    return()=>clearInterval(interval);
  },[project.id,project.status,fetchProjectDetails]);
  const download=async name=>{setBusy(true);setError('');try{await downloadFile(`/projects/${project.id}/download-model?model_name=${encodeURIComponent(name)}`,`${project.id}_${name.replaceAll(' ','_')}.pkl`);}catch(e){setError(errorMessage(e));}finally{setBusy(false);}};
  const champion=async name=>{setBusy(true);setError('');try{await api.post(`/projects/${project.id}/champion`,{model_name:name});await fetchProjectDetails(project.id);}catch(e){setError(errorMessage(e));}finally{setBusy(false);}};
  const models=Object.entries(project.modelsComparison || {});
  return <div className="space-y-6"><h1 className="text-3xl font-bold">Model Registry</h1><p className="text-zinc-400">Compare trained pipelines, download model artifacts, and select the model used for predictions.</p>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    <section className="p-6 bg-brand-dark-surface border border-brand-dark-border rounded-xl overflow-x-auto">
      {models.length ? <table className="w-full text-left text-sm"><thead><tr><th className="py-3">Algorithm</th><th>Status</th><th>{project.problemType === 'classification' ? 'Test F1 (weighted)' : 'Test MSE'}</th><th>Test Accuracy</th><th>Actions</th></tr></thead><tbody>{models.map(([name, model])=><tr key={name} className="border-t border-brand-dark-border"><td className="py-4 font-semibold">{name}{project.bestModel === name && <span className="text-emerald-400 ml-2">Champion</span>}</td><td title={model.error}>{model.status}</td><td className="font-mono">{model.metric?.toFixed(4) ?? 'Pending'}</td><td>{model.accuracy != null ? `${(model.accuracy*100).toFixed(1)}%` : 'N/A'}</td><td><div className="flex gap-2"><button disabled={busy || model.status !== 'Trained'} onClick={()=>download(name)} className="bg-zinc-800 disabled:opacity-40 px-3 py-2 rounded-lg">Download {name}</button>{project.bestModel !== name && <button disabled={busy || model.status !== 'Trained' || project.status === 'Training'} onClick={()=>champion(name)} className="bg-brand-primary disabled:opacity-40 px-3 py-2 rounded-lg">Set Champion</button>}</div>{model.error && <p className="text-red-400 text-xs mt-2">{model.error}</p>}</td></tr>)}</tbody></table> : <p className="text-zinc-400">Train models to populate the registry.</p>}
    </section></div>;
}
