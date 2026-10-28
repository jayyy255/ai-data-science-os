import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useProjectStore } from '../store/useProjectStore';
import ThemeToggle from './ThemeToggle';
import { FolderKanban, Database, BarChart3, Sliders, Cpu, Eye, GitCommit, FileText, MessageSquare, Archive, Activity, Menu, X, LogOut, Sparkles, BrainCircuit, User } from 'lucide-react';

export default function Layout({ children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { getActiveProject, activeProjectId, currentUser, logout, fetchProjects, error, clearError, loading, fetchProjectDetails, fetchProjectJobs } = useProjectStore();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const sidebarRef = useRef(null);
  const menuButtonRef = useRef(null);
  const mainRef = useRef(null);

  useEffect(() => {
    mainRef.current?.scrollTo(0, 0);
  }, [location.pathname]);

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const sidebar = sidebarRef.current;
    const menuButton = menuButtonRef.current;
    const controls = () => [...sidebar.querySelectorAll('a[href], button:not([disabled])')];
    controls()[0]?.focus();
    const onKeyDown = event => {
      if (event.key === 'Escape') setMobileMenuOpen(false);
      if (event.key !== 'Tab') return;
      const items = controls();
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    };
    const desktop = window.matchMedia('(min-width: 1024px)');
    const closeOnDesktop = () => { if (desktop.matches) setMobileMenuOpen(false); };
    document.addEventListener('keydown', onKeyDown);
    desktop.addEventListener('change', closeOnDesktop);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      desktop.removeEventListener('change', closeOnDesktop);
      if (!desktop.matches) menuButton?.focus();
    };
  }, [mobileMenuOpen]);

  const activeProject = getActiveProject();
  const activePath = location.pathname;

  useEffect(() => {
    fetchProjects().catch(() => {});
  }, [fetchProjects]);

  const isWorkspacePath = activePath !== '/' && activePath !== '/create-project' && activePath !== '/login' && activePath !== '/settings';
  const showSidebar = activeProjectId && isWorkspacePath;

  useEffect(() => {
    if (!activeProject.id || activeProject.status !== 'Training') return;
    const interval = setInterval(() => {
      fetchProjectDetails(activeProject.id).catch(() => {});
      fetchProjectJobs(activeProject.id);
    }, 3000);
    return () => clearInterval(interval);
  }, [activeProject.id, activeProject.status, fetchProjectDetails, fetchProjectJobs]);

  const navLinks = [
    { name: 'Project Overview', path: '/overview', icon: FolderKanban },
    { name: 'Timeline Auditing', path: '/timeline', icon: GitCommit },
    { name: 'Dataset Intelligence', path: '/dataset', icon: Database },
    { name: 'Chat Assistant', path: '/assistant', icon: MessageSquare },
    { name: 'EDA', path: '/eda', icon: BarChart3 },
    { name: 'Feature Engineering', path: '/features', icon: Sliders },
    { name: 'Training & HPO', path: '/training', icon: Cpu },
    { name: 'Explainability (SHAP)', path: '/explainability', icon: Eye },
    { name: 'Knowledge Card', path: '/knowledge-card', icon: FileText },
    { name: 'Model Registry', path: '/registry', icon: Archive },
    { name: 'Monitoring & Drift', path: '/monitoring', icon: Activity },
  ];

  return (
    <div className="app-shell min-h-screen text-zinc-100 flex flex-col font-body">
      <a href="#main-content" className="skip-link" onClick={event => { event.preventDefault(); document.getElementById('main-content')?.focus(); }}>Skip to content</a>
      {/* Top Navbar */}
      <header className="glass-header border-b border-brand-dark-border h-16 px-4 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          {showSidebar && (
            <button
              ref={menuButtonRef}
              aria-label={mobileMenuOpen ? 'Close navigation' : 'Open navigation'}
              aria-expanded={mobileMenuOpen}
              aria-controls="workspace-navigation"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="glass-icon-button p-2 hover:bg-brand-dark-card rounded-xl lg:hidden"
            >
              <Menu className="w-5 h-5 text-zinc-400" />
            </button>
          )}

          {/* DSOS Clickable Logo */}
          <Link to="/" className="flex items-center gap-2 cursor-pointer group">
            <div className="glass-logo bg-brand-primary p-1.5 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform">
              <BrainCircuit className="w-6 h-6 text-white" />
            </div>
            <span className="font-display font-bold text-xl tracking-tight bg-gradient-to-r from-violet-400 via-indigo-200 to-purple-400 bg-clip-text text-transparent group-hover:opacity-90 transition-opacity">
              DSOS
            </span>
            <span className="text-[10px] uppercase font-mono tracking-widest text-brand-primary font-bold px-1.5 py-0.5 rounded bg-brand-primary/10 border border-brand-primary/20">
              v1.0
            </span>
          </Link>
        </div>

        {/* User Details & Logout */}
        <div className="flex items-center gap-3">
          {currentUser && (
            <div className="user-pill flex items-center gap-2 border border-brand-dark-border px-3.5 py-1.5 rounded-full text-xs font-mono text-zinc-300">
              <User className="w-3.5 h-3.5 text-brand-primary" />
              <span className="username-label max-w-52 truncate"><span className="hidden sm:inline">Username: </span><strong className="font-dataset-name dataset-username text-violet-300">{currentUser.username || currentUser.email.split('@')[0]}</strong></span>
            </div>
          )}

          <ThemeToggle />

          {currentUser && (
            <>
            <Link to="/settings" aria-label="System Status" title="System Status" className="system-link text-zinc-400 text-sm flex items-center gap-2"><Activity className="h-4 w-4 sm:hidden" /><span className="hidden sm:inline">System Status</span></Link>
            <button
              onClick={async () => { try { await logout(); } finally { navigate('/login'); } }}
              className="glass-icon-button p-2 hover:bg-red-500/10 hover:text-red-400 border border-transparent hover:border-red-500/20 text-zinc-400 rounded-xl transition-all cursor-pointer"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
            </>
          )}
        </div>
      </header>

      <div className="flex flex-1 relative">
        {showSidebar && mobileMenuOpen && <button className="nav-scrim lg:hidden" aria-label="Close navigation backdrop" onClick={() => setMobileMenuOpen(false)} tabIndex={-1} />}
        {/* Sidebar Navigation */}
        {showSidebar && (
          <aside id="workspace-navigation" ref={sidebarRef} role={mobileMenuOpen ? 'dialog' : undefined} aria-modal={mobileMenuOpen || undefined} aria-label="Workspace navigation" className={`glass-sidebar ${mobileMenuOpen ? 'is-open' : ''}
            fixed inset-y-16 left-0 z-50 w-64 border border-brand-dark-border transform transition-transform duration-300 ease-in-out
            lg:translate-x-0 lg:static
            ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}
          `}>
            <div className="flex flex-col h-full justify-between p-4 overflow-y-auto">
              <nav className="space-y-1" aria-label="Project">
                <button aria-label="Close navigation" onClick={() => setMobileMenuOpen(false)} className="glass-icon-button mb-3 ml-auto flex items-center justify-center lg:hidden"><X className="w-5 h-5" /></button>
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
                      aria-current={isActive ? 'page' : undefined}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`
                        glass-nav-link flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group
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
                    Project context summaries<br/>
                    Drift: compare uploaded data
                  </p>
                </div>
              </div>
            </div>
          </aside>
        )}

        {/* Main Content Area */}
        <main id="main-content" ref={mainRef} tabIndex={-1} inert={mobileMenuOpen || undefined} className="glass-workspace flex-1 p-4 lg:p-6 overflow-y-auto w-full">
          {error && <div role="alert" className="mb-4 p-3 rounded-xl border border-red-500/30 text-red-300">{error} <button onClick={clearError} className="ml-3 underline">Dismiss</button></div>}
            {loading && <p className="text-zinc-400 mb-3">Loading projects...</p>}
            {!loading && !activeProject.id && isWorkspacePath && activePath !== '/create-project' ? <Link to="/create-project" className="text-violet-300">Create a project to get started.</Link> : children}
        </main>
      </div>
    </div>
  );
}
