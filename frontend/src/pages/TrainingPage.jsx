import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Cpu, RefreshCw, Layers, CheckCircle2, Server, Play, HelpCircle, Activity, Sparkles } from 'lucide-react';

export default function TrainingPage() {
  const { getActiveProject, triggerTraining, fetchProjectDetails } = useProjectStore();
  const project = getActiveProject();

  const [activeTab, setActiveTab] = useState('pipeline');
  const isTraining = project.status === 'Training';

  useEffect(() => {
    if (isTraining) {
      const interval = setInterval(() => {
        fetchProjectDetails(project.id);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isTraining, project.id, fetchProjectDetails]);

  const handleStartTraining = () => {
    triggerTraining(project.id);
  };

  // Get dynamic model comparison status from DB, or default fallbacks
  const models = project.modelsComparison || {
    'XGBoost': { status: 'Idle', metric: null },
    'LightGBM': { status: 'Idle', metric: null },
    'Random Forest': { status: 'Idle', metric: null },
    'Neural Network': { status: 'Idle', metric: null },
    'Tabular Transformer': { status: 'Idle', metric: null }
  };

  const getMetricLabel = () => {
    return project.problemType === 'classification' ? 'F1 Validation Score' : 'MSE Validation Loss';
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Model Training & HPO</h1>
          <p className="text-sm text-zinc-400">Asynchronous Kafka training pipeline and Optuna HPO optimization.</p>
        </div>
        
        {!isTraining ? (
          <button
            onClick={handleStartTraining}
            className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-4 py-2 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20 animate-pulse"
          >
            <Play className="w-4 h-4 fill-white" />
            Start Training Job
          </button>
        ) : (
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 px-4 py-2 rounded-xl text-sm font-semibold">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Optuna Searching & Comparing...
          </div>
        )}
      </div>

      {/* Selector Tabs */}
      <div className="flex border-b border-brand-dark-border/40 gap-6">
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'pipeline' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Kafka Live Node Graph
        </button>
        <button
          onClick={() => setActiveTab('trials')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'trials' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Optuna HPO Trials
        </button>
      </div>

      {/* Tab 1: Live Kafka Node Graph */}
      {activeTab === 'pipeline' && (
        <div className="space-y-6">
          {/* Animated SVG Node Graph */}
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-6 relative overflow-hidden">
            
            {/* Legend indicators */}
            <div className="absolute top-4 right-4 flex items-center gap-3 text-[10px] font-mono text-zinc-500 bg-brand-dark-bg/60 border border-brand-dark-border/30 px-2.5 py-1.5 rounded-lg z-10">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-brand-primary animate-pulse"></span>
                Active Queue Flow
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                Completed
              </span>
            </div>

            <div className="space-y-2 mb-4">
              <h3 className="font-semibold text-zinc-200 text-sm">Live Kafka Pipeline Telemetry</h3>
              <p className="text-xs text-zinc-500 font-mono">Real-time message routing across parallel workers</p>
            </div>

            {/* Interactive SVG Node Diagram */}
            <div className="w-full flex items-center justify-center p-4 bg-brand-dark-bg/40 rounded-xl border border-brand-dark-border/20 min-h-[300px]">
              <svg viewBox="0 0 800 240" className="w-full max-w-3xl overflow-visible">
                {/* Node connections lines */}
                <path d="M 120 120 L 250 120" stroke="#7c3aed" strokeWidth="2" strokeDasharray="6 4" className="animate-[dash_10s_linear_infinite]" />
                
                {/* Worker 1 active line */}
                <path d="M 330 120 L 460 70" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="2" strokeDasharray="6 4" className={isTraining ? "animate-[dash_8s_linear_infinite]" : ""} />
                
                {/* Worker 2 active line (Now Animated during training!) */}
                <path d="M 330 120 L 460 170" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="2" strokeDasharray="6 4" className={isTraining ? "animate-[dash_8s_linear_infinite]" : ""} />
                
                {/* Outgoing Worker lines */}
                <path d="M 540 70 L 670 120" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="2" strokeDasharray="6 4" className={isTraining ? "animate-[dash_8s_linear_infinite]" : ""} />
                <path d="M 540 170 L 670 120" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="2" strokeDasharray="6 4" className={isTraining ? "animate-[dash_8s_linear_infinite]" : ""} />

                {/* Node 1: Request */}
                <g transform="translate(40, 80)">
                  <rect width="80" height="80" rx="12" fill="#18181b" stroke="#3f3f46" strokeWidth="1.5" />
                  <circle cx="40" cy="30" r="14" fill="#7c3aed" fillOpacity="0.1" stroke="#7c3aed" strokeWidth="1.5" />
                  <path d="M 36 30 L 44 30 M 40 26 L 40 34" stroke="#c084fc" strokeWidth="2" strokeLinecap="round" />
                  <text x="40" y="62" fill="#a1a1aa" fontSize="10" textAnchor="middle" fontWeight="bold">Request</text>
                  <text x="40" y="73" fill="#34d399" fontSize="8" textAnchor="middle" fontFamily="monospace">Complete</text>
                </g>

                {/* Node 2: Kafka Broker */}
                <g transform="translate(250, 80)">
                  <rect width="80" height="80" rx="12" fill="#18181b" stroke="#7c3aed" strokeWidth="1.5" className="animate-pulse" />
                  <circle cx="40" cy="30" r="14" fill="#7c3aed" fillOpacity="0.1" stroke="#7c3aed" strokeWidth="1.5" />
                  <path d="M 32 30 A 8 8 0 0 1 48 30" stroke="#c084fc" strokeWidth="1.5" fill="none" />
                  <circle cx="40" cy="30" r="3" fill="#c084fc" />
                  <text x="40" y="62" fill="#a1a1aa" fontSize="10" textAnchor="middle" fontWeight="bold">Kafka Queue</text>
                  <text x="40" y="73" fill="#a78bfa" fontSize="8" textAnchor="middle" fontFamily="monospace">{isTraining ? 'Active (5 tasks)' : 'Idle (0 tasks)'}</text>
                </g>

                {/* Node 3: Worker 1 (XGB/LGB/RF) */}
                <g transform="translate(460, 30)">
                  <rect width="80" height="80" rx="12" fill="#18181b" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="1.5" />
                  <circle cx="40" cy="30" r="14" fill={isTraining ? '#7c3aed' : '#27272a'} fillOpacity="0.1" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="1.5" />
                  <path d="M 35 25 L 45 25 M 35 30 L 45 30 M 35 35 L 45 35" stroke={isTraining ? '#c084fc' : '#71717a'} strokeWidth="1.5" />
                  <text x="40" y="62" fill="#a1a1aa" fontSize="10" textAnchor="middle" fontWeight="bold">Worker 1</text>
                  <text x="40" y="73" fill={isTraining ? '#f59e0b' : '#71717a'} fontSize="8" textAnchor="middle" fontFamily="monospace">
                    {isTraining ? 'ACTIVE (Tree HPO)' : 'IDLE'}
                  </text>
                </g>

                {/* Node 4: Worker 2 (NN/Transformer - Now fully animated!) */}
                <g transform="translate(460, 130)">
                  <rect width="80" height="80" rx="12" fill="#18181b" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="1.5" />
                  <circle cx="40" cy="30" r="14" fill={isTraining ? '#7c3aed' : '#27272a'} fillOpacity="0.1" stroke={isTraining ? '#7c3aed' : '#3f3f46'} strokeWidth="1.5" />
                  <path d="M 35 25 L 45 25 M 35 30 L 45 30 M 35 35 L 45 35" stroke={isTraining ? '#c084fc' : '#71717a'} strokeWidth="1.5" />
                  <text x="40" y="62" fill="#a1a1aa" fontSize="10" textAnchor="middle" fontWeight="bold">Worker 2</text>
                  <text x="40" y="73" fill={isTraining ? '#f59e0b' : '#71717a'} fontSize="8" textAnchor="middle" fontFamily="monospace">
                    {isTraining ? 'ACTIVE (NN/Attn)' : 'IDLE'}
                  </text>
                </g>

                {/* Node 5: Storage (MLflow/PG) */}
                <g transform="translate(670, 80)">
                  <rect width="80" height="80" rx="12" fill="#18181b" stroke="#3f3f46" strokeWidth="1.5" />
                  <circle cx="40" cy="30" r="14" fill="#27272a" stroke="#3f3f46" strokeWidth="1.5" />
                  <path d="M 34 26 L 46 26 M 34 30 L 46 30 M 34 34 L 46 34" stroke="#71717a" strokeWidth="2" />
                  <text x="40" y="62" fill="#a1a1aa" fontSize="10" textAnchor="middle" fontWeight="bold">MLflow State</text>
                  <text x="40" y="73" fill="#34d399" fontSize="8" textAnchor="middle" fontFamily="monospace">Connected</text>
                </g>
              </svg>
            </div>
            
            {/* Inline CSS animation styles for dashboard SVGs */}
            <style dangerouslySetInnerHTML={{__html: `
              @keyframes dash {
                to {
                  stroke-dashoffset: -40;
                }
              }
            `}} />
          </div>

          {/* Model Comparison Benchmark Status Panel */}
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Layers className="w-4.5 h-4.5 text-brand-primary" />
              Multi-Model Training & Benchmark Comparison
            </h3>

            {/* Model Comparison Grid */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {Object.keys(models).map((modelName) => {
                const modelData = models[modelName];
                const isModelTraining = modelData.status === 'Training';
                const isModelTrained = modelData.status === 'Trained';
                
                return (
                  <div key={modelName} className="bg-brand-dark-bg/60 border border-brand-dark-border rounded-xl p-4 space-y-2 relative overflow-hidden">
                    <span className="text-[10px] font-mono text-zinc-500 uppercase block">{modelName}</span>
                    
                    <div className="flex items-center justify-between mt-1">
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                        isModelTrained 
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : isModelTraining 
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
                            : 'bg-zinc-800 text-zinc-500 border border-brand-dark-border'
                      }`}>
                        {modelData.status}
                      </span>
                      {isModelTraining && <RefreshCw className="w-3 h-3 text-amber-400 animate-spin" />}
                    </div>

                    <div className="pt-2">
                      <span className="text-[10px] text-zinc-500 font-mono">{getMetricLabel()}:</span>
                      <p className="text-sm font-bold font-mono text-violet-300">
                        {modelData.metric !== null ? modelData.metric.toFixed(4) : 'N/A'}
                      </p>
                    </div>

                    {/* Progress Bar indicator */}
                    <div className="w-full bg-zinc-800 h-1.5 rounded-full overflow-hidden mt-2">
                      <div 
                        className={`h-full transition-all duration-500 ${isModelTrained ? 'bg-emerald-500 w-full' : isModelTraining ? 'bg-amber-500 w-1/2 animate-pulse' : 'w-0'}`} 
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Metric Comparison Graph Visualisation */}
            <div className="pt-4 border-t border-brand-dark-border/40 space-y-3">
              <h4 className="text-xs font-mono uppercase text-zinc-500">Benchmark Graph View</h4>
              <div className="space-y-2.5">
                {Object.keys(models).map((modelName) => {
                  const modelData = models[modelName];
                  const hasMetric = modelData.metric !== null;
                  
                  // Compute bar width percentage
                  // Standardize: if metric is classification (F1, max=1.0) we map directly. If loss (MSE, smaller is better), we map inverse.
                  let pct = 0;
                  if (hasMetric) {
                    if (project.problemType === 'classification') {
                      pct = modelData.metric * 100;
                    } else {
                      // Regressor: smaller is better, let's normalize against max or arbitrary threshold
                      pct = Math.max(10, 100 - (modelData.metric / 100)); 
                    }
                  }

                  return (
                    <div key={modelName} className="flex items-center gap-3 text-xs">
                      <span className="w-32 font-medium text-zinc-300 truncate">{modelName}</span>
                      <div className="flex-1 bg-brand-dark-bg/60 border border-brand-dark-border h-6 rounded-lg overflow-hidden flex items-center pr-3">
                        <div 
                          style={{ width: `${pct}%` }} 
                          className={`h-full transition-all duration-1000 ${
                            modelName === project.bestModel 
                              ? 'bg-brand-primary' 
                              : 'bg-brand-primary/40'
                          }`}
                        />
                        <span className="ml-3 font-mono font-bold text-[10px] text-zinc-400">
                          {hasMetric ? modelData.metric.toFixed(4) : 'Pending'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Optuna Trials list */}
      {activeTab === 'trials' && (
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-brand-dark-bg/60 border-b border-brand-dark-border text-zinc-400 font-mono text-xs">
                <tr>
                  <th className="p-4">Trial ID</th>
                  <th className="p-4">Hyperparameter Parameters</th>
                  <th className="p-4 text-center">Validation Metric</th>
                  <th className="p-4">Optimization Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-dark-border/40 text-zinc-300">
                {project.hpoTrials?.map((tr, idx) => (
                  <tr key={idx} className="hover:bg-brand-dark-card/40 transition-colors">
                    <td className="p-4 font-semibold text-zinc-100 font-mono">Trial #{tr.trial}</td>
                    <td className="p-4">
                      <code className="text-xs bg-brand-dark-bg border border-brand-dark-border px-2 py-1 rounded text-violet-300 font-mono">
                        {JSON.stringify(tr.params)}
                      </code>
                    </td>
                    <td className="p-4 text-center font-mono font-bold text-emerald-400">
                      {tr.f1 ? tr.f1.toFixed(3) : 'N/A'}
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
                        tr.status.includes('Best')
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : tr.status === 'Running'
                            ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
                            : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20'
                      }`}>
                        {tr.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {project.hpoTrials?.length === 0 && (
                  <tr>
                    <td colSpan={4} className="p-8 text-center text-zinc-500 text-xs font-mono">
                      No HPO trials executed. Start training to optimize and compare models.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
