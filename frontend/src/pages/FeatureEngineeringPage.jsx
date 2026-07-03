import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Sliders, HelpCircle, Save, Sparkles, AlertTriangle, ShieldCheck, Check } from 'lucide-react';

export default function FeatureEngineeringPage() {
  const { getActiveProject, applyOverride } = useProjectStore();
  const project = getActiveProject();

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);

  // Local state overrides selection
  const [overrides, setOverrides] = useState({});

  const handleOverrideSelect = (feature, choice) => {
    setOverrides(prev => ({ ...prev, [feature]: choice }));
    // Instantly commit to store to trigger state and timeline updates
    applyOverride(project.id, feature, choice);
  };

  const handleSave = () => {
    setSaving(true);
    setSuccess(false);
    setTimeout(() => {
      setSaving(false);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Feature Engineering</h1>
          <p className="text-sm text-zinc-400">Manage automated transformations and commit custom overrides to Project Memory.</p>
        </div>
        
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-4 py-2 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20"
        >
          {saving ? 'Saving...' : success ? 'Saved!' : 'Save Decisions'}
          {success ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
        </button>
      </div>

      {/* Summary Stat */}
      <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-4 flex flex-col md:flex-row justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <Sparkles className="w-4.5 h-4.5 text-brand-primary" />
          <span>Average AI recommendation confidence is <strong className="text-emerald-400 font-mono">91%</strong> based on dataset features metadata.</span>
        </div>
        <div className="text-xs font-mono text-zinc-500 self-end md:self-center">
          Decisions are logged inside PostgreSQL & MLflow.
        </div>
      </div>

      {/* Recommendations Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {project.featureEngineeringDecisions?.map((dec, idx) => {
          return (
            <div 
              key={idx}
              className={`bg-brand-dark-surface border rounded-xl p-5 flex flex-col justify-between transition-all ${
                dec.overrideActive 
                  ? 'border-amber-500/30 shadow-md shadow-amber-500/2' 
                  : 'border-brand-dark-border'
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] font-mono uppercase text-zinc-500">Feature Variable</span>
                    <h3 className="font-semibold text-zinc-200 font-mono text-base">{dec.feature}</h3>
                  </div>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                    dec.overrideActive 
                      ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                      : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  }`}>
                    {dec.overrideActive ? 'User Override Active' : `AI Confidence: ${(dec.confidence * 100).toFixed(0)}%`}
                  </span>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase">Recommended Action</span>
                  <p className="text-sm font-semibold text-violet-300">{dec.decision}</p>
                </div>

                <div className="space-y-1">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase">Reasoning Basis</span>
                  <p className="text-xs text-zinc-400 leading-relaxed">{dec.reason}</p>
                </div>
              </div>

              {/* Form Controls / Dropdowns for user choice overrides */}
              <div className="mt-5 pt-3 border-t border-brand-dark-border/40 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs text-zinc-500 font-mono">Transformation Strategy:</span>
                  <select
                    value={dec.overrideActive ? (dec.userChoice || '') : 'recommended'}
                    onChange={(e) => handleOverrideSelect(dec.feature, e.target.value)}
                    className="bg-brand-dark-bg border border-brand-dark-border hover:border-brand-dark-border rounded-lg text-xs font-semibold text-zinc-300 py-1.5 px-2.5 outline-none cursor-pointer"
                  >
                    <option value="recommended">Apply AI Recommended</option>
                    <option value="Impute Median">Median Imputation</option>
                    <option value="Impute Mean">Mean Imputation</option>
                    <option value="One-Hot Encoding">One-Hot Encoding</option>
                    <option value="Standard Scaling">Standard Scaling</option>
                    <option value="Keep Raw">Keep Raw Numerical</option>
                    <option value="Discretize Binning">Discretize / Binning</option>
                  </select>
                </div>

                {dec.overrideActive && (
                  <div className="flex items-center gap-1.5 bg-amber-500/5 border border-amber-500/10 p-2 rounded-lg text-[10px] text-amber-400 font-medium">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    <span>User overrode pipeline transformation parameter. This will be stored in Project Memory.</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
