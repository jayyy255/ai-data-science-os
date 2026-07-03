import React, { useState } from 'react';
import { useProjectStore } from '../store/useProjectStore';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts';
import { HelpCircle, Sparkles, TrendingUp, Info } from 'lucide-react';

// Sample plotting data for Tenure distribution
const tenureData = [
  { tenure: '0-5 mo', count: 1400 },
  { tenure: '10 mo', count: 700 },
  { tenure: '20 mo', count: 620 },
  { tenure: '30 mo', count: 500 },
  { tenure: '40 mo', count: 480 },
  { tenure: '50 mo', count: 550 },
  { tenure: '60 mo', count: 720 },
  { tenure: '65-72 mo', count: 1350 },
];

// Sample target class Churn data
const classData = [
  { name: 'Retained (No)', count: 36750, color: '#3f3f46' },
  { name: 'Churned (Yes)', count: 13250, color: '#7c3aed' },
];

export default function EdaPage() {
  const { getActiveProject } = useProjectStore();
  const project = getActiveProject();
  const [activeTab, setActiveTab] = useState('distributions');

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
          className={`pb-2.5 text-sm font-semibold transition-all ${
            activeTab === 'distributions' ? 'border-b-2 border-brand-primary text-violet-300' : 'text-zinc-500 hover:text-zinc-300'
          }`}
        >
          Feature Distributions
        </button>
        <button
          onClick={() => setActiveTab('correlations')}
          className={`pb-2.5 text-sm font-semibold transition-all ${
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
            {/* Tenure distribution Area chart */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <div>
                <h3 className="font-semibold text-zinc-200 text-sm">Tenure Longevity Distribution</h3>
                <p className="text-xs text-zinc-500 font-mono">Bimodal density curve peak detection</p>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={tenureData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorTenure" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#7c3aed" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="tenure" stroke="#71717a" fontSize={11} fontClassName="font-mono" />
                    <YAxis stroke="#71717a" fontSize={11} fontClassName="font-mono" />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                      labelStyle={{ color: '#a78bfa', fontWeight: 'bold' }}
                    />
                    <Area type="monotone" dataKey="count" stroke="#7c3aed" strokeWidth={2} fillOpacity={1} fill="url(#colorTenure)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Target Variable distribution Bar chart */}
            <div className="bg-brand-dark-surface border border-brand-dark-border rounded-xl p-5 space-y-4">
              <div>
                <h3 className="font-semibold text-zinc-200 text-sm">Target Variable Class Balance ('{project.targetVariable}')</h3>
                <p className="text-xs text-zinc-500 font-mono">Moderate class distribution disparity</p>
              </div>

              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={classData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#27272a" vertical={false} />
                    <XAxis dataKey="name" stroke="#71717a" fontSize={11} />
                    <YAxis stroke="#71717a" fontSize={11} fontClassName="font-mono" />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#18181b', borderColor: '#3f3f46', borderRadius: '12px' }}
                      itemStyle={{ color: '#fff' }}
                    />
                    <Bar dataKey="count" radius={[8, 8, 0, 0]} maxBarSize={60}>
                      {classData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
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
                  <strong className="text-zinc-200">Bimodal Longevity:</strong> Customer tenure exhibits two distinct peaks—first-month signups (new customers) and 70+ months (highly loyal segment).
                </li>
                <li>
                  <strong className="text-zinc-200">Price Sensitivity:</strong> Customers paying monthly charges above <strong className="text-violet-400 font-mono">$75</strong> have a 4.2x higher rate of churn compared to baseline segments.
                </li>
              </ul>
              <ul className="space-y-2.5 list-disc pl-4">
                <li>
                  <strong className="text-zinc-200">Support Call Threshold:</strong> Customers calling customer support 4 or more times have a <strong className="text-amber-400 font-mono">74% probability</strong> of churning.
                </li>
                <li>
                  <strong className="text-zinc-200">Imbalance Metrics:</strong> Minority class (Churn: Yes) is 26.5%, indicating oversampling techniques like SMOTE or thresholding should be configured for modeling.
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
            <div className="grid grid-cols-5 gap-1.5 text-center font-mono text-xs text-zinc-500">
              <div></div>
              <div className="truncate">tenure</div>
              <div className="truncate">MonthlyCharges</div>
              <div className="truncate">TotalCharges</div>
              <div className="truncate">churn</div>
            </div>

            <div className="space-y-1.5">
              {/* Row 1 */}
              <div className="grid grid-cols-5 gap-1.5 items-center font-mono text-xs">
                <div className="text-right pr-2 font-semibold text-zinc-400 truncate">tenure</div>
                <div className="bg-brand-primary p-3 text-white rounded font-bold">1.00</div>
                <div className="bg-zinc-800 p-3 text-zinc-400 rounded">0.24</div>
                <div className="bg-brand-primary/80 p-3 text-white rounded font-bold">0.82</div>
                <div className="bg-red-500/20 p-3 text-red-400 rounded">-0.35</div>
              </div>
              
              {/* Row 2 */}
              <div className="grid grid-cols-5 gap-1.5 items-center font-mono text-xs">
                <div className="text-right pr-2 font-semibold text-zinc-400 truncate">MonthlyCharges</div>
                <div className="bg-zinc-800 p-3 text-zinc-400 rounded">0.24</div>
                <div className="bg-brand-primary p-3 text-white rounded font-bold">1.00</div>
                <div className="bg-brand-primary/50 p-3 text-white rounded font-bold">0.65</div>
                <div className="bg-brand-primary/20 p-3 text-violet-300 rounded">0.19</div>
              </div>

              {/* Row 3 */}
              <div className="grid grid-cols-5 gap-1.5 items-center font-mono text-xs">
                <div className="text-right pr-2 font-semibold text-zinc-400 truncate">TotalCharges</div>
                <div className="bg-brand-primary/80 p-3 text-white rounded font-bold">0.82</div>
                <div className="bg-brand-primary/50 p-3 text-white rounded font-bold">0.65</div>
                <div className="bg-brand-primary p-3 text-white rounded font-bold">1.00</div>
                <div className="bg-red-500/10 p-3 text-red-300 rounded">-0.19</div>
              </div>

              {/* Row 4 */}
              <div className="grid grid-cols-5 gap-1.5 items-center font-mono text-xs">
                <div className="text-right pr-2 font-semibold text-zinc-400 truncate">churn</div>
                <div className="bg-red-500/20 p-3 text-red-400 rounded">-0.35</div>
                <div className="bg-brand-primary/20 p-3 text-violet-300 rounded">0.19</div>
                <div className="bg-red-500/10 p-3 text-red-300 rounded">-0.19</div>
                <div className="bg-brand-primary p-3 text-white rounded font-bold">1.00</div>
              </div>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono pt-4 border-t border-brand-dark-border/40">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-brand-primary rounded"></span>
                Strong Positive (&gt; 0.6)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-red-500/20 rounded"></span>
                Strong Negative (&lt; -0.3)
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-zinc-800 rounded"></span>
                Weak Correlation (0.0 to 0.3)
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
