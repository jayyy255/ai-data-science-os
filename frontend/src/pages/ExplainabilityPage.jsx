import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Eye, Search, Sparkles, UserCheck, AlertTriangle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function ExplainabilityPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  const [explainTab, setExplainTab] = useState('global');
  const [searchId, setSearchId] = useState('US-8594-QD');

  // Custom colors for SHAP: violet for positive (pushing churn up), zinc for negative (reducing churn)
  const getShapColor = (val) => (val > 0 ? '#7c3aed' : '#71717a');

  // Formatted data for Recharts global SHAP Summary
  const globalShapData = project.shapGlobal?.map(d => ({
    name: d.feature,
    value: d.shap,
    type: d.type
  })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white tracking-tight">Explainability Engine (SHAP)</h1>
        <p className="text-sm text-zinc-400">Interpret global feature impact and local inference predictions in real-time.</p>
      </div>

      {/* Segmented control */}
      <div className="flex border-b border-brand-dark-border/40 gap-6">
        <button
          onClick={() => setExplainTab('global')}
          className={`pb-2.5 text-sm font-semibold transition-all ${
            explainTab === 'global' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Global Feature Importance
        </button>
        <button
          onClick={() => setExplainTab('local')}
          className={`pb-2.5 text-sm font-semibold transition-all ${
            explainTab === 'local' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Local Explanation (Instance Lookup)
        </button>
      </div>

      {/* Global explanations */}
      {explainTab === 'global' && (
        <div className="space-y-6">
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <div>
              <h3 className="font-semibold text-zinc-200 text-sm">SHAP Summary Plot (Global Feature Importance)</h3>
              <p className="text-xs text-zinc-500 font-mono">Mean absolute SHAP value impact on target output</p>
            </div>

            <div className="h-96 w-full max-w-3xl">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={globalShapData}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#71717a" fontSize={11} fontClassName="font-mono" />
                  <YAxis dataKey="name" type="category" stroke="#71717a" fontSize={11} width={120} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                    labelStyle={{ color: '#a78bfa', fontWeight: 'bold' }}
                  />
                  <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                    {globalShapData.map((entry, idx) => (
                      <Cell key={`cell-${idx}`} fill={getShapColor(entry.value)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            
            <div className="flex justify-start text-[10px] font-mono text-zinc-500 gap-6 pl-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-brand-primary rounded"></span>
                Positive Impact (Increases Churn Probability)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-zinc-600 rounded"></span>
                Negative Impact (Decreases Churn Probability)
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Local explanations lookup */}
      {explainTab === 'local' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Lookup parameters card */}
            <div className="lg:col-span-1 bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-semibold text-zinc-200">Select Instance ID</h3>
              
              <div className="relative">
                <Search className="absolute left-3 top-3 w-4 h-4 text-zinc-500" />
                <input
                  type="text"
                  value={searchId}
                  onChange={(e) => setSearchId(e.target.value)}
                  className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 pl-9 pr-4 rounded-xl text-sm font-medium transition-all"
                  placeholder="US-8594-QD"
                />
              </div>

              <div className="bg-brand-dark-bg/60 p-4 rounded-xl border border-brand-dark-border/40 text-center space-y-1">
                <span className="text-[10px] text-zinc-500 font-mono uppercase">Predicted Probability</span>
                <h4 className="text-3xl font-bold font-mono text-red-400">
                  {(project.shapLocal?.probability * 100).toFixed(1)}%
                </h4>
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full mt-2">
                  {project.shapLocal?.risk}
                </span>
              </div>
            </div>

            {/* Drivers list waterfall panel */}
            <div className="lg:col-span-2 bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand-primary" />
                Inference Drivers Summary
              </h3>

              <div className="space-y-4">
                <p className="text-sm text-zinc-400">
                  Customer churn prediction is heavily driven by:
                </p>

                <div className="space-y-2.5">
                  {project.shapLocal?.drivers?.map((dr, idx) => (
                    <div key={idx} className="flex items-center justify-between bg-brand-dark-bg/40 p-3 rounded-xl border border-brand-dark-border/20">
                      <div className="flex items-center gap-2.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-brand-primary"></span>
                        <div>
                          <p className="text-xs font-mono text-zinc-500 uppercase">{dr.feature}</p>
                          <p className="text-sm font-semibold text-zinc-200">{dr.value}</p>
                        </div>
                      </div>
                      <span className="text-sm font-bold font-mono text-red-400">{dr.impact}</span>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-2 bg-brand-dark-bg/60 border border-brand-dark-border/40 p-3.5 rounded-xl">
                  <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />
                  <p className="text-xs text-zinc-400 leading-relaxed">
                    Recommendation: High probability of churn is linked with the support call count override and new customer billing cycles. Retaining customer requires contract restructuring incentives.
                  </p>
                </div>
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
