import React, { useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Archive, ArrowUp, ArrowDown, Download, ExternalLink, HardDrive, RefreshCw } from 'lucide-react';

export default function ModelRegistryPage() {
  const { getActiveProject, fetchProjectDetails } = useProjectStore();
  const project = getActiveProject();

  const isTraining = project.status === 'Training';

  // Poll project details in the background if actively training, to update registry model states in real-time
  useEffect(() => {
    if (isTraining) {
      const interval = setInterval(() => {
        fetchProjectDetails(project.id);
      }, 3000);
      return () => clearInterval(interval);
    }
  }, [isTraining, project.id, fetchProjectDetails]);

  const models = project.modelsComparison || {};
  const hasModel = Object.keys(models).some(k => models[k].status === 'Trained');

  const registryVersions = [];
  
  if (hasModel || isTraining) {
    Object.keys(models).forEach((modelName, index) => {
      const modelData = models[modelName];
      // Display models that are either Training or Trained
      if (modelData.status !== 'Idle') {
        const isChamp = project.bestModel === modelName;
        registryVersions.push({
          version: `v${index + 1}`,
          algorithm: modelName,
          status: modelData.status === 'Trained' 
            ? (isChamp ? 'Production' : 'Staging') 
            : 'Training',
          metricVal: modelData.metric !== null ? modelData.metric.toFixed(4) : 'Pending',
          path: modelData.status === 'Trained'
            ? (isChamp && project.modelPath ? project.modelPath : `s3://aidso-runs/models/${project.id}/${modelName.toLowerCase().replace(" ", "-")}.pkl`)
            : 'Generating...',
          created: modelData.status === 'Trained' ? 'Trained' : 'In HPO...',
          metrics: {
            accuracy: modelData.metric ? `${(modelData.metric * 100).toFixed(1)}%` : 'N/A',
            logloss: 'N/A'
          }
        });
      }
    });
  }

  // Fallback to static mock list if no models have been touched yet
  if (registryVersions.length === 0) {
    registryVersions.push(
      {
        version: 'v3',
        algorithm: 'XGBoost',
        status: 'Production',
        metricVal: '0.9130',
        path: 's3://models/customer-churn/v3.bin',
        created: '2 hours ago',
        metrics: { accuracy: '89.2%', logloss: '0.23' }
      },
      {
        version: 'v4',
        algorithm: 'LightGBM',
        status: 'Staging',
        metricVal: '0.9020',
        path: 's3://models/customer-churn/v4.bin',
        created: '1 day ago',
        metrics: { accuracy: '88.5%', logloss: '0.26' }
      }
    );
  }

  const handleDownload = (reg) => {
    if (reg.status !== 'Training') {
      const API_BASE = window.location.origin.includes('localhost') ? 'http://localhost:8000/api' : '/api';
      window.open(`${API_BASE}/projects/${project.id}/download-model?model_name=${encodeURIComponent(reg.algorithm)}`, '_blank');
    } else {
      alert('This model is currently training.');
    }
  };

  const handleOpenMLflow = () => {
    window.open('http://localhost:5000', '_blank');
  };

  const getMetricHeader = () => {
    return project.problemType === 'classification' ? 'F1 Validation' : 'MSE Validation';
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Model Registry</h1>
          <p className="text-sm text-zinc-400">Manage trained binaries, MLflow runs, and production deployment targets.</p>
        </div>

        {isTraining && (
          <div className="flex items-center gap-2 bg-amber-500/10 border border-amber-500/20 text-amber-400 px-4 py-2 rounded-xl text-sm font-semibold animate-pulse">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Parallel HPO Runs Logging...
          </div>
        )}
      </div>

      {/* Deployment summary widgets */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex items-start gap-4">
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-2.5 rounded-xl">
            <Archive className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-zinc-500 font-mono uppercase block">Active Production Champion</span>
            <h4 className="text-lg font-bold text-zinc-100 mt-1">
              {hasModel && project.status === 'Ready for Deployment' 
                ? `v1 (${project.bestModel})` 
                : 'v3 (XGBoost Classifier)'}
            </h4>
            <p className="text-xs text-zinc-500 mt-1 font-mono">
              Validation Metric: {hasModel && project.status === 'Ready for Deployment' ? project.bestF1?.toFixed(4) : '0.9130'} | Logged: recently
            </p>
          </div>
        </div>

        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex items-start gap-4">
          <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 p-2.5 rounded-xl">
            <Archive className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] text-zinc-500 font-mono uppercase block">Staging Candidate</span>
            <h4 className="text-lg font-bold text-zinc-100 mt-1">
              {hasModel && project.status !== 'Ready for Deployment'
                ? `v1 (${project.bestModel})` 
                : 'v4 (LightGBM Classifier)'}
            </h4>
            <p className="text-xs text-zinc-500 mt-1 font-mono">
              Validation Metric: {hasModel && project.status !== 'Ready for Deployment' ? project.bestF1?.toFixed(4) : '0.9020'} | Logged: recently
            </p>
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
                <th className="p-4 text-center">{getMetricHeader()}</th>
                <th className="p-4 text-center">Accuracy</th>
                <th className="p-4">MinIO S3 Binary Storage</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-brand-dark-border/40 text-zinc-300">
              {registryVersions.map((reg, idx) => {
                const isProduction = reg.status === 'Production';
                const isStaging = reg.status === 'Staging';
                const isModelTraining = reg.status === 'Training';
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
                            : isModelTraining
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse'
                              : 'bg-zinc-800 text-zinc-500 border border-brand-dark-border'
                      }`}>
                        {isModelTraining && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                        {reg.status}
                      </span>
                    </td>
                    <td className="p-4 text-center font-mono font-bold text-violet-300">{reg.metricVal}</td>
                    <td className="p-4 text-center font-mono text-zinc-400">{reg.metrics.accuracy}</td>
                    <td className="p-4 font-mono text-xs text-zinc-500">
                      <div className="flex items-center gap-1.5">
                        <HardDrive className="w-3.5 h-3.5 text-zinc-600" />
                        <span className="truncate max-w-[180px]" title={reg.path}>{reg.path}</span>
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
                          onClick={() => handleDownload(reg)}
                          disabled={isModelTraining}
                          className="bg-zinc-800 hover:bg-zinc-700 p-1.5 rounded-lg text-zinc-400 border border-brand-dark-border hover:text-zinc-200 transition-all cursor-pointer disabled:opacity-55"
                          title="Download trained model binary"
                        >
                          <Download className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={handleOpenMLflow}
                          className="bg-zinc-800 hover:bg-zinc-700 p-1.5 rounded-lg text-zinc-400 border border-brand-dark-border hover:text-zinc-200 transition-all cursor-pointer"
                          title="View run inside MLflow"
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
