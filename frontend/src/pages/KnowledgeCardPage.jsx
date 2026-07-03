import React from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { FileText, ArrowUpRight, CheckCircle2, Server, HelpCircle, Archive, Sliders, Database } from 'lucide-react';

export default function KnowledgeCardPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold text-white tracking-tight">Knowledge Card Dashboard</h1>
          <p className="text-sm text-zinc-400">The centerpiece knowledge representation summarizing the model architecture, preparatives, and memory logs.</p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(project, null, 2));
              const downloadAnchor = document.createElement('a');
              downloadAnchor.setAttribute("href", dataStr);
              downloadAnchor.setAttribute("download", `knowledge_card_${project.id}.json`);
              document.body.appendChild(downloadAnchor);
              downloadAnchor.click();
              downloadAnchor.remove();
            }}
            className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-4 py-2 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20"
          >
            <Archive className="w-4 h-4" />
            Export Card JSON
          </button>
        </div>
      </div>

      {/* Flagship Three-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        
        {/* Level 1: Executive Summary */}
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex flex-col justify-between hover:shadow-xl hover:shadow-brand-primary/5 transition-all">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-brand-dark-border/40 pb-2">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-brand-primary" />
                <h3 className="font-semibold text-zinc-200 text-sm">Level 1: Executive Summary</h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-500 uppercase bg-zinc-800/80 px-2 py-0.5 rounded border border-brand-dark-border">
                L1 CARD
              </span>
            </div>

            <div className="space-y-3.5 text-sm">
              <div className="bg-brand-dark-bg/60 p-3 rounded-xl border border-brand-dark-border/20">
                <span className="text-[10px] text-zinc-500 font-mono uppercase">Target Outcome Goal</span>
                <p className="text-zinc-200 mt-1 leading-relaxed">
                  Reduce customer attrition rate by predicting high-risk subscribers.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="bg-brand-dark-bg/60 p-3 rounded-xl border border-brand-dark-border/20">
                  <span className="text-[10px] text-zinc-500 font-mono uppercase">Champion Model</span>
                  <p className="text-sm font-bold text-violet-300 mt-1">{project.bestModel}</p>
                </div>
                <div className="bg-brand-dark-bg/60 p-3 rounded-xl border border-brand-dark-border/20">
                  <span className="text-[10px] text-zinc-500 font-mono uppercase">Validation F1</span>
                  <p className="text-sm font-bold text-emerald-400 mt-1 font-mono">{project.bestF1 || 'N/A'}</p>
                </div>
              </div>

              <div className="flex justify-between items-center py-1">
                <span className="text-zinc-500">Operation Status</span>
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  {project.status}
                </span>
              </div>
            </div>
          </div>
          
          <div className="pt-4 border-t border-brand-dark-border/40 text-xs text-zinc-500 italic">
            Visual metrics synthesized from active PostgreSQL schema profiles.
          </div>
        </div>

        {/* Level 2: Technical Summary */}
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex flex-col justify-between hover:shadow-xl hover:shadow-brand-primary/5 transition-all">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-brand-dark-border/40 pb-2">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-indigo-400" />
                <h3 className="font-semibold text-zinc-200 text-sm">Level 2: Technical Specs</h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-500 uppercase bg-zinc-800/80 px-2 py-0.5 rounded border border-brand-dark-border">
                L2 CARD
              </span>
            </div>

            <div className="space-y-3.5 text-sm">
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="bg-brand-dark-bg/60 p-2.5 rounded-xl border border-brand-dark-border/20">
                  <span className="text-[9px] text-zinc-500 font-mono uppercase block">Dataset Rows</span>
                  <strong className="text-zinc-200 font-mono text-sm">{project.rowsCount?.toLocaleString()}</strong>
                </div>
                <div className="bg-brand-dark-bg/60 p-2.5 rounded-xl border border-brand-dark-border/20">
                  <span className="text-[9px] text-zinc-500 font-mono uppercase block">Dataset Features</span>
                  <strong className="text-zinc-200 font-mono text-sm">{project.columnsCount} columns</strong>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-zinc-500">Missing Values</span>
                  <span className="font-mono text-zinc-300 font-bold">{project.missingValuesPct}% handled</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-zinc-500">Oversampling Method</span>
                  <span className="font-mono text-zinc-300 text-xs">{project.balancingMethod}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-zinc-500">Benchmarked Architectures</span>
                  <span className="font-mono text-zinc-300 font-bold">{project.modelsTestedCount} types</span>
                </div>
              </div>

              <div className="bg-brand-dark-bg/60 p-3 rounded-xl border border-brand-dark-border/20 text-xs space-y-1">
                <span className="text-[10px] text-zinc-500 font-mono uppercase">Top Predictor Features</span>
                <p className="font-semibold text-violet-300 font-mono">
                  {project.topFeatures?.join(', ')}
                </p>
              </div>
            </div>
          </div>

          <div className="pt-4 border-t border-brand-dark-border/40 text-xs text-zinc-500 italic">
            Metrics registered directly within MinIO objects and local PostgreSQL.
          </div>
        </div>

        {/* Level 3: AI summary / Decisions log */}
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex flex-col justify-between hover:shadow-xl hover:shadow-brand-primary/5 transition-all">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-brand-dark-border/40 pb-2">
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-violet-400" />
                <h3 className="font-semibold text-zinc-200 text-sm">Level 3: AI & Memory Summary</h3>
              </div>
              <span className="text-[10px] font-mono text-zinc-500 uppercase bg-zinc-800/80 px-2 py-0.5 rounded border border-brand-dark-border">
                L3 CARD
              </span>
            </div>

            <div className="space-y-3.5">
              {project.featureEngineeringDecisions?.slice(0, 3).map((dec, i) => (
                <div key={i} className="border-l-2 border-brand-primary pl-3 text-xs">
                  <div className="flex justify-between font-bold text-violet-300 mb-0.5 font-display">
                    <span>{dec.feature} &rarr; {dec.decision}</span>
                    <span className="text-[10px] font-mono text-emerald-400">
                      {(dec.confidence * 100).toFixed(0)}% AI
                    </span>
                  </div>
                  <p className="text-zinc-400 leading-normal text-[11px]">{dec.reason}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-4 border-t border-brand-dark-border/40 text-xs text-zinc-500 italic">
            Chronological reasoning log synchronized with project memory tables.
          </div>
        </div>

      </div>
    </div>
  );
}
