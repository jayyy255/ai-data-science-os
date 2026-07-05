import React, { useState, useEffect } from 'react';
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
  Menu,
  LogOut,
  Sparkles,
  BrainCircuit,
  User
} from 'lucide-react';

export default function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { getActiveProject, projects, activeProjectId, setActiveProjectId, currentUser, logout, fetchProjects } = useProjectStore();
  
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  const activeProject = getActiveProject();
  const activePath = location.pathname;

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const isWorkspacePath = activePath !== '/' && activePath !== '/create' && activePath !== '/login';
  const showSidebar = activeProjectId && isWorkspacePath;

  const navLinks = [
    { name: 'Project Overview', path: '/overview', icon: FolderKanban },
    { name: 'Timeline Auditing', path: '/timeline', icon: GitCommit },
    { name: 'Dataset Intelligence', path: '/dataset', icon: Database },
    { name: 'AI Assistant', path: '/assistant', icon: MessageSquare },
    { name: 'EDA', path: '/eda', icon: BarChart3 },
    { name: 'Feature Engineering', path: '/features', icon: Sliders },
    { name: 'Training & HPO', path: '/training', icon: Cpu },
    { name: 'Explainability (SHAP)', path: '/explainability', icon: Eye },
    { name: 'Knowledge Card', path: '/knowledge-card', icon: FileText },
    { name: 'Model Registry', path: '/registry', icon: Archive },
    { name: 'Monitoring & Drift', path: '/monitoring', icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-brand-dark-bg text-zinc-100 flex flex-col font-body">
      {/* Top Navbar */}
      <header className="bg-brand-dark-surface border-b border-brand-dark-border h-16 px-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          {showSidebar && (
            <button 
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 hover:bg-brand-dark-card rounded-lg lg:hidden"
            >
              <Menu className="w-5 h-5 text-zinc-400" />
            </button>
          )}
          
          {/* AIDSO Clickable Logo */}
          <Link to="/" className="flex items-center gap-2 cursor-pointer group">
            <div className="bg-brand-primary p-1.5 rounded-lg flex items-center justify-center group-hover:scale-105 transition-transform">
              <BrainCircuit className="w-6 h-6 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight bg-gradient-to-r from-violet-400 via-indigo-200 to-purple-400 bg-clip-text text-transparent group-hover:opacity-90 transition-opacity">
              AIDSO
            </span>
            <span className="text-[10px] uppercase font-mono tracking-widest text-brand-primary font-bold px-1.5 py-0.5 rounded bg-brand-primary/10 border border-brand-primary/20">
              v1.0
            </span>
          </Link>
        </div>

        {/* User Details & Logout */}
        <div className="flex items-center gap-3">
          {currentUser && (
            <div className="flex items-center gap-2 bg-brand-dark-bg border border-brand-dark-border px-3.5 py-1.5 rounded-xl text-xs font-mono text-zinc-300">
              <User className="w-3.5 h-3.5 text-brand-primary" />
              <span>Username: <strong className="text-violet-300 font-semibold">{currentUser.username || currentUser.email.split('@')[0]}</strong></span>
            </div>
          )}

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
        {showSidebar && (
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
        )}

        {/* Main Content Area */}
        <main className="flex-1 p-4 lg:p-6 overflow-y-auto max-h-[calc(100vh-4rem)] w-full">
          {children}
        </main>
      </div>
    </div>
  );
}
