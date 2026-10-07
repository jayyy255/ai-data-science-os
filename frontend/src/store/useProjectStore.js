import { create } from 'zustand';
import api, { errorMessage } from '../api';

const emptyProject = {
  id: '', name: '', targetVariable: '', problemType: '', status: '', description: '',
  bestModel: 'None', bestF1: null, bestAccuracy: null, bestMse: null,
  rowsCount: 0, columnsCount: 0, missingValuesPct: 0, balancingMethod: 'None',
  modelsTestedCount: 0, topFeatures: [], features: [], featureEngineeringDecisions: [],
  timeline: [], hpoTrials: [], shapGlobal: [], shapLocal: { probability: 0, drivers: [] },
  distributions: {}, correlations: { columns: [], values: [] }, classDistribution: [],
  structure: { numerical: 0, categorical: 0, datetime: 0, text: 0 }, qualityHealth: {},
  monitoring: { driftPsi: null, driftStatus: 'No monitoring dataset', driftAlerts: [] },
};
function mapProject(project, card = {}, eda = project.eda_profile_json || {}) {
  return {
    ...emptyProject, id: project.id, name: project.name, targetVariable: project.target_variable,
    problemType: project.problem_type, status: project.status, description: project.description,
    bestModel: card.best_model ?? 'None', bestF1: card.best_f1 ?? null,
    bestAccuracy: card.best_accuracy ?? null, bestMse: card.best_mse ?? null,
    rowsCount: eda.rows_count ?? card.rows_count ?? 0, columnsCount: eda.columns_count ?? card.columns_count ?? 0,
    missingValuesPct: Number((eda.missing_pct ?? card.missing_values_pct ?? 0).toFixed(2)),
    balancingMethod: card.balancing_method ?? 'None', modelsTestedCount: card.models_tested_count ?? 0,
    topFeatures: card.top_features ?? [], modelPath: card.model_path,
    modelsComparison: card.models_comparison_json ?? {}, shapGlobal: card.shap_global_json ?? [],
    shapLocal: card.shap_local_json ?? emptyProject.shapLocal, edaAnalysis: project.eda_analysis,
    qualityHealth: eda.quality_health ?? {}, features: eda.features ?? [],
    classDistribution: eda.class_distribution ?? [], correlations: eda.correlations ?? emptyProject.correlations,
    distributions: eda.distributions ?? {},
    structure: { numerical: eda.numerical_count ?? 0, categorical: eda.categorical_count ?? 0, datetime: 0, text: 0 },
  };
}
export const useProjectStore = create((set, get) => ({
  projects: [], activeProjectId: localStorage.getItem('aidso-active-project') || '',
  projectJobs: {}, chatHistories: {}, error: '', loading: false, authReady: false,
  currentUser: (() => { try { return JSON.parse(localStorage.getItem('aidso-user') || 'null'); } catch { return null; } })(),
  connections: {},
  initializeAuth: async () => {
    try {
      const { data } = await api.get('/auth/me');
      if (!data.user) {
        localStorage.removeItem('aidso-user');
        set({ currentUser: null, projects: [], activeProjectId: '' });
      } else set(state => ({ currentUser: { ...state.currentUser, ...data.user } }));
    } catch (err) { set({ error: errorMessage(err) }); }
    finally { set({ authReady: true }); }
  },
  getActiveProject: () => get().projects.find(p => p.id === get().activeProjectId) || emptyProject,
  clearError: () => set({ error: '' }),
  setActiveProjectId: (id) => {
    localStorage.setItem('aidso-active-project', id);
    set({ activeProjectId: id });
    get().fetchProjectDetails(id).catch(() => {});
    get().fetchProjectJobs(id);
  },
  getChatHistory: (id, name) => get().chatHistories[id] || [{ sender: 'ai', text: `Ask about ${name}'s dataset, preprocessing, or model results.` }],
  addChatMessage: (id, message) => set(state => ({ chatHistories: { ...state.chatHistories, [id]: [...(state.chatHistories[id] || []), message] } })),
  fetchProjectJobs: async (id) => {
    if (!id) return;
    try {
      const { data } = await api.get(`/projects/${id}/jobs`);
      set(state => ({ projectJobs: { ...state.projectJobs, [id]: data.jobs } }));
      return data.jobs;
    } catch (err) { set({ error: errorMessage(err) }); }
  },
  login: async (identity, password) => {
    try {
      const { data } = await api.post('/auth/login', { identity, password });
      const user = { ...data.user, refreshToken: data.refreshToken };
      localStorage.setItem('aidso-user', JSON.stringify(user));
      set({ currentUser: user, projects: [], activeProjectId: '', error: '' });
      return { success: true };
    } catch (err) { return { success: false, error: errorMessage(err) }; }
  },
  signup: async (fullName, username, email, password) => {
    try {
      const { data } = await api.post('/auth/signup', { full_name: fullName, username, email, password });
      const user = { ...data.user, refreshToken: data.refreshToken };
      localStorage.setItem('aidso-user', JSON.stringify(user));
      set({ currentUser: user, projects: [], activeProjectId: '', error: '' });
      return { success: true };
    } catch (err) { return { success: false, error: errorMessage(err) }; }
  },
  logout: async () => {
    try { await api.post('/auth/logout', { refresh_token: get().currentUser?.refreshToken }); }
    finally {
      localStorage.removeItem('aidso-user'); localStorage.removeItem('aidso-active-project');
      set({ currentUser: null, projects: [], activeProjectId: '', projectJobs: {}, chatHistories: {}, error: '' });
    }
  },
  forgotPassword: async (email) => {
    try { const { data } = await api.post('/auth/forgot-password', { email }); return { success: true, message: data.message }; }
    catch (err) { return { success: false, error: errorMessage(err) }; }
  },
  updateConnections: (connections) => set({ connections }),
  fetchProjects: async () => {
    const user = get().currentUser;
    if (!user) return;
    set({ loading: true });
    try {
      const { data } = await api.get('/projects');
      if (get().currentUser?.username !== user.username) return;
      const projects = data.map(p => ({ ...mapProject(p), ...get().projects.find(old => old.id === p.id), status: p.status }));
      const id = projects.some(p => p.id === get().activeProjectId) ? get().activeProjectId : projects[0]?.id || '';
      localStorage.setItem('aidso-active-project', id);
      set({ projects, activeProjectId: id, error: '' });
      await Promise.all(projects.map(p => get().fetchProjectDetails(p.id)));
    } catch (err) { set({ error: errorMessage(err) }); }
    finally { set({ loading: false }); }
  },
  fetchProjectDetails: async (id) => {
    if (!id) return;
    try {
      const { data } = await api.get(`/projects/${id}`);
      const mapped = mapProject(data.project, data.knowledge_card || {}, data.cached_eda || data.project.eda_profile_json || {});
      mapped.timeline = (data.timeline || []).map(t => ({ time: new Date(t.timestamp.endsWith('Z') ? t.timestamp : t.timestamp + 'Z').toLocaleString(), title: t.title, desc: t.description, type: t.event_type }));
      mapped.featureEngineeringDecisions = (data.decisions || []).map(d => ({ feature: d.feature_name, decision: d.decision, reason: d.reason, confidence: d.confidence, overrideActive: d.override_active, userChoice: d.user_choice, comparisonMetrics: d.comparison_metrics_json }));
      mapped.hpoTrials = data.hpo_trials || [];
      set(state => ({ projects: state.projects.some(p => p.id === id) ? state.projects.map(p => p.id === id ? mapped : p) : state.projects }));
      return mapped;
    } catch (err) { set({ error: errorMessage(err) }); throw err; }
  },
  createProject: async (name, targetVariable, description, file, problemType = 'auto') => {
    const form = new FormData();
    form.append('name', name.trim()); form.append('target_variable', targetVariable.trim());
    form.append('description', description); form.append('file', file); form.append('problem_type', problemType);
    try {
      const { data } = await api.post('/projects', form);
      const project = mapProject(data.project);
      localStorage.setItem('aidso-active-project', project.id);
      set(state => ({ projects: [...state.projects, project], activeProjectId: project.id, error: '' }));
      await get().fetchProjectDetails(project.id);
      return project.id;
    } catch (err) { set({ error: errorMessage(err) }); throw err; }
  },
  applyOverride: async (id, feature, choice) => get().applyFeatureTransformation(id, feature, choice),
  applyFeatureTransformation: async (id, feature, transformation) => {
    const { data } = await api.post(`/projects/${id}/transform`, { feature_name: feature, transformation });
    await get().fetchProjectDetails(id);
    return data;
  },
  triggerTraining: async (id, method = 'Median') => {
    try {
      await api.post(`/projects/${id}/train`, null, { params: { imputation_method: method } });
      await get().fetchProjectDetails(id);
      await get().fetchProjectJobs(id);
    } catch (err) { set({ error: errorMessage(err) }); throw err; }
  },
}));
