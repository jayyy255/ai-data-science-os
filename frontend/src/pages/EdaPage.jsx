import React, { useState, useEffect } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { HelpCircle, Sparkles, Info } from 'lucide-react';

export default function EdaPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();
  const [activeTab, setActiveTab] = useState('distributions');

  // Parse dynamic feature distributions
  const distFeatures = project.distributions ? Object.keys(project.distributions) : [];
  const [selectedFeature, setSelectedFeature] = useState('');

  useEffect(() => {
    if (distFeatures.length > 0) {
      setSelectedFeature(distFeatures[0]);
    } else {
      setSelectedFeature('tenure');
    }
  }, [project.id, project.distributions]);

  // Dynamic distribution data or mock fallback
  const distributionData = project.distributions && project.distributions[selectedFeature]
    ? project.distributions[selectedFeature]
    : [
        { bin: '0-10', count: 1400 },
        { bin: '10-20', count: 700 },
        { bin: '20-30', count: 620 },
        { bin: '30-40', count: 500 },
        { bin: '40-50', count: 480 },
        { bin: '50-60', count: 550 },
        { bin: '60-70', count: 720 },
        { bin: '70-80', count: 1350 },
      ];

  // Dynamic target class distribution or mock fallback
  const classData = project.classDistribution && project.classDistribution.length > 0
    ? project.classDistribution
    : [
        { name: 'Retained (No)', count: 36750, color: '#3f3f46' },
        { name: 'Churned (Yes)', count: 13250, color: '#7c3aed' },
      ];

  // Dynamic correlation matrix or mock fallback
  const corrColumns = project.correlations?.columns || ['tenure', 'MonthlyCharges', 'TotalCharges', 'churn'];
  const corrValues = project.correlations?.values || [
    [1.00, 0.24, 0.82, -0.35],
    [0.24, 1.00, 0.65, 0.19],
    [0.82, 0.65, 1.00, -0.19],
    [-0.35, 0.19, -0.19, 1.00]
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-white tracking-tight">Automated EDA</h1>
        <p className="text-sm text-zinc-400">Statistical data profiling and distributions cached in Redis.</p>
      </div>

      {/* Tabs Toggles */}
      <div className="flex border-b border-brand-dark-border/40 gap-6">
        <button
          onClick={() => setActiveTab('distributions')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'distributions' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Feature Distributions
        </button>
        <button
          onClick={() => setActiveTab('correlations')}
          className={`pb-2.5 text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'correlations' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Correlations Matrix
        </button>
      </div>

      {/* Tab 1: Distributions */}
      {activeTab === 'distributions' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Feature distribution Area chart */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-zinc-200 text-sm">Feature Density Distribution</h3>
                  <p className="text-xs text-zinc-500 font-mono">Bimodal density curve peak detection</p>
                </div>
                
                {distFeatures.length > 0 && (
                  <select
                    value={selectedFeature}
                    onChange={(e) => setSelectedFeature(e.target.value)}
                    className="bg-brand-dark-bg border border-brand-dark-border rounded-lg px-2.5 py-1 text-xs font-semibold text-zinc-300 focus:outline-none cursor-pointer"
                  >
                    {distFeatures.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                )}
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={distributionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorFeature" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="bin" stroke="#71717a" fontSize={11} />
                    <YAxis stroke="#71717a" fontSize={11} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                      labelStyle={{ color: '#a78bfa', fontWeight: 'bold' }}
                    />
                    <Area type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2} fillOpacity={1} fill="url(#colorFeature)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Target Variable distribution Bar chart */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <div>
                <h3 className="font-semibold text-zinc-200 text-sm">Target Variable Class Balance ('{project.targetVariable}')</h3>
                <p className="text-xs text-zinc-500 font-mono">Disparity class balance metrics</p>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={classData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="name" stroke="#71717a" fontSize={11} />
                    <YAxis stroke="#71717a" fontSize={11} />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Bar dataKey="count" radius={[8, 8, 0, 0]} maxBarSize={60}>
                      {classData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color || "#7c3aed"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Statistical summary panel */}
          <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-primary" />
              Automated Statistical Insights
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-zinc-400">
              <ul className="space-y-2.5 list-disc pl-4">
                <li>
                  <strong className="text-zinc-200">Data Shape:</strong> Loaded {project.rowsCount?.toLocaleString()} records spanning {project.columnsCount} dimensions.
                </li>
                <li>
                  <strong className="text-zinc-200">Missing Ratio:</strong> Missing value threshold stands at <strong className="text-violet-400 font-mono">{project.missingValuesPct}%</strong> across columns.
                </li>
              </ul>
              <ul className="space-y-2.5 list-disc pl-4">
                <li>
                  <strong className="text-zinc-200">Class Balance:</strong> Target column class balance is mapped dynamically, showing {classData.length} unique labels.
                </li>
                <li>
                  <strong className="text-zinc-200">Imbalance Resolution:</strong> The pipeline is configured to use <strong className="text-amber-400 font-mono">{project.balancingMethod}</strong> strategy for HPO training validation.
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Correlations */}
      {activeTab === 'correlations' && (
        <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-6 space-y-4">
          <div>
            <h3 className="font-semibold text-zinc-200 text-sm">Feature Correlation Coefficient Matrix</h3>
            <p className="text-xs text-zinc-500 font-mono">Linear relationship coefficients (-1 to +1)</p>
          </div>

          {/* Heatmap visualization */}
          <div className="max-w-xl mx-auto space-y-4">
            <div 
              style={{ gridTemplateColumns: `repeat(${corrColumns.length + 1}, minmax(0, 1fr))` }} 
              className="grid gap-1.5 text-center font-mono text-[10px] text-zinc-500"
            >
              <div></div>
              {corrColumns.map((col, idx) => (
                <div key={idx} className="truncate" title={col}>{col}</div>
              ))}
            </div>

            <div className="space-y-1.5">
              {corrColumns.map((rowCol, rIdx) => (
                <div 
                  key={rIdx} 
                  style={{ gridTemplateColumns: `repeat(${corrColumns.length + 1}, minmax(0, 1fr))` }} 
                  className="grid gap-1.5 items-center font-mono text-[10px]"
                >
                  <div className="text-right pr-2 font-semibold text-zinc-400 truncate" title={rowCol}>{rowCol}</div>
                  {corrColumns.map((colCol, cIdx) => {
                    const val = corrValues[rIdx]?.[cIdx] ?? 0;
                    const isDiagonal = rIdx === cIdx;
                    const bgClass = isDiagonal 
                      ? 'bg-brand-primary text-white font-bold' 
                      : val > 0.4 
                        ? 'bg-brand-primary/60 text-white font-bold'
                        : val < -0.2 
                          ? 'bg-red-500/20 text-red-400' 
                          : 'bg-zinc-800 text-zinc-400';
                    return (
                      <div key={cIdx} className={`${bgClass} p-2 text-center rounded`} title={`Correlation between ${rowCol} and ${colCol}`}>
                        {val.toFixed(2)}
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>

            {/* Legend */}
            <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono pt-4 border-t border-brand-dark-border/40">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-brand-primary rounded"></span>
                Strong Positive (&gt; 0.4)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-red-500/20 rounded"></span>
                Strong Negative (&lt; -0.2)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-zinc-800 rounded"></span>
                Weak Correlation
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
