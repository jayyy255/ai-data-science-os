import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Eye, Search, Sparkles, UserCheck, AlertTriangle, Info, HelpCircle } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

export default function ExplainabilityPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  const [explainTab, setExplainTab] = useState('global');
  const [searchId, setSearchId] = useState('US-8594-QD');
  
  const isDefaultProject = project.id === 'churn-prediction' || project.id === 'demand-forecasting';

  if (project.status !== 'Ready for Deployment' && !isDefaultProject) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Explainability Engine (SHAP)</h1>
          <p className="text-sm text-zinc-400">Interpret global feature impact and local inference predictions in real-time.</p>
        </div>
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="p-4 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400">
            <Eye className="w-8 h-8 animate-pulse" />
          </div>
          <div className="space-y-1.5 max-w-sm">
            <h3 className="text-zinc-200 font-bold text-base">Explainability Engine is Offline</h3>
            <p className="text-xs text-zinc-500 leading-relaxed">
              SHAP global importance plots and local inference predictions become active once a model is trained and registered for production.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Custom colors for SHAP: violet for positive (pushing target probability up), zinc for negative (reducing target probability)
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

      {/* Simplified Explanation Box */}
      <div className="bg-brand-primary/10 border border-brand-primary/20 rounded-xl p-4 flex gap-3.5 items-start">
        <HelpCircle className="w-5 h-5 text-violet-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="text-sm font-semibold text-violet-200">How to interpret SHAP explanations?</h4>
          <p className="text-xs text-zinc-300 leading-relaxed">
            SHAP (SHapley Additive exPlanations) is a game-theory approach that explains <strong>how much each feature contributes</strong> to the model's final output. 
            Features marked in <span className="text-violet-400 font-bold">purple</span> push the prediction probability <strong>higher</strong> (e.g. increasing churn probability), while features in <span className="text-zinc-400 font-bold">gray</span> push the probability <strong>lower</strong> (e.g. retaining the customer).
          </p>
        </div>
      </div>

      {/* Segmented control */}
      <div className="flex border-b border-brand-dark-border/40 gap-6">
        <button
          onClick={() => setExplainTab('global')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            explainTab === 'global' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Global Feature Importance (Overall Model Drivers)
        </button>
        <button
          onClick={() => setExplainTab('local')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            explainTab === 'local' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Local Explanation (Individual Customer Lookup)
        </button>
      </div>

      {/* Global explanations */}
      {explainTab === 'global' && (
        <div className="space-y-6">
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <div>
              <h3 className="font-semibold text-zinc-200 text-sm">SHAP Global Importance Plot</h3>
              <p className="text-xs text-zinc-500 font-mono">Mean absolute SHAP value impact across all dataset records</p>
            </div>

            <div className="h-96 w-full max-w-3xl">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={globalShapData}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
                  <XAxis type="number" stroke="#71717a" fontSize={11} />
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
            
            <div className="flex flex-col sm:flex-row justify-start text-[10px] font-mono text-zinc-500 gap-4 sm:gap-6 pl-4 border-t border-brand-dark-border/40 pt-4">
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-brand-primary rounded"></span>
                Positive Impact (Increases prediction score or Churn likelihood)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 bg-zinc-600 rounded"></span>
                Negative Impact (Decreases prediction score or Churn likelihood)
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
              <div>
                <h3 className="font-semibold text-zinc-200 text-sm">Select Target Instance</h3>
                <p className="text-xs text-zinc-500 font-mono mt-0.5">Lookup specific customer prediction drivers</p>
              </div>
              
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
                <span className="text-[10px] text-zinc-500 font-mono uppercase block">Model Prediction Output</span>
                <span className="text-[9px] text-zinc-400 font-mono block">Probability of target variable being positive</span>
                <h4 className="text-3xl font-bold font-mono text-red-400 mt-1">
                  {(project.shapLocal?.probability * 100).toFixed(1)}%
                </h4>
                <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-red-400 bg-red-500/10 border border-red-500/20 px-2 py-0.5 rounded-full mt-2">
                  {project.shapLocal?.risk}
                </span>
              </div>
            </div>

            {/* Drivers list waterfall panel */}
            <div className="lg:col-span-2 bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-brand-primary" />
                  Individual Inference Drivers
                </h3>
                <p className="text-xs text-zinc-500 font-mono mt-0.5">Top attributes contributing to this prediction</p>
              </div>

              <div className="space-y-4">
                <p className="text-xs text-zinc-400">
                  This customer's high risk score is primarily driven by the following factors:
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
                    <strong>Remediation Suggestion:</strong> High probability of churn is linked with the support call count override and new customer billing cycles. Retaining customer requires contract restructuring incentives.
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
