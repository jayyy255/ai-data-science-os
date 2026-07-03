import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useProjectStore } from '../store/useProjectStore';
import {
  LayoutDashboard,
  FolderKanban,
  Database,
  BarChart3,
  Sliders,
  Cpu,
  Eye,
  GitCommit,
  FileText,
  MessageSquare,
  Archive,
  Activity,
  Settings,
  Menu,
  ChevronRight,
  LogOut,
  Sparkles,
  HelpCircle,
  TrendingUp,
  BrainCircuit,
  Lock,
  Layers,
  ArrowRight,
  CheckCircle,
  FileCode
} from 'lucide-react';

export default function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { getActiveProject, projects, setActiveProjectId, currentUser, logout } = useProjectStore();
  
  const [kcOpen, setKcOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  const activeProject = getActiveProject();
  const activePath = location.pathname;

  const navLinks = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Project Overview', path: '/overview', icon: FolderKanban },
    { name: 'Dataset Intelligence', path: '/dataset', icon: Database },
    { name: 'EDA', path: '/eda', icon: BarChart3 },
    { name: 'Feature Engineering', path: '/features', icon: Sliders },
    { name: 'Training & HPO', path: '/training', icon: Cpu },
    { name: 'Explainability (SHAP)', path: '/explainability', icon: Eye },
    { name: 'Timeline Auditing', path: '/timeline', icon: GitCommit },
    { name: 'Knowledge Card', path: '/knowledge-card', icon: FileText },
    { name: 'AI Assistant', path: '/assistant', icon: MessageSquare },
    { name: 'Model Registry', path: '/registry', icon: Archive },
    { name: 'Monitoring & Drift', path: '/monitoring', icon: Activity },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <div className="min-h-screen bg-brand-dark-bg text-zinc-100 flex flex-col font-body">
      {/* Top Navbar */}
      <header className="bg-brand-dark-surface border-b border-brand-dark-border h-16 px-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 hover:bg-brand-dark-card rounded-lg lg:hidden"
          >
            <Menu className="w-5 h-5 text-zinc-400" />
          </button>
          <div className="flex items-center gap-2">
            <div className="bg-brand-primary p-1.5 rounded-lg flex items-center justify-center">
              <BrainCircuit className="w-6 h-6 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight bg-gradient-to-r from-violet-400 via-indigo-200 to-purple-400 bg-clip-text text-transparent">
              AIDSO
            </span>
            <span className="text-[10px] uppercase font-mono tracking-widest text-brand-primary font-bold px-1.5 py-0.5 rounded bg-brand-primary/10 border border-brand-primary/20">
              v1.0
            </span>
          </div>
        </div>

        {/* Project Selector & Actions */}
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-2 bg-brand-dark-bg border border-brand-dark-border px-3 py-1.5 rounded-xl">
            <span className="text-xs text-zinc-500 font-mono">Active Project:</span>
            <select
              value={activeProject.id}
              onChange={(e) => setActiveProjectId(e.target.value)}
              className="bg-transparent text-sm font-semibold text-violet-300 focus:outline-none cursor-pointer"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-brand-dark-surface text-zinc-200">
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setKcOpen(!kcOpen)}
            className="flex items-center gap-2 bg-brand-primary/10 hover:bg-brand-primary/20 border border-brand-primary/30 text-violet-300 px-3.5 py-1.5 rounded-xl text-sm font-medium transition-all cursor-pointer"
          >
            <FileText className="w-4 h-4" />
            <span className="hidden md:inline">Knowledge Card</span>
            <span className={`w-2 h-2 rounded-full ${activeProject.status === 'Ready for Deployment' ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`}></span>
          </button>

          {currentUser && (
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="p-2 hover:bg-red-500/10 hover:text-red-400 border border-transparent hover:border-red-500/20 text-zinc-400 rounded-xl transition-all cursor-pointer"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </header>

      <div className="flex flex-1 relative">
        {/* Sidebar Navigation */}
        <aside className={`
          fixed inset-y-16 left-0 z-30 w-64 bg-brand-dark-surface border-r border-brand-dark-border transform transition-transform duration-300 ease-in-out
          lg:translate-x-0 lg:static lg:h-[calc(100vh-4rem)]
          ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
        `}>
          <div className="flex flex-col h-full justify-between p-4 overflow-y-auto">
            <nav className="space-y-1">
              <div className="px-3 mb-2 text-xs font-mono tracking-widest text-zinc-500 uppercase">
                Navigation
              </div>
              {navLinks.map((link) => {
                const Icon = link.icon;
                const isActive = activePath === link.path;
                return (
                  <Link
                    key={link.path}
                    to={link.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`
                      flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group
                      ${isActive 
                        ? 'bg-brand-primary/10 border-l-2 border-brand-primary text-violet-300' 
                        : 'text-zinc-400 hover:bg-brand-dark-card hover:text-zinc-200'}
                    `}
                  >
                    <Icon className={`w-4 h-4 group-hover:scale-110 transition-transform ${isActive ? 'text-brand-primary' : 'text-zinc-500'}`} />
                    <span>{link.name}</span>
                  </Link>
                );
              })}
            </nav>

            <div className="mt-8 border-t border-brand-dark-border pt-4">
              <div className="bg-brand-dark-bg p-3 rounded-xl border border-brand-dark-border text-xs">
                <div className="flex items-center gap-2 mb-1.5 text-violet-300 font-semibold font-display">
                  <Sparkles className="w-3.5 h-3.5 text-brand-primary" />
                  <span>Gemini Engine</span>
                </div>
                <p className="text-zinc-500 leading-relaxed font-mono">
                  Understanding: Active<br/>
                  Drift Audit: 30s intervals
                </p>
              </div>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-4 lg:p-6 overflow-y-auto max-h-[calc(100vh-4rem)] w-full">
          {children}
        </main>

        {/* Knowledge Card Collapsible Overlay (Drawer) */}
        {kcOpen && (
          <div className="fixed inset-0 z-50 flex justify-end">
            {/* Backdrop */}
            <div 
              onClick={() => setKcOpen(false)}
              className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300"
            />
            
            {/* Slide-over panel */}
            <div className="relative w-full max-w-md bg-brand-dark-surface border-l border-brand-dark-border h-full flex flex-col shadow-2xl z-10 transition-all duration-300 animate-slide-in">
              {/* Header */}
              <div className="p-4 border-b border-brand-dark-border flex items-center justify-between bg-brand-dark-surface/50">
                <div className="flex items-center gap-2.5">
                  <FileText className="w-5 h-5 text-brand-primary" />
                  <div>
                    <h2 className="font-display font-semibold text-base text-zinc-100">Project Knowledge Card</h2>
                    <p className="text-xs font-mono text-zinc-500">Single Source of Truth</p>
                  </div>
                </div>
                <button
                  onClick={() => setKcOpen(false)}
                  className="p-1.5 hover:bg-brand-dark-card rounded-lg text-zinc-400"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>

              {/* Scrollable Content */}
              <div className="flex-1 overflow-y-auto p-4 space-y-5">
                {/* Level 1: Executive Summary */}
                <div className="bg-brand-dark-bg p-4 rounded-xl border border-brand-dark-border">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] uppercase font-mono tracking-widest text-zinc-500 font-bold px-1.5 py-0.5 rounded bg-zinc-800">
                      Level 1: Executive
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                      activeProject.status === 'Ready for Deployment' 
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}>
                      {activeProject.status}
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-zinc-500">Project Name</span>
                      <span className="font-medium text-zinc-200">{activeProject.name}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-zinc-500">Best Model</span>
                      <span className="font-semibold text-violet-300">{activeProject.bestModel}</span>
                    </div>
                    {activeProject.bestF1 && (
                      <div className="flex justify-between items-center text-sm">
                        <span className="text-zinc-500">Best F1 Score</span>
                        <span className="font-semibold text-emerald-400 font-mono">{activeProject.bestF1}</span>
                      </div>
                    )}
                    <div className="flex justify-between items-center text-sm">
                      <span className="text-zinc-500">Problem Type</span>
                      <span className="capitalize text-zinc-300 font-mono text-xs">{activeProject.problemType}</span>
                    </div>
                  </div>
                </div>

                {/* Level 2: Technical Summary */}
                <div className="bg-brand-dark-bg p-4 rounded-xl border border-brand-dark-border">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] uppercase font-mono tracking-widest text-zinc-500 font-bold px-1.5 py-0.5 rounded bg-zinc-800">
                      Level 2: Technical
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    <div className="grid grid-cols-2 gap-3 text-center">
                      <div className="bg-brand-dark-card p-2 rounded-lg border border-brand-dark-border">
                        <p className="text-[10px] text-zinc-500 font-mono uppercase">Dataset Rows</p>
                        <p className="font-mono text-sm font-semibold text-zinc-200">{activeProject.rowsCount?.toLocaleString()}</p>
                      </div>
                      <div className="bg-brand-dark-card p-2 rounded-lg border border-brand-dark-border">
                        <p className="text-[10px] text-zinc-500 font-mono uppercase">Total Features</p>
                        <p className="font-mono text-sm font-semibold text-zinc-200">{activeProject.columnsCount}</p>
                      </div>
                    </div>
                    
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Missing Values</span>
                        <span className="text-zinc-300 font-mono">{activeProject.missingValuesPct}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Class Balancing</span>
                        <span className="text-zinc-300 font-mono text-xs">{activeProject.balancingMethod}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-zinc-500">Models Checked</span>
                        <span className="text-zinc-300 font-mono">{activeProject.modelsTestedCount} architectures</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Level 3: AI summary / Decisions log */}
                <div className="bg-brand-dark-bg p-4 rounded-xl border border-brand-dark-border">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[10px] uppercase font-mono tracking-widest text-zinc-500 font-bold px-1.5 py-0.5 rounded bg-zinc-800">
                      Level 3: Project Memory
                    </span>
                  </div>

                  <div className="space-y-3">
                    {activeProject.featureEngineeringDecisions.slice(0, 3).map((dec, i) => (
                      <div key={i} className="border-l-2 border-brand-primary pl-3 py-0.5">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="font-bold text-violet-300 font-display">{dec.feature} &rarr; {dec.decision}</span>
                          <span className="text-[10px] text-emerald-400 font-mono bg-emerald-500/10 px-1 rounded">
                            {(dec.confidence * 100).toFixed(0)}% AI Conf.
                          </span>
                        </div>
                        <p className="text-xs text-zinc-400 leading-relaxed">{dec.reason}</p>
                        {dec.overrideActive && (
                          <div className="mt-1 text-[9px] font-semibold uppercase text-amber-400 flex items-center gap-1">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
                            User Override Active: {dec.userChoice}
                          </div>
                        )}
                      </div>
                    ))}
                    {activeProject.featureEngineeringDecisions.length === 0 && (
                      <div className="text-center py-4 text-xs text-zinc-500">
                        No AI decisions logged in memory yet.
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="p-4 border-t border-brand-dark-border bg-brand-dark-surface/50 grid grid-cols-2 gap-3">
                <Link
                  to="/knowledge-card"
                  onClick={() => setKcOpen(false)}
                  className="flex items-center justify-center gap-2 border border-brand-dark-border hover:bg-brand-dark-card px-3 py-2 rounded-xl text-xs font-semibold text-zinc-300 transition-all cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5" />
                  Full Centerpiece
                </Link>
                <button
                  onClick={() => {
                    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeProject, null, 2));
                    const downloadAnchor = document.createElement('a');
                    downloadAnchor.setAttribute("href", dataStr);
                    downloadAnchor.setAttribute("download", `knowledge_card_${activeProject.id}.json`);
                    document.body.appendChild(downloadAnchor);
                    downloadAnchor.click();
                    downloadAnchor.remove();
                  }}
                  className="flex items-center justify-center gap-2 bg-brand-primary hover:bg-brand-primary-hover px-3 py-2 rounded-xl text-xs font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20"
                >
                  <Archive className="w-3.5 h-3.5" />
                  Export JSON
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
