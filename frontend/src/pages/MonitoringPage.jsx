import React from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from 'recharts';
import { Activity, ShieldAlert, Sparkles, RefreshCw } from 'lucide-react';

// PSI data timeline
const driftPsiData = [
  { day: 'Day 1', PSI: 0.05, Threshold: 0.20 },
  { day: 'Day 5', PSI: 0.08, Threshold: 0.20 },
  { day: 'Day 10', PSI: 0.12, Threshold: 0.20 },
  { day: 'Day 15', PSI: 0.14, Threshold: 0.20 },
  { day: 'Day 20', PSI: 0.18, Threshold: 0.20 },
  { day: 'Day 25', PSI: 0.22, Threshold: 0.20 },
  { day: 'Day 30', PSI: 0.24, Threshold: 0.20 },
];

// F1 Score production decay
const f1DecayData = [
  { day: 'Day 1', Baseline: 0.913, Production: 0.913 },
  { day: 'Day 5', Baseline: 0.913, Production: 0.912 },
  { day: 'Day 10', Baseline: 0.913, Production: 0.908 },
  { day: 'Day 15', Baseline: 0.913, Production: 0.905 },
  { day: 'Day 20', Baseline: 0.913, Production: 0.897 },
  { day: 'Day 25', Baseline: 0.913, Production: 0.888 },
  { day: 'Day 30', Baseline: 0.913, Production: 0.882 },
];

export default function MonitoringPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  const isDrift = project.monitoring?.driftStatus === 'DRIFT DETECTED';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Model Monitoring & Drift</h1>
          <p className="text-sm text-zinc-400">Track population stability indexes and decay stats in production.</p>
        </div>

        {isDrift && (
          <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm font-semibold animate-pulse">
            <ShieldAlert className="w-4.5 h-4.5" />
            <span>Drift Warnings Active</span>
          </div>
        )}
      </div>

      {/* Overview stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border">
          <span className="text-[10px] text-zinc-500 font-mono uppercase">Telemetry status</span>
          <h3 className={`text-xl font-bold font-mono mt-1 ${isDrift ? 'text-red-400' : 'text-emerald-400'}`}>
            {project.monitoring?.driftStatus}
          </h3>
        </div>
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border">
          <span className="text-[10px] text-zinc-500 font-mono uppercase">Max PSI observed</span>
          <h3 className="text-xl font-bold font-mono text-zinc-200 mt-1">{project.monitoring?.driftPsi}</h3>
        </div>
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border">
          <span className="text-[10px] text-zinc-500 font-mono uppercase">PSI Alert Threshold</span>
          <h3 className="text-xl font-bold font-mono text-zinc-200 mt-1">0.20</h3>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Chart 1: Data Drift PSI Timeline */}
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
          <div>
            <h3 className="font-semibold text-zinc-200 text-sm">Data Drift (PSI Timeline)</h3>
            <p className="text-xs text-zinc-500 font-mono">Population Stability Index over last 30 days</p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={driftPsiData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorPsi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="day" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} fontClassName="font-mono" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                  labelStyle={{ color: '#ef4444', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="PSI" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#colorPsi)" />
                <Area type="monotone" dataKey="Threshold" stroke="#71717a" strokeWidth={1} strokeDasharray="4 4" fill="none" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Performance decay */}
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
          <div>
            <h3 className="font-semibold text-zinc-200 text-sm">Model Performance Decay Timeline</h3>
            <p className="text-xs text-zinc-500 font-mono">Production F1 metric vs. validation baseline</p>
          </div>

          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={f1DecayData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                <XAxis dataKey="day" stroke="#71717a" fontSize={11} />
                <YAxis stroke="#71717a" fontSize={11} domain={[0.8, 1]} fontClassName="font-mono" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                  labelStyle={{ color: '#a78bfa', fontWeight: 'bold' }}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Line type="monotone" dataKey="Production" stroke="#7c3aed" strokeWidth={2.5} activeDot={{ r: 6 }} />
                <Line type="monotone" dataKey="Baseline" stroke="#71717a" strokeWidth={1.5} strokeDasharray="5 5" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Alerts Log Panel */}
      {isDrift && (
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
          <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-brand-primary" />
            Active Drift Warnings Log
          </h3>

          <div className="space-y-3">
            {project.monitoring?.driftAlerts?.map((alert) => (
              <div 
                key={alert.id} 
                className="bg-brand-dark-bg/60 border border-brand-dark-border/40 p-4 rounded-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-3"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500"></span>
                    <strong className="text-xs uppercase font-mono tracking-wider text-red-400">
                      {alert.severity} Alert
                    </strong>
                    <span className="text-[10px] text-zinc-500 font-mono">{alert.time}</span>
                  </div>
                  <p className="text-sm font-semibold text-zinc-200 mt-1.5">{alert.message}</p>
                </div>
                
                <button
                  onClick={() => alert('Dispatched retraining job to Kafka workers queue.')}
                  className="bg-violet-500/10 hover:bg-violet-500/20 border border-violet-500/30 text-violet-300 text-xs font-bold px-3 py-1.5 rounded-lg transition-all cursor-pointer flex items-center gap-1.5"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  Retrain Model
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
