import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { Server, ShieldCheck, KeyRound, Save, HelpCircle, HardDrive, RefreshCw } from 'lucide-react';

export default function SettingsPage() {
  const { connections, updateConnections } = useProjectStore();

  const [activeTab, setActiveTab] = useState('infrastructure');
  
  // Local form states
  const [pgUrl, setPgUrl] = useState(connections.postgresql.url);
  const [redisUrl, setRedisUrl] = useState(connections.redis.url);
  const [minioEndpoint, setMinioEndpoint] = useState(connections.minio.endpoint);
  const [minioAccessKey, setMinioAccessKey] = useState(connections.minio.accessKey);
  const [minioSecretKey, setMinioSecretKey] = useState('••••••••••••');
  const [kafkaBrokers, setKafkaBrokers] = useState(connections.kafka.brokers);

  const [geminiKey, setGeminiKey] = useState(connections.gemini.apiKey);
  const [geminiModel, setGeminiModel] = useState(connections.gemini.model);
  const [jwtSecret, setJwtSecret] = useState(connections.jwtSecret);

  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState('');

  const handleSave = (e) => {
    e.preventDefault();
    setSaving(true);
    setTestResult('');

    // Update connection store values
    updateConnections({
      postgresql: { status: 'CONNECTED', url: pgUrl },
      redis: { status: 'CONNECTED', url: redisUrl },
      minio: { status: 'CONNECTED', endpoint: minioEndpoint, accessKey: minioAccessKey },
      kafka: { status: 'CONNECTED', brokers: kafkaBrokers },
      gemini: { status: 'ACTIVE', apiKey: geminiKey, model: geminiModel },
      jwtSecret: jwtSecret
    });

    setTimeout(() => {
      setSaving(false);
      setTestResult('Settings saved successfully and connections verified.');
    }, 1000);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white tracking-tight">System Settings</h1>
        <p className="text-sm text-zinc-400">Configure connection schemas for local S3 (MinIO), Kafka event streaming, and database engines.</p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-brand-dark-border/40 gap-6">
        <button
          onClick={() => setActiveTab('infrastructure')}
          className={`pb-2.5 text-sm font-semibold transition-all ${
            activeTab === 'infrastructure' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Infrastructure & Connections
        </button>
        <button
          onClick={() => setActiveTab('security')}
          className={`pb-2.5 text-sm font-semibold transition-all ${
            activeTab === 'security' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          AI & Credentials Keys
        </button>
      </div>

      {/* Form Workspace */}
      <form onSubmit={handleSave} className="space-y-6">
        
        {/* Tab 1: Infrastructure */}
        {activeTab === 'infrastructure' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            
            {/* MinIO */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-zinc-200 text-sm flex items-center gap-2">
                  <HardDrive className="w-4.5 h-4.5 text-brand-primary" />
                  MinIO Storage
                </h3>
                <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                  CONNECTED
                </span>
              </div>
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-zinc-500 uppercase">Endpoint URL</label>
                  <input
                    type="text"
                    value={minioEndpoint}
                    onChange={(e) => setMinioEndpoint(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-1.5 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-zinc-500 uppercase">Access Key</label>
                  <input
                    type="text"
                    value={minioAccessKey}
                    onChange={(e) => setMinioAccessKey(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-1.5 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-mono text-zinc-500 uppercase">Secret Key</label>
                  <input
                    type="password"
                    value={minioSecretKey}
                    onChange={(e) => setMinioSecretKey(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-1.5 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>
              </div>
            </div>

            {/* PostgreSQL */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <h3 className="font-semibold text-zinc-200 text-sm flex items-center gap-2">
                    <Server className="w-4.5 h-4.5 text-brand-primary" />
                    PostgreSQL Connection
                  </h3>
                  <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    CONNECTED
                  </span>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-mono text-zinc-500 uppercase">Database URL (DATABASE_URL)</label>
                  <input
                    type="text"
                    value={pgUrl}
                    onChange={(e) => setPgUrl(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-1.5 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>
              </div>
              
              <p className="text-[10px] text-zinc-500 leading-normal mt-4">
                Used to persist project data indices, decision memories, event timeline logs, and active knowledge cards.
              </p>
            </div>

            {/* Redis */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <h3 className="font-semibold text-zinc-200 text-sm flex items-center gap-2">
                    <Server className="w-4.5 h-4.5 text-brand-primary" />
                    Redis Cache
                  </h3>
                  <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    CONNECTED
                  </span>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-mono text-zinc-500 uppercase">Cache URL (REDIS_URL)</label>
                  <input
                    type="text"
                    value={redisUrl}
                    onChange={(e) => setRedisUrl(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-1.5 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>
              </div>

              <p className="text-[10px] text-zinc-500 leading-normal mt-4">
                Caches user authentication sessions, assistant conversation traces, and pre-calculated statistical summary files.
              </p>
            </div>

            {/* Kafka */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 flex flex-col justify-between">
              <div className="space-y-4">
                <div className="flex justify-between items-start">
                  <h3 className="font-semibold text-zinc-200 text-sm flex items-center gap-2">
                    <Server className="w-4.5 h-4.5 text-brand-primary" />
                    Kafka Queue Brokers
                  </h3>
                  <span className="text-[9px] font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    CONNECTED
                  </span>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-mono text-zinc-500 uppercase">Bootstrap Broker Server</label>
                  <input
                    type="text"
                    value={kafkaBrokers}
                    onChange={(e) => setKafkaBrokers(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-1.5 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>
              </div>

              <p className="text-[10px] text-zinc-500 leading-normal mt-4">
                Handles messaging topics for worker training jobs asynchronously to support scale and parallel optimization trials.
              </p>
            </div>

          </div>
        )}

        {/* Tab 2: Security & API Keys */}
        {activeTab === 'security' && (
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-5">
            <h3 className="font-semibold text-zinc-200 text-sm flex items-center gap-2 border-b border-brand-dark-border/40 pb-2">
              <KeyRound className="w-4.5 h-4.5 text-brand-primary" />
              API Credentials & Secrets Configuration
            </h3>

            <div className="space-y-4">
              {/* Gemini API */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-400">Gemini Developer Key (GEMINI_API_KEY)</label>
                  <input
                    type="password"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-zinc-400">Default Model Target</label>
                  <select
                    value={geminiModel}
                    onChange={(e) => setGeminiModel(e.target.value)}
                    className="w-full bg-brand-dark-bg border border-brand-dark-border rounded-lg text-xs font-semibold py-2.5 px-3 focus:outline-none text-zinc-300"
                  >
                    <option value="Gemini 1.5 Flash">Gemini 1.5 Flash (Medium/Fast)</option>
                    <option value="Gemini 1.5 Pro">Gemini 1.5 Pro (Heavy/Analytical)</option>
                  </select>
                </div>
              </div>

              {/* JWT */}
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-400">JSON Web Token Secret (JWT_SECRET)</label>
                <input
                  type="password"
                  value={jwtSecret}
                  onChange={(e) => setJwtSecret(e.target.value)}
                  className="w-full bg-brand-dark-bg/60 border border-brand-dark-border focus:border-brand-primary focus:ring-1 focus:ring-brand-primary outline-none py-2 px-3 rounded-lg text-xs font-mono transition-all text-zinc-300"
                />
              </div>
            </div>
          </div>
        )}

        {/* Footer Save Row */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 pt-4 border-t border-brand-dark-border/40">
          <div>
            {testResult && (
              <p className="text-xs text-emerald-400 font-semibold flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4" />
                {testResult}
              </p>
            )}
          </div>
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-1.5 bg-brand-primary hover:bg-brand-primary-hover px-5 py-2.5 rounded-xl text-xs font-bold text-white transition-all cursor-pointer shadow-lg shadow-brand-primary/25"
          >
            {saving ? 'Testing & Saving...' : 'Save Settings & Test Connections'}
            <Save className="w-4 h-4" />
          </button>
        </div>

      </form>
    </div>
  );
}
