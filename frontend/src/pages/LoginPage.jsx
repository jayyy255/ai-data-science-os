import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '../store/useProjectStore';
import { BrainCircuit, KeyRound, Mail, ShieldCheck } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useProjectStore((state) => state.login);
  const [email, setEmail] = useState('datascientist@company.ai');
  const [password, setPassword] = useState('password123');

  const handleSubmit = (e) => {
    e.preventDefault();
    login(email, password);
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-brand-dark-bg text-zinc-100 flex font-body">
      {/* Left Pane - Neural Network Art & Subtitle */}
      <div className="hidden lg:flex w-1/2 relative bg-neutral-950 items-center justify-center border-r border-brand-dark-border overflow-hidden">
        {/* Glow Effects */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-primary/10 rounded-full blur-[120px] pointer-events-none"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none"></div>
        
        {/* Grid Line Overlay */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1f293710_1px,transparent_1px),linear-gradient(to_bottom,#1f293710_1px,transparent_1px)] bg-[size:4rem_4rem]"></div>
        
        {/* Technical Visualization Grid */}
        <div className="relative z-10 p-12 max-w-lg space-y-6">
          <div className="flex items-center gap-3">
            <div className="bg-brand-primary/20 p-2.5 rounded-2xl border border-brand-primary/30">
              <BrainCircuit className="w-10 h-10 text-violet-400" />
            </div>
            <h1 className="font-display font-extrabold text-3xl tracking-tight bg-gradient-to-r from-violet-400 via-indigo-200 to-purple-400 bg-clip-text text-transparent">
              AIDSO
            </h1>
          </div>
          <div className="space-y-4">
            <h2 className="text-4xl font-display font-bold text-white leading-tight">
              Turn Raw Data into Explainable Models
            </h2>
            <p className="text-zinc-400 leading-relaxed text-sm">
              AIDSO is a memory-driven, local-first Operating System for Data Scientists. Track experiments, manage data quality, run HPO trials via Kafka, and explain model decisions automatically.
            </p>
          </div>

          <div className="pt-6 border-t border-brand-dark-border/40 grid grid-cols-2 gap-4">
            <div className="bg-brand-dark-surface/40 p-4 rounded-xl border border-brand-dark-border/30">
              <span className="text-[10px] font-mono text-zinc-500 uppercase">Architecture</span>
              <p className="text-xs font-semibold text-zinc-300">S3 / MinIO Storage</p>
            </div>
            <div className="bg-brand-dark-surface/40 p-4 rounded-xl border border-brand-dark-border/30">
              <span className="text-[10px] font-mono text-zinc-500 uppercase">Event Loop</span>
              <p className="text-xs font-semibold text-zinc-300">Kafka Workers</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Pane - Form Card */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 bg-brand-dark-bg">
        <div className="w-full max-w-md space-y-8 bg-brand-dark-surface/40 p-8 rounded-2xl border border-brand-dark-border/60 shadow-xl backdrop-blur-md">
          <div className="space-y-2 text-center lg:text-left">
            <h3 className="text-2xl font-display font-bold text-white">Sign In</h3>
            <p className="text-xs text-zinc-400">Access your local data science projects & training state</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email Field */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-zinc-400">Email Address</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3 w-4 h-4 text-zinc-500" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2.5 pl-10 pr-4 rounded-xl text-sm font-medium transition-all"
                  required
                />
              </div>
            </div>

            {/* Password Field */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-zinc-400">Password</label>
                <a href="#forgot" className="text-xs text-violet-400 hover:underline">Forgot password?</a>
              </div>
              <div className="relative">
                <KeyRound className="absolute left-3.5 top-3 w-4 h-4 text-zinc-500" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2.5 pl-10 pr-4 rounded-xl text-sm font-medium transition-all"
                  required
                />
              </div>
            </div>

            {/* Sign In Button */}
            <button
              type="submit"
              className="w-full bg-brand-primary hover:bg-brand-primary-hover py-2.5 rounded-xl text-sm font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/20 flex items-center justify-center gap-2"
            >
              Sign In
            </button>
          </form>



          {/* Footer note */}
          <div className="text-center pt-2 flex items-center justify-center gap-1.5 text-[10px] text-zinc-500 font-mono">
            <ShieldCheck className="w-3.5 h-3.5 text-zinc-600" />
            <span>Redis Session Cache & JWT Auth Enabled</span>
          </div>
        </div>
      </div>
    </div>
  );
}
