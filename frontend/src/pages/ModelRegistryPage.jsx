import React from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Archive, ArrowUp, ArrowDown, Download, ExternalLink, HardDrive } from 'lucide-react';

export default function ModelRegistryPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  // Mock registry versions
  const registryVersions = [
    {
      version: 'v3',
      algorithm: 'XGBoost',
      status: 'Production',
      f1: 0.913,
      path: 's3://models/customer-churn/v3.bin',
      created: '2 hours ago',
      metrics: { accuracy: '89.2%', logloss: '0.23' }
    },
    {
      version: 'v4',
      algorithm: 'LightGBM',
      status: 'Staging',
      f1: 0.902,
      path: 's3://models/customer-churn/v4.bin',
      created: '1 day ago',
      metrics: { accuracy: '88.5%', logloss: '0.26' }
    },
    {
      version: 'v2',
      algorithm: 'Random Forest',
      status: 'Archived',
      f1: 0.865,
      path: 's3://models/customer-churn/v2.bin',
      created: '1 week ago',
      metrics: { accuracy: '85.4%', logloss: '0.34' }
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white tracking-tight">Model Registry</h1>
        <p className="text-sm text-zinc-400">Manage trained binaries, MLflow runs, and production deployment targets.</p>
      </div>

      {/* Deployment summary widgets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex items-start gap-4">
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-2.5 rounded-xl">
            <Archive className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-zinc-500 font-mono uppercase block">Active Production Champion</span>
            <h4 className="text-lg font-bold text-zinc-100 mt-1">v3 (XGBoost Classifier)</h4>
            <p className="text-xs text-zinc-500 mt-1 font-mono">F1-Score: 0.913 \| Logged: 2 hours ago</p>
          </div>
        </div>

        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex items-start gap-4">
          <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 p-2.5 rounded-xl">
            <Archive className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-zinc-500 font-mono uppercase block">Staging Candidate</span>
            <h4 className="text-lg font-bold text-zinc-100 mt-1">v4 (LightGBM Classifier)</h4>
            <p className="text-xs text-zinc-500 mt-1 font-mono">F1-Score: 0.902 \| Logged: 1 day ago</p>
          </div>
        </div>

      </div>

      {/* Versions Table */}
      <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-brand-dark-bg/60 border-b border-brand-dark-border text-zinc-400 font-mono text-xs">
              <tr>
                <th className="p-4">Model Version</th>
                <th className="p-4">Algorithm</th>
                <th className="p-4">Deployment Status</th>
                <th className="p-4 text-center">F1 Validation</th>
                <th className="p-4 text-center">Accuracy</th>
                <th className="p-4">MinIO S3 Binary Storage</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-dark-border/40 text-zinc-300">
              {registryVersions.map((reg, idx) => {
                const isProduction = reg.status === 'Production';
                const isStaging = reg.status === 'Staging';
                return (
                  <tr key={idx} className="hover:bg-brand-dark-card/40 transition-colors">
                    <td className="p-4 font-semibold text-zinc-100 font-mono">{reg.version}</td>
                    <td className="p-4 font-semibold text-zinc-300">{reg.algorithm}</td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full ${
                        isProduction 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                          : isStaging 
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                            : 'bg-zinc-800 text-zinc-500 border border-brand-dark-border'
                      }`}>
                        {reg.status}
                      </span>
                    </td>
                    <td className="p-4 text-center font-mono font-bold text-violet-300">{reg.f1}</td>
                    <td className="p-4 text-center font-mono text-zinc-400">{reg.metrics.accuracy}</td>
                    <td className="p-4 font-mono text-xs text-zinc-500">
                      <div className="flex items-center gap-1.5">
                        <HardDrive className="w-3.5 h-3.5 text-zinc-600" />
                        <span className="truncate max-w-[160px]">{reg.path}</span>
                      </div>
                    </td>
                    <td className="p-4 text-right">
                      <div className="inline-flex gap-2">
                        {isStaging && (
                          <button 
                            className="bg-brand-primary hover:bg-brand-primary-hover p-1.5 rounded-lg text-white transition-all cursor-pointer"
                            title="Promote to Production"
                          >
                            <ArrowUp className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {isProduction && (
                          <button 
                            className="bg-zinc-800 hover:bg-zinc-700 p-1.5 rounded-lg text-zinc-400 border border-brand-dark-border hover:text-zinc-200 transition-all cursor-pointer"
                            title="Demote to Staging"
                          >
                            <ArrowDown className="w-3.5 h-3.5" />
                          </button>
                        )}
                        <button
                          onClick={() => {
                            alert(`Downloading Model Binary: ${reg.version}`);
                          }}
                          className="bg-zinc-800 hover:bg-zinc-700 p-1.5 rounded-lg text-zinc-400 border border-brand-dark-border hover:text-zinc-200 transition-all cursor-pointer"
                          title="Download .bin from MinIO"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            alert(`Launching MLflow Run UI`);
                          }}
                          className="bg-zinc-800 hover:bg-zinc-700 p-1.5 rounded-lg text-zinc-400 border border-brand-dark-border hover:text-zinc-200 transition-all cursor-pointer"
                          title="View MLflow Logs"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
