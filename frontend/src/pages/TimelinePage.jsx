import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Clock, Search, ChevronDown, ChevronUp, FileCode } from 'lucide-react';

export default function TimelinePage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();

  const [expandedId, setExpandedId] = useState(null);

  const toggleExpand = (idx) => {
    setExpandedId(expandedId === idx ? null : idx);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white tracking-tight">Timeline Auditing</h1>
        <p className="text-sm text-zinc-400">Chronological history log of every pipeline trigger, model run, and memory updates.</p>
      </div>

      {/* Timeline Layout */}
      <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-6 shadow-xl max-w-3xl">
        <div className="space-y-6 relative before:absolute before:inset-y-2 before:left-4 before:w-0.5 before:bg-brand-dark-border pl-1">
          
          {project.timeline?.map((evt, idx) => {
            const isExpanded = expandedId === idx;
            return (
              <div key={idx} className="flex gap-5 relative">
                
                {/* Node icon indicator */}
                <div className="w-8 h-8 rounded-full bg-brand-dark-card border border-brand-dark-border flex items-center justify-center text-xs font-bold z-10 select-none">
                  <span className={`w-2.5 h-2.5 rounded-full ${
                    evt.type === 'success' ? 'bg-emerald-500' : evt.type === 'warning' ? 'bg-amber-500' : 'bg-brand-primary'
                  }`} />
                </div>

                {/* Event text card */}
                <div className="flex-1 bg-brand-dark-bg/60 border border-brand-dark-border/40 hover:border-brand-dark-border rounded-xl p-4 transition-all">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-sm font-bold text-zinc-200">{evt.title}</h4>
                        <span className="text-[10px] uppercase font-mono tracking-wider font-semibold px-1.5 py-0.2 rounded bg-brand-dark-card border border-brand-dark-border text-zinc-400">
                          {evt.type}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-500 font-mono mt-0.5">{evt.time}</p>
                    </div>

                    <button
                      onClick={() => toggleExpand(idx)}
                      className="p-1 hover:bg-brand-dark-card rounded-lg text-zinc-400 cursor-pointer"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>

                  <p className="text-xs text-zinc-300 mt-2 leading-relaxed">
                    {evt.desc}
                  </p>

                  {/* Collapsible JSON Log panel */}
                  {isExpanded && (
                    <div className="mt-3.5 pt-3 border-t border-brand-dark-border/40 space-y-2">
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-zinc-500">
                        <FileCode className="w-3.5 h-3.5" />
                        <span>System audit log payload:</span>
                      </div>
                      <pre className="bg-neutral-950 p-3 rounded-lg border border-brand-dark-border/40 overflow-x-auto text-[10px] font-mono text-violet-300 leading-normal max-w-full">
{JSON.stringify({
  event: evt.title,
  timestamp: evt.time,
  status: evt.type === 'success' ? 'SUCCESS' : 'PENDING',
  project_id: project.id,
  target: project.targetVariable,
  details: {
    logged_summary: evt.desc,
    optuna_optimizing: project.status === 'Training'
  }
}, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>

              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
