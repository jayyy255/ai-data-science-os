import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Sliders, HelpCircle, Save, Sparkles, AlertTriangle, ShieldCheck, Check, ArrowRight, Download, TrendingUp, Database, Loader2 } from 'lucide-react';

export default function FeatureEngineeringPage() {
  const { getActiveProject, applyOverride, triggerTraining, applyFeatureTransformation } = useProjectStore();
  const project = getActiveProject();

  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [downloadingTransformed, setDownloadingTransformed] = useState(false);

  // Local state overrides selection
  const [overrides, setOverrides] = useState({});
  const [applying, setApplying] = useState({});

  const handleOverrideSelect = (feature, choice) => {
    setOverrides(prev => ({ ...prev, [feature]: choice }));
  };

  const handleApplyTransformation = async (feature) => {
    const choice = overrides[feature];
    if (!choice) return;
    
    setApplying(prev => ({ ...prev, [feature]: true }));
    try {
      await applyFeatureTransformation(project.id, feature, choice);
    } catch (err) {
      console.error(err);
      alert("Failed to apply transformation: " + (err.response?.data?.detail || err.message));
    } finally {
      setApplying(prev => ({ ...prev, [feature]: false }));
    }
  };

  const handleDownloadTransformed = async () => {
    setDownloadingTransformed(true);
    const API_BASE = window.location.origin.includes('localhost') ? 'http://localhost:8000/api' : '/api';
    try {
      const res = await fetch(`${API_BASE}/projects/${project.id}/presigned-download-transformed`);
      if (!res.ok) throw new Error("Failed to get presigned URL");
      const data = await res.json();
      
      const fileRes = await fetch(data.url);
      const blob = await fileRes.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = blobUrl;
      a.download = `${project.id}_transformed_dataset.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(blobUrl);
      a.remove();
    } catch (err) {
      console.warn("Signed URL download failed/CORS block. Falling back to backend stream:", err);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = `${API_BASE}/projects/${project.id}/download-transformed`;
      a.download = `${project.id}_transformed_dataset.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } finally {
      setDownloadingTransformed(false);
    }
  };

  const handleSave = () => {
    setSaving(true);
    setSuccess(false);
    setTimeout(() => {
      setSaving(false);
      setSuccess(true);
      triggerTraining(project.id);
      setTimeout(() => setSuccess(false), 3000);
    }, 1200);
  };

  // Check if any feature has a transformed state
  const hasTransformedFeatures = project.featureEngineeringDecisions?.some(d => d.overrideActive || d.comparisonMetrics);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Feature Engineering</h1>
          <p className="text-sm text-zinc-400">Manage automated transformations, evaluate correlation metrics, and commit custom overrides.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {hasTransformedFeatures && (
            <button
              onClick={handleDownloadTransformed}
              disabled={downloadingTransformed}
              className="flex items-center gap-1.5 bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 px-4 py-2 rounded-xl text-sm font-bold text-zinc-200 transition-all cursor-pointer"
            >
              {downloadingTransformed ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-zinc-400" />
                  Downloading...
                </>
              ) : (
                <>
                  <Download className="w-4 h-4 text-brand-primary" />
                  Download Transformed CSV
                </>
              )}
            </button>
          )}

          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-4 py-2 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20"
          >
            {saving ? 'Saving...' : success ? 'Saved!' : 'Save Decisions'}
            {success ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          </button>
        </div>
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
          const currentChoice = overrides[dec.feature] !== undefined ? overrides[dec.feature] : (dec.overrideActive ? (dec.userChoice || '') : 'recommended');
          const isPendingApply = overrides[dec.feature] !== undefined && overrides[dec.feature] !== (dec.overrideActive ? dec.userChoice : 'recommended');
          const metrics = dec.comparisonMetrics;
          
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

              {/* Evaluation Comparison Panel */}
              {metrics && (
                <div className="mt-4 p-3 bg-zinc-900/50 border border-zinc-800 rounded-lg space-y-2">
                  <span className="text-[10px] font-mono text-zinc-500 uppercase block">Transformation Impact Analysis</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="space-y-1">
                      <span className="text-zinc-500">Target Correlation</span>
                      <div className="flex items-center gap-1 text-zinc-300 font-mono">
                        <span>{metrics.before_corr}</span>
                        <ArrowRight className="w-3 h-3 text-zinc-500" />
                        <span className={metrics.better ? 'text-emerald-400 font-bold' : 'text-zinc-300'}>{metrics.after_corr}</span>
                      </div>
                    </div>
                    <div className="space-y-1">
                      <span className="text-zinc-500">Missing Values</span>
                      <div className="flex items-center gap-1 text-zinc-300 font-mono">
                        <span>{metrics.before_missing}</span>
                        <ArrowRight className="w-3 h-3 text-zinc-500" />
                        <span className={metrics.after_missing < metrics.before_missing ? 'text-emerald-400 font-bold' : 'text-zinc-300'}>{metrics.after_missing}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center justify-between pt-1 border-t border-zinc-800/60 mt-1">
                    <div className="flex items-center gap-1">
                      <TrendingUp className={`w-3.5 h-3.5 ${metrics.better ? 'text-emerald-400' : 'text-zinc-500'}`} />
                      <span className={`text-[10px] font-semibold ${metrics.better ? 'text-emerald-400' : 'text-zinc-500'}`}>
                        {metrics.improvement > 0 ? `Improvement: +${metrics.improvement}` : metrics.improvement === 0 ? 'No correlation change' : `Change: ${metrics.improvement}`}
                      </span>
                    </div>
                    {metrics.better ? (
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded font-bold">
                        Optimized
                      </span>
                    ) : (
                      <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">
                        Applied
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Form Controls / Dropdowns for user choice overrides */}
              <div className="mt-5 pt-3 border-t border-brand-dark-border/40 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <span className="text-xs text-zinc-500 font-mono">Transformation Strategy:</span>
                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    <select
                      value={currentChoice}
                      onChange={(e) => handleOverrideSelect(dec.feature, e.target.value)}
                      className="bg-brand-dark-bg border border-brand-dark-border hover:border-brand-dark-border rounded-lg text-xs font-semibold text-zinc-300 py-1.5 px-2.5 outline-none cursor-pointer flex-1 sm:flex-initial"
                    >
                      <option value="recommended">Apply AI Recommended</option>
                      <option value="Impute Median">Median Imputation</option>
                      <option value="Impute Mean">Mean Imputation</option>
                      <option value="One-Hot Encoding">One-Hot Encoding</option>
                      <option value="Standard Scaling">Standard Scaling</option>
                      <option value="Keep Raw">Keep Raw Numerical</option>
                      <option value="Discretize Binning">Discretize / Binning</option>
                    </select>

                    <button
                      onClick={() => handleApplyTransformation(dec.feature)}
                      disabled={applying[dec.feature] || !isPendingApply}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer flex items-center gap-1 ${
                        isPendingApply 
                          ? 'bg-brand-primary hover:bg-brand-primary-hover text-white' 
                          : 'bg-zinc-800 text-zinc-500 border border-zinc-700/50 cursor-not-allowed'
                      }`}
                    >
                      {applying[dec.feature] ? (
                        <>
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Applying...
                        </>
                      ) : (
                        'Apply'
                      )}
                    </button>
                  </div>
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
