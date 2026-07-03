import React from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { LayoutGrid, AlertTriangle, CheckCircle, BarChart3, Database, ShieldAlert, Sparkles } from 'lucide-react';

export default function DatasetIntelligencePage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  const struct = project.structure || { numerical: 0, categorical: 0, datetime: 0, text: 0 };
  const health = project.qualityHealth || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white tracking-tight">Dataset Intelligence</h1>
        <p className="text-sm text-zinc-400">Structural schema analysis and quality profiling logged in PostgreSQL.</p>
      </div>

      {/* Structure Grid */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider font-mono">Dataset Structure</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
            <span className="text-[10px] text-zinc-500 font-mono uppercase">Numerical Columns</span>
            <h4 className="text-2xl font-bold font-mono text-violet-300 mt-1">{struct.numerical}</h4>
            <span className="text-[10px] text-zinc-500 block mt-1">e.g. tenure, MonthlyCharges</span>
          </div>
          <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
            <span className="text-[10px] text-zinc-500 font-mono uppercase">Categorical Columns</span>
            <h4 className="text-2xl font-bold font-mono text-indigo-300 mt-1">{struct.categorical}</h4>
            <span className="text-[10px] text-zinc-500 block mt-1">e.g. contract, payment_method</span>
          </div>
          <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
            <span className="text-[10px] text-zinc-500 font-mono uppercase">Datetime Columns</span>
            <h4 className="text-2xl font-bold font-mono text-zinc-400 mt-1">{struct.datetime}</h4>
            <span className="text-[10px] text-zinc-500 block mt-1">e.g. signup_date</span>
          </div>
          <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
            <span className="text-[10px] text-zinc-500 font-mono uppercase">Text Columns</span>
            <h4 className="text-2xl font-bold font-mono text-zinc-400 mt-1">{struct.text}</h4>
            <span className="text-[10px] text-zinc-500 block mt-1">e.g. customer_feedback</span>
          </div>
        </div>
      </div>

      {/* Quality Profile Cards */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider font-mono">Dataset Quality Health</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-4 flex gap-3.5 items-start">
            <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 p-2 rounded-lg">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono uppercase text-zinc-500">Missing Values</span>
              <p className="text-sm font-semibold text-zinc-200 mt-0.5">{health.missingValues}</p>
              <p className="text-xs text-zinc-500 mt-1">Requires imputation during Feature Preprocessing</p>
            </div>
          </div>

          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-4 flex gap-3.5 items-start">
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-2 rounded-lg">
              <CheckCircle className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono uppercase text-zinc-500">Duplicate Check</span>
              <p className="text-sm font-semibold text-zinc-200 mt-0.5">{health.duplicates}</p>
              <p className="text-xs text-zinc-500 mt-1">No index cleaning required</p>
            </div>
          </div>

          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-4 flex gap-3.5 items-start">
            <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 p-2 rounded-lg">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono uppercase text-zinc-500">Outlier Detection</span>
              <p className="text-sm font-semibold text-zinc-200 mt-0.5">{health.outliers}</p>
              <p className="text-xs text-zinc-500 mt-1">Identified via Z-score metric threshold &gt; 3</p>
            </div>
          </div>

          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-4 flex gap-3.5 items-start md:col-span-2 lg:col-span-1">
            <div className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 p-2 rounded-lg">
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono uppercase text-zinc-500">Class Balance</span>
              <p className="text-sm font-semibold text-zinc-200 mt-0.5">{health.classImbalance}</p>
              <p className="text-xs text-zinc-500 mt-1">SMOTE oversampling config will apply in Kafka training</p>
            </div>
          </div>
        </div>
      </div>

      {/* Feature Details Table */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-300 uppercase tracking-wider font-mono">Feature Schema Registry</h3>
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-brand-dark-bg/60 border-b border-brand-dark-border text-zinc-400 font-mono text-xs">
                <tr>
                  <th className="p-4">Feature Name</th>
                  <th className="p-4">Data Type</th>
                  <th className="p-4 text-center">Missing %</th>
                  <th className="p-4 text-center">Unique Counts</th>
                  <th className="p-4">Sample Value</th>
                  <th className="p-4">Pre-Engineering Quality</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-dark-border/40 text-zinc-300">
                {project.features?.map((feat, i) => (
                  <tr key={i} className="hover:bg-brand-dark-card/40 transition-colors">
                    <td className="p-4 font-semibold text-zinc-100 font-mono">{feat.name}</td>
                    <td className="p-4 font-mono text-xs text-violet-300">{feat.type}</td>
                    <td className={`p-4 text-center font-mono font-bold ${feat.missing > 0 ? 'text-amber-400' : 'text-zinc-500'}`}>
                      {feat.missing}%
                    </td>
                    <td className="p-4 text-center font-mono">{feat.unique?.toLocaleString()}</td>
                    <td className="p-4 text-zinc-400 font-mono text-xs truncate max-w-xs">{feat.sample}</td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
                        feat.quality?.includes('Imputed') || feat.quality?.includes('Overridden')
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : feat.quality === 'Target'
                            ? 'bg-violet-500/15 text-violet-300 border border-violet-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {feat.quality}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
