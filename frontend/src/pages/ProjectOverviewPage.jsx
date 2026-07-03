import React from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Calendar, Tag, CheckCircle2, ChevronRight, Activity, Clock, Server, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function ProjectOverviewPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  const isCompleted = project.status === 'Ready for Deployment';

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-xs uppercase font-mono tracking-widest text-brand-primary bg-brand-primary/10 border border-brand-primary/20 px-2 py-0.5 rounded font-bold">
              {project.problemType}
            </span>
            <span className="text-xs font-mono text-zinc-500">Target Variable:</span>
            <span className="text-xs font-mono font-bold text-violet-300 bg-brand-dark-card border border-brand-dark-border px-1.5 py-0.5 rounded">
              {project.targetVariable}
            </span>
          </div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">{project.name}</h1>
        </div>

        <span className={`self-start md:self-auto px-3 py-1 rounded-full text-xs font-semibold ${
          isCompleted 
            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
            : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
        }`}>
          Status: {project.status}
        </span>
      </div>

      {/* Description */}
      <div className="bg-brand-dark-surface p-5 rounded-xl border border-brand-dark-border space-y-2">
        <h3 className="text-xs font-mono uppercase text-zinc-500">Business Objective & Context</h3>
        <p className="text-zinc-300 text-sm leading-relaxed max-w-4xl">
          {project.description}
        </p>
      </div>

      {/* Statistics Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
          <p className="text-[10px] text-zinc-500 font-mono uppercase">Dataset Rows</p>
          <h4 className="text-xl font-bold font-mono text-zinc-200 mt-1">{project.rowsCount?.toLocaleString()}</h4>
        </div>
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
          <p className="text-[10px] text-zinc-500 font-mono uppercase">Columns Count</p>
          <h4 className="text-xl font-bold font-mono text-zinc-200 mt-1">{project.columnsCount}</h4>
        </div>
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
          <p className="text-[10px] text-zinc-500 font-mono uppercase">Missing Values</p>
          <h4 className="text-xl font-bold font-mono text-amber-400 mt-1">{project.missingValuesPct}%</h4>
        </div>
        <div className="bg-brand-dark-surface p-4 rounded-xl border border-brand-dark-border text-center">
          <p className="text-[10px] text-zinc-500 font-mono uppercase">Best Model</p>
          <h4 className="text-xl font-bold font-mono text-violet-300 mt-1 truncate">{project.bestModel}</h4>
        </div>
      </div>

      {/* Two Columns: Quick Model Info & Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Model state */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-200 border-b border-brand-dark-border/40 pb-2 flex items-center gap-2">
              <Server className="w-4 h-4 text-brand-primary" />
              Deployment Summary
            </h3>
            
            <div className="space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Champion Model</span>
                <span className="font-semibold text-violet-300 font-mono">{project.bestModel}</span>
              </div>
              {project.bestF1 && (
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Validation F1 Score</span>
                  <span className="font-semibold text-emerald-400 font-mono">{project.bestF1}</span>
                </div>
              )}
              {project.bestAccuracy && (
                <div className="flex justify-between items-center">
                  <span className="text-zinc-500">Validation Accuracy</span>
                  <span className="font-semibold text-zinc-300 font-mono">{project.bestAccuracy}</span>
                </div>
              )}
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Class Balancing</span>
                <span className="text-zinc-300 font-mono text-xs">{project.balancingMethod}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-zinc-500">Models Tested</span>
                <span className="text-zinc-300 font-mono">{project.modelsTestedCount} variants</span>
              </div>
            </div>

            <div className="pt-3 border-t border-brand-dark-border/40">
              <Link
                to="/registry"
                className="w-full flex items-center justify-center gap-1 bg-brand-primary hover:bg-brand-primary-hover py-2.5 rounded-xl text-xs font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/10"
              >
                Go to Registry
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>
        </div>

        {/* Milestone timeline */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-brand-dark-border/40 pb-2">
              <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
                <Clock className="w-4 h-4 text-brand-primary" />
                Recent Milestones
              </h3>
              <Link to="/timeline" className="text-xs text-violet-400 hover:underline flex items-center gap-0.5">
                Full timeline
                <ChevronRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="space-y-4 relative before:absolute before:inset-y-1 before:left-3.5 before:w-0.5 before:bg-brand-dark-border/60 pl-1">
              {project.timeline.slice(0, 4).map((evt, i) => (
                <div key={i} className="flex gap-4 relative group">
                  <div className="w-7 h-7 rounded-full bg-brand-dark-card border-2 border-brand-dark-border flex items-center justify-center text-xs font-bold z-10">
                    <span className={`w-2 h-2 rounded-full ${
                      evt.type === 'success' ? 'bg-emerald-500' : evt.type === 'warning' ? 'bg-amber-500' : 'bg-brand-primary'
                    }`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <h4 className="text-sm font-semibold text-zinc-200">{evt.title}</h4>
                      <span className="text-[10px] font-mono text-zinc-500 whitespace-nowrap">{evt.time}</span>
                    </div>
                    <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">{evt.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
