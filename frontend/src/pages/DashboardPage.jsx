import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useProjectStore } from '../store/useProjectStore';
import { Plus, Play, CheckCircle2, AlertTriangle, ArrowRight, Activity, Cpu, Database, CpuIcon } from 'lucide-react';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { projects, setActiveProjectId } = useProjectStore();

  // Summary counts
  const totalProjects = projects.length;
  const totalModels = projects.reduce((acc, p) => acc + (p.modelsTestedCount || 0), 0);

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Dashboard Overview</h1>
          <p className="text-sm text-zinc-400">Manage your local S3 datasets, experiments, and model explanations.</p>
        </div>
        <Link
          to="/create-project"
          className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-4 py-2 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/25"
        >
          <Plus className="w-4 h-4" />
          Create Project
        </Link>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border flex items-center justify-between">
          <div>
            <span className="text-xs font-mono uppercase text-zinc-500">Active Projects</span>
            <h3 className="text-2xl font-semibold text-zinc-100 font-mono mt-1">{totalProjects}</h3>
          </div>
          <div className="p-2.5 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-400">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border flex items-center justify-between">
          <div>
            <span className="text-xs font-mono uppercase text-zinc-500">Trained Models</span>
            <h3 className="text-2xl font-semibold text-zinc-100 font-mono mt-1">{totalModels}</h3>
          </div>
          <div className="p-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Cpu className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border flex items-center justify-between">
          <div>
            <span className="text-xs font-mono uppercase text-zinc-500">Compute Queue</span>
            <h3 className="text-sm font-semibold text-emerald-400 mt-1 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-pulse"></span>
              GPU Workers Idle
            </h3>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <CpuIcon className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border flex items-center justify-between">
          <div>
            <span className="text-xs font-mono uppercase text-zinc-500">Kafka Streaming</span>
            <h3 className="text-sm font-semibold text-zinc-300 mt-1">2 Workers Online</h3>
          </div>
          <div className="p-2.5 rounded-lg bg-zinc-500/10 border border-zinc-500/20 text-zinc-400">
            <Database className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Projects Grid Section */}
      <div className="space-y-3">
        <h2 className="text-xl font-display font-semibold text-zinc-200">Recent Projects</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((p) => {
            const isCompleted = p.status === 'Ready for Deployment';
            const isTraining = p.status === 'Training';
            
            return (
              <div 
                key={p.id}
                className="bg-brand-dark-surface border border-brand-dark-border hover:border-violet-500/30 rounded-xl p-5 flex flex-col justify-between transition-all group hover:shadow-lg hover:shadow-brand-primary/5"
              >
                <div className="space-y-3">
                  {/* Card Header */}
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-lg font-display font-bold text-zinc-100 group-hover:text-violet-300 transition-colors">
                        {p.name}
                      </h3>
                      <span className="text-xs font-mono text-zinc-500 uppercase">Target: {p.targetVariable}</span>
                    </div>

                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                      isCompleted 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                        : isTraining 
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' 
                          : 'bg-zinc-500/10 text-zinc-400 border border-zinc-500/20'
                    }`}>
                      {p.status}
                    </span>
                  </div>

                  {/* Description */}
                  <p className="text-sm text-zinc-400 leading-relaxed line-clamp-2">
                    {p.description}
                  </p>

                  {/* Summary Specs */}
                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-brand-dark-border/40 text-center font-mono">
                    <div className="bg-brand-dark-bg/60 p-2 rounded-lg border border-brand-dark-border/20">
                      <span className="text-[10px] text-zinc-500 uppercase">Rows</span>
                      <p className="text-xs font-bold text-zinc-300 mt-0.5">{p.rowsCount?.toLocaleString()}</p>
                    </div>
                    <div className="bg-brand-dark-bg/60 p-2 rounded-lg border border-brand-dark-border/20">
                      <span className="text-[10px] text-zinc-500 uppercase">Features</span>
                      <p className="text-xs font-bold text-zinc-300 mt-0.5">{p.columnsCount}</p>
                    </div>
                    <div className="bg-brand-dark-bg/60 p-2 rounded-lg border border-brand-dark-border/20">
                      <span className="text-[10px] text-zinc-500 uppercase">Best Model</span>
                      <p className="text-xs font-bold text-violet-300 mt-0.5 truncate">{p.bestModel}</p>
                    </div>
                  </div>

                  {/* Model score */}
                  {p.bestF1 && (
                    <div className="flex items-center justify-between text-xs bg-emerald-500/5 border border-emerald-500/10 p-2.5 rounded-xl">
                      <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Best Score (F1)</span>
                      </div>
                      <span className="font-mono font-bold text-emerald-400 text-sm">{p.bestF1}</span>
                    </div>
                  )}
                </div>

                {/* Card Actions */}
                <div className="flex items-center gap-3 mt-5 pt-3 border-t border-brand-dark-border/40">
                  <button
                    onClick={() => {
                      setActiveProjectId(p.id);
                      navigate('/overview');
                    }}
                    className="flex-1 flex items-center justify-center gap-1 bg-brand-dark-card hover:bg-brand-dark-border border border-brand-dark-border hover:text-white px-4 py-2 rounded-xl text-xs font-bold text-zinc-300 transition-all cursor-pointer"
                  >
                    Open Workspace
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
