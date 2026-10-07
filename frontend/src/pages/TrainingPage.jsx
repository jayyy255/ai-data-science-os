import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Cpu, RefreshCw, Layers, CheckCircle2, Server, Play, HelpCircle, Activity, Sparkles } from 'lucide-react';

export default function TrainingPage() {
  const { getActiveProject, triggerTraining, fetchProjectDetails, fetchProjectJobs, projectJobs } = useProjectStore();
  const project = getActiveProject();

  const [activeTab, setActiveTab] = useState('pipeline');
  const [selectedImputation, setSelectedImputation] = useState('KNN');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isTraining = project.status === 'Training' || isSubmitting;

  useEffect(() => {
    fetchProjectJobs(project.id);
  }, [project.id, fetchProjectJobs]);

  useEffect(() => {
    if (project.status === 'Training') {
      const interval = setInterval(() => {
        fetchProjectDetails(project.id);
        fetchProjectJobs(project.id);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [project.status, project.id, fetchProjectDetails, fetchProjectJobs]);

  const handleStartTraining = async () => {
    setIsSubmitting(true);
    try {
      await triggerTraining(project.id, selectedImputation);
    } catch (e) {
      alert(e.response?.data?.detail || e.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Get dynamic model comparison status from DB, or default fallbacks
  const models = project.modelsComparison || {
    'XGBoost': { status: 'Idle', metric: null },
    'LightGBM': { status: 'Idle', metric: null },
    'Random Forest': { status: 'Idle', metric: null },
    'Neural Network': { status: 'Idle', metric: null },
  };

  const getMetricLabel = () => {
    return project.problemType === 'classification' ? 'Test F1 (weighted)' : 'Test MSE';
  };

  const totalModels = Object.keys(models).length || 1;
  const trainedCount = Object.values(models).filter(m => m.status === 'Trained').length;
  const progressPercent = Math.round((trainedCount / totalModels) * 100);
  const currentTrainingModel = Object.keys(models).find(name => models[name].status === 'Training') || 'Optuna Optimization';

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Model Training & HPO</h1>
          <p className="text-sm text-zinc-400">Asynchronous database queue training pipeline and Optuna HPO optimization.</p>
        </div>
        
        {!isTraining ? (
          <div className="flex items-center gap-3">
            <div className="flex flex-col text-right">
              <span className="text-[10px] text-zinc-500 font-mono font-bold uppercase">Training Dataset</span>
              <select
                value={selectedImputation}
                onChange={(e) => setSelectedImputation(e.target.value)}
                className="bg-brand-dark-surface border border-brand-dark-border rounded-lg px-2.5 py-1.5 text-xs font-semibold text-zinc-300 outline-none focus:border-brand-primary cursor-pointer font-mono"
              >
                <option value="Median">Median Imputation</option>
                <option value="Mean">Mean Imputation</option>
                <option value="Mode">Mode Imputation</option>
                <option value="KNN">KNN Imputation</option>
              </select>
            </div>
            
            <button
              onClick={handleStartTraining}
              className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20"
            >
              <Play className="w-4 h-4 fill-white" />
              Start Training Job
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 px-4 py-2.5 rounded-xl text-sm font-semibold">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Optuna Searching & Comparing...
          </div>
        )}
      </div>

      {/* Real-time Progress Bar */}
      {isTraining && (
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-3">
          <div className="flex justify-between items-center text-xs font-mono">
            <div className="flex items-center gap-2 text-zinc-300">
              <Sparkles className="w-4 h-4 text-amber-400 animate-pulse" />
              <span>Current Task: <strong className="text-violet-300">{currentTrainingModel}</strong></span>
            </div>
            <span className="text-zinc-500 font-bold">{trainedCount} of {totalModels} models completed ({progressPercent}%)</span>
          </div>
          
          <div className="w-full bg-brand-dark-bg h-2.5 rounded-full overflow-hidden border border-brand-dark-border/40">
            <div 
              className="bg-brand-primary h-full transition-all duration-500 shadow-[0_0_8px_rgba(124,58,237,0.5)]"
              style={{ width: `${Math.max(5, progressPercent)}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* Selector Tabs */}
      <div className="flex border-b border-brand-dark-border/40 gap-6">
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'pipeline' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Training Pipeline
        </button>
        <button
          onClick={() => setActiveTab('trials')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'trials' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          HPO Trials
        </button>
      </div>

      {/* Tab 1: Live Database Queue Node Graph */}
      {activeTab === 'pipeline' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {['Uploaded dataset', 'Train / validation / test split', 'Model fitting & comparison', 'Saved inference pipelines'].map((stage, index) => <div key={stage} className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5"><span className="text-violet-400 font-mono">{index+1}</span><p className="mt-2 text-sm">{stage}</p></div>)}
          </div>

          {/* Model Comparison Benchmark Status Panel */}
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Layers className="w-4.5 h-4.5 text-brand-primary" />
              Multi-Model Training & Benchmark Comparison
            </h3>

            {/* Model Comparison Grid */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
                      {tr.f1 != null ? tr.f1.toFixed(3) : 'N/A'}
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

      {/* Past Training Jobs History */}
      <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-sm font-semibold text-zinc-200">HPO & Model Training History</h3>
            <p className="text-xs text-zinc-500 font-mono">Audited history of training jobs executed on this project</p>
          </div>
          <button 
            onClick={() => fetchProjectJobs(project.id)}
            className="text-xs text-brand-primary hover:text-violet-300 font-semibold flex items-center gap-1 cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh History
          </button>
        </div>

        <div className="overflow-x-auto">
          {projectJobs[project.id] && projectJobs[project.id].length > 0 ? (
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-brand-dark-border text-zinc-500 uppercase font-mono">
                  <th className="py-2.5 px-3">Job ID</th>
                  <th className="py-2.5 px-3">Model Type / Configuration</th>
                  <th className="py-2.5 px-3">Imputation</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">{project.problemType === 'regression' ? 'Test MSE' : 'Test F1'}</th>
                  <th className="py-2.5 px-3">Started At</th>
                  <th className="py-2.5 px-3">Completed At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-brand-dark-border/40 text-zinc-300">
                {projectJobs[project.id].map((job) => {
                  const isCompleted = job.status === 'completed';
                  const isFailed = job.status === 'failed';
                  const isRunning = job.status === 'running';
                  
                  return (
                    <tr key={job.id} className="hover:bg-brand-dark-bg/20 font-mono">
                      <td className="py-3 px-3 font-semibold">#{job.id}</td>
                      <td className="py-3 px-3 text-zinc-400 font-semibold">{job.model_type}</td>
                      <td className="py-3 px-3 text-violet-400 font-bold">{job.imputation_method || 'Median'}</td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded-full font-semibold ${
                          isCompleted 
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : isFailed
                              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                              : isRunning
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
                                : 'bg-zinc-800 text-zinc-500 border border-brand-dark-border'
                        }`}>
                          {job.status}{job.metrics_json?.error && <span className="ml-2 text-red-400">{job.metrics_json.error}</span>}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-violet-300 font-bold">
                        {job.metrics_json?.best_metric != null ? job.metrics_json.best_metric.toFixed(4) : 'N/A'}
                      </td>
                      <td className="py-3 px-3 text-zinc-500">
                        {job.started_at ? new Date(job.started_at.endsWith('Z') ? job.started_at : job.started_at + 'Z').toLocaleString() : 'Pending'}
                      </td>
                      <td className="py-3 px-3 text-zinc-500">
                        {job.completed_at ? new Date(job.completed_at.endsWith('Z') ? job.completed_at : job.completed_at + 'Z').toLocaleString() : 'N/A'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-8 text-zinc-500 text-xs">
              No training jobs have been executed yet. Click "Start Training Job" above to launch the first run.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
