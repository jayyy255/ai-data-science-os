import React, { useState, useEffect } from 'react';
import api, { errorMessage } from '../api';
export default function SettingsPage() {
  const [system,setSystem]=useState(null);
  const [error,setError]=useState('');
  useEffect(()=>{api.get('/system').then(r=>setSystem(r.data)).catch(e=>setError(errorMessage(e)));},[]);
  return <div className="space-y-6"><h1 className="text-3xl font-bold">System Status</h1>{error && <p role="alert" className="text-red-400">{error}</p>}<section className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-6">{system ? <dl className="space-y-4">{Object.entries(system).map(([key,value])=><div key={key} className="flex justify-between gap-6"><dt className="capitalize text-zinc-400">{key.replaceAll('_',' ')}</dt><dd>{value ?? 'No heartbeat received'}</dd></div>)}</dl> : <p>Loading system status...</p>}</section></div>;
}
