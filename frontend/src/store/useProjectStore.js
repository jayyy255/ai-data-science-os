import { create } from 'zustand';

// Seed mock data for Customer Churn Prediction (Default Project)
const defaultChurnProject = {
  id: 'churn-prediction',
  name: 'Customer Churn Prediction',
  targetVariable: 'churn',
  problemType: 'classification',
  description: 'Predict customer churn and identify key factors influencing customer attrition to drive retention programs.',
  status: 'Ready for Deployment',
  bestModel: 'XGBoost',
  bestF1: 0.913,
  bestAccuracy: 0.892,
  rowsCount: 50000,
  columnsCount: 42,
  missingValuesPct: 3.2,
  balancingMethod: 'SMOTE',
  modelsTestedCount: 5,
  topFeatures: ['tenure', 'MonthlyCharges', 'support_calls'],
  structure: {
    numerical: 18,
    categorical: 20,
    datetime: 2,
    text: 2,
  },
  qualityHealth: {
    missingValues: '3.2% handled (1,600 values tenure/TotalCharges)',
    duplicates: '0 duplicates',
    outliers: 'Outliers detected in MonthlyCharges/TotalCharges (handled)',
    classImbalance: 'Target Churn: Yes = 26.5%, No = 73.5%',
    invalidDataTypes: '0 invalid data types',
  },
  features: [
    { name: 'customerID', type: 'object (categorical)', missing: 0, unique: 50000, sample: '7590-VHVEG', quality: 'Good (ID)' },
    { name: 'gender', type: 'object (categorical)', missing: 0, unique: 2, sample: 'Female', quality: 'Good' },
    { name: 'SeniorCitizen', type: 'int64 (numerical)', missing: 0, unique: 2, sample: '0', quality: 'Good' },
    { name: 'tenure', type: 'int64 (numerical)', missing: 3.2, unique: 73, sample: '1 month', quality: 'Imputed (Median)' },
    { name: 'MonthlyCharges', type: 'float64 (numerical)', missing: 0, unique: 1585, sample: '29.85', quality: 'Scaled (Standard)' },
    { name: 'TotalCharges', type: 'float64 (numerical)', missing: 1.2, unique: 4890, sample: '29.85', quality: 'Imputed (Median)' },
    { name: 'support_calls', type: 'int64 (numerical)', missing: 0, unique: 10, sample: '3 calls', quality: 'User Overridden (Raw)' },
    { name: 'contract_type', type: 'object (categorical)', missing: 0, unique: 3, sample: 'Month-to-month', quality: 'Encoded (One-Hot)' },
    { name: 'payment_method', type: 'object (categorical)', missing: 0, unique: 4, sample: 'Electronic check', quality: 'Encoded (One-Hot)' },
  ],
  featureEngineeringDecisions: [
    { feature: 'tenure', decision: 'Median Imputation', reason: 'Outliers and missing values detected', confidence: 0.91, overrideActive: false },
    { feature: 'payment_method', decision: 'One-Hot Encoding', reason: 'Low cardinality categorical feature (4 values)', confidence: 0.95, overrideActive: false },
    { feature: 'MonthlyCharges', decision: 'Standard Scaling', reason: 'Skewed continuous distribution', confidence: 0.88, overrideActive: false },
    { feature: 'support_calls', decision: 'Keep Raw Numerical', reason: 'User override: preserve raw counts instead of suggested binning', confidence: 0.85, overrideActive: true, userChoice: 'Keep Raw' },
  ],
  hpoTrials: [
    { trial: 46, params: { max_depth: 6, learning_rate: 0.05, n_estimators: 250 }, f1: 0.913, status: 'Completed (Best)' },
    { trial: 45, params: { max_depth: 8, learning_rate: 0.01, n_estimators: 300 }, f1: 0.898, status: 'Completed' },
    { trial: 44, params: { max_depth: 5, learning_rate: 0.1, n_estimators: 150 }, f1: 0.891, status: 'Completed' },
    { trial: 43, params: { max_depth: 4, learning_rate: 0.05, n_estimators: 200 }, f1: 0.882, status: 'Completed' },
    { trial: 42, params: { max_depth: 6, learning_rate: 0.2, n_estimators: 100 }, f1: 0.875, status: 'Completed' },
  ],
  timeline: [
    { time: '10:14 AM', title: 'Knowledge Card Updated', desc: 'L1, L2, L3 summaries regenerated based on champion XGBoost metrics.', type: 'info' },
    { time: '10:12 AM', title: 'Best Model Selected', desc: 'XGBoost (Trial 46) selected as Champion with F1 score of 0.913.', type: 'success' },
    { time: '10:10 AM', title: 'Model Training Completed', desc: 'Optuna completed 46/100 HPO trials. Saved metrics to MLflow registry.', type: 'info' },
    { time: '09:45 AM', title: 'Model Training Started', desc: 'Published training requests to Kafka topic. Training worker-1 active.', type: 'info' },
    { time: '09:30 AM', title: 'Feature Engineering Applied', desc: 'Computed scaling and encoding. User overrode support_calls scaling.', type: 'warning' },
    { time: '09:12 AM', title: 'EDA Generated', desc: 'Statistical metrics and correlations calculated. Cached results in Redis.', type: 'info' },
    { time: '09:05 AM', title: 'Project Understood', desc: 'Gemini API analyzed business goal. Determined classification task targeting Churn.', type: 'info' },
    { time: '09:00 AM', title: 'Dataset Uploaded', desc: 'churn_data.csv (12.8 MB) uploaded to MinIO storage bucket.', type: 'success' },
  ],
  shapGlobal: [
    { feature: 'tenure', shap: -0.32, type: 'Negative impact (reduces churn)' },
    { feature: 'MonthlyCharges', shap: 0.24, type: 'Positive impact (increases churn)' },
    { feature: 'support_calls', shap: 0.18, type: 'Positive impact (increases churn)' },
    { feature: 'contract_type=Month-to-month', shap: 0.15, type: 'Positive impact (increases churn)' },
    { feature: 'payment_method=Electronic check', shap: 0.08, type: 'Positive impact' },
    { feature: 'gender=Male', shap: 0.01, type: 'Muted impact' },
  ],
  shapLocal: {
    customerId: 'US-8594-QD',
    probability: 0.842,
    risk: 'High Risk',
    drivers: [
      { feature: 'MonthlyCharges', value: '$110/mo', impact: '+23.1% (Increases risk)' },
      { feature: 'tenure', value: '3 months', impact: '+18.4% (Increases risk)' },
      { feature: 'support_calls', value: '5 calls', impact: '+14.2% (Increases risk)' },
      { feature: 'contract_type', value: 'Month-to-month', impact: '+8.5% (Increases risk)' },
    ]
  },
  monitoring: {
    driftPsi: 0.24,
    driftStatus: 'DRIFT DETECTED',
    driftAlerts: [
      { id: 1, time: '2 hours ago', severity: 'critical', feature: 'MonthlyCharges', message: 'Critical data drift detected. PSI 0.24 > 0.20 threshold. Inferences shifting to higher charges.' },
      { id: 2, time: '1 day ago', severity: 'warning', feature: 'support_calls', message: 'Moderate distribution shift observed. PSI = 0.14.' }
    ]
  }
};

// Seed mock data for second project
const defaultDemandProject = {
  id: 'demand-forecasting',
  name: 'Retail Demand Forecasting',
  targetVariable: 'quantity_sold',
  problemType: 'regression',
  description: 'Forecast retail product demand for inventory optimization using historical sales and temporal markers.',
  status: 'Training',
  bestModel: 'LightGBM Regressor',
  bestF1: null,
  bestAccuracy: null,
  rowsCount: 250000,
  columnsCount: 15,
  missingValuesPct: 0.1,
  balancingMethod: 'None',
  modelsTestedCount: 2,
  topFeatures: ['promo_active', 'prev_week_sales', 'store_id'],
  structure: {
    numerical: 8,
    categorical: 5,
    datetime: 2,
    text: 0,
  },
  qualityHealth: {
    missingValues: '0.1% handled',
    duplicates: '0 duplicates',
    outliers: 'No critical outliers',
    classImbalance: 'Not applicable (regression)',
    invalidDataTypes: '0 invalid data types',
  },
  features: [
    { name: 'date', type: 'datetime', missing: 0, unique: 1095, sample: '2023-01-01', quality: 'Good' },
    { name: 'store_id', type: 'object (categorical)', missing: 0, unique: 45, sample: 'Store-04', quality: 'Encoded' },
    { name: 'item_id', type: 'object (categorical)', missing: 0, unique: 120, sample: 'Item-893', quality: 'Encoded' },
    { name: 'quantity_sold', type: 'int64 (numerical)', missing: 0, unique: 580, sample: '45 units', quality: 'Target' },
    { name: 'promo_active', type: 'int64 (numerical)', missing: 0, unique: 2, sample: '1', quality: 'Good' },
  ],
  featureEngineeringDecisions: [
    { feature: 'date', decision: 'Temporal Feature Extraction', reason: 'Extract month, day of week, season', confidence: 0.98, overrideActive: false },
    { feature: 'store_id', decision: 'Target Encoding', reason: 'High cardinality categorical feature', confidence: 0.92, overrideActive: false },
  ],
  hpoTrials: [
    { trial: 12, params: { learning_rate: 0.05, num_leaves: 31, max_depth: -1 }, f1: 0.881, status: 'Running' },
    { trial: 11, params: { learning_rate: 0.01, num_leaves: 63, max_depth: 8 }, f1: 0.865, status: 'Completed' },
  ],
  timeline: [
    { time: '1 hour ago', title: 'HPO Search Fired', desc: 'Optuna optimization job triggered via Kafka training workers.', type: 'info' },
    { time: '2 hours ago', title: 'Dataset Uploaded', desc: 'sales_historical.csv (38.4 MB) stored in MinIO.', type: 'success' },
  ],
  shapGlobal: [
    { feature: 'promo_active', shap: 0.45, type: 'Positive impact' },
    { feature: 'prev_week_sales', shap: 0.38, type: 'Positive impact' },
  ],
  shapLocal: {
    customerId: 'Store-04_Item-893',
    probability: 0.72,
    risk: 'Normal',
    drivers: [
      { feature: 'promo_active', value: 'Active', impact: '+35 units demand' }
    ]
  },
  monitoring: {
    driftPsi: 0.08,
    driftStatus: 'HEALTHY',
    driftAlerts: []
  }
};

export const useProjectStore = create((set, get) => ({
  projects: [defaultChurnProject, defaultDemandProject],
  activeProjectId: 'churn-prediction',
  currentUser: { email: 'datascientist@company.ai', token: 'mock-jwt-token-123' },
  
  // Environment Connections state
  connections: {
    postgresql: { status: 'CONNECTED', url: 'postgresql://postgres:postgres@localhost:5432/aidso' },
    redis: { status: 'CONNECTED', url: 'redis://localhost:6379/0' },
    minio: { status: 'CONNECTED', endpoint: 'localhost:9000', accessKey: 'admin' },
    kafka: { status: 'CONNECTED', brokers: 'localhost:9092' },
    gemini: { status: 'ACTIVE', apiKey: '', model: 'Gemini 1.5 Flash' },
    jwtSecret: ''
  },
  
  // Get currently active project
  getActiveProject: () => {
    const state = get();
    return state.projects.find(p => p.id === state.activeProjectId) || defaultChurnProject;
  },

  setActiveProjectId: (id) => set({ activeProjectId: id }),

  // Auth actions
  login: (email, password) => {
    set({ currentUser: { email, token: 'mock-jwt-token-new' } });
  },
  logout: () => set({ currentUser: null }),
  
  // Settings actions
  updateConnections: (newConnections) => set((state) => ({
    connections: { ...state.connections, ...newConnections }
  })),

  // Add project (Create Project flow)
  createProject: (name, description, targetVariable, datasetName, datasetSize) => {
    const newProject = {
      id: name.toLowerCase().replace(/\s+/g, '-'),
      name,
      targetVariable,
      problemType: 'classification', // default, updated by AI understanding
      description,
      status: 'Dataset Analysis',
      bestModel: 'None',
      bestF1: null,
      rowsCount: 25000,
      columnsCount: 12,
      missingValuesPct: 1.5,
      balancingMethod: 'None',
      modelsTestedCount: 0,
      topFeatures: [],
      structure: { numerical: 6, categorical: 6, datetime: 0, text: 0 },
      qualityHealth: {
        missingValues: '1.5% missing',
        duplicates: '0 duplicates',
        outliers: 'None',
        classImbalance: 'Imbalance detected',
        invalidDataTypes: '0 invalid data types',
      },
      features: [
        { name: 'id', type: 'object', missing: 0, unique: 25000, sample: '1023', quality: 'Good' },
        { name: targetVariable, type: 'int64', missing: 0, unique: 2, sample: '0', quality: 'Target' }
      ],
      featureEngineeringDecisions: [],
      hpoTrials: [],
      timeline: [
        { time: new Date().toLocaleTimeString(), title: 'Dataset Uploaded', desc: `${datasetName} (${datasetSize}) uploaded to MinIO.`, type: 'success' },
        { time: new Date().toLocaleTimeString(), title: 'Project Initialized', desc: `Project structure initialized in PostgreSQL.`, type: 'info' }
      ],
      shapGlobal: [],
      shapLocal: { customerId: 'N/A', probability: 0, risk: 'Normal', drivers: [] },
      monitoring: { driftPsi: 0, driftStatus: 'HEALTHY', driftAlerts: [] }
    };
    
    set((state) => ({
      projects: [...state.projects, newProject],
      activeProjectId: newProject.id
    }));
  },

  // Apply user override for Feature Engineering
  applyOverride: (projectId, featureName, userChoice) => {
    set((state) => ({
      projects: state.projects.map((p) => {
        if (p.id !== projectId) return p;
        return {
          ...p,
          featureEngineeringDecisions: p.featureEngineeringDecisions.map((d) => {
            if (d.feature !== featureName) return d;
            return {
              ...d,
              overrideActive: true,
              userChoice: userChoice
            };
          }),
          timeline: [
            {
              time: new Date().toLocaleTimeString(),
              title: 'Feature Overridden',
              desc: `User overrode transformation for feature '${featureName}' to: ${userChoice}`,
              type: 'warning'
            },
            ...p.timeline
          ]
        };
      })
    }));
  },

  // Simulate training start via Kafka
  triggerTraining: (projectId) => {
    set((state) => ({
      projects: state.projects.map((p) => {
        if (p.id !== projectId) return p;
        return {
          ...p,
          status: 'Training',
          timeline: [
            {
              time: new Date().toLocaleTimeString(),
              title: 'Model Training Started',
              desc: 'Training request successfully dispatched to Kafka model-training-tasks broker.',
              type: 'info'
            },
            ...p.timeline
          ]
        };
      })
    }));
  }
}));
