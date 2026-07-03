import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useProjectStore } from './store/useProjectStore';

import Layout from './components/Layout';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CreateProjectPage from './pages/CreateProjectPage';
import ProjectOverviewPage from './pages/ProjectOverviewPage';
import DatasetIntelligencePage from './pages/DatasetIntelligencePage';
import EdaPage from './pages/EdaPage';
import FeatureEngineeringPage from './pages/FeatureEngineeringPage';
import TrainingPage from './pages/TrainingPage';
import ExplainabilityPage from './pages/ExplainabilityPage';
import TimelinePage from './pages/TimelinePage';
import KnowledgeCardPage from './pages/KnowledgeCardPage';
import AiAssistantPage from './pages/AiAssistantPage';
import ModelRegistryPage from './pages/ModelRegistryPage';
import MonitoringPage from './pages/MonitoringPage';
import SettingsPage from './pages/SettingsPage';

// Guard component to protect pages requiring active login sessions
function PrivateRoute({ children }) {
  const currentUser = useProjectStore((state) => state.currentUser);
  return currentUser ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Auth Route */}
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Application Routes */}
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/create-project" element={<CreateProjectPage />} />
                  <Route path="/overview" element={<ProjectOverviewPage />} />
                  <Route path="/dataset" element={<DatasetIntelligencePage />} />
                  <Route path="/eda" element={<EdaPage />} />
                  <Route path="/features" element={<FeatureEngineeringPage />} />
                  <Route path="/training" element={<TrainingPage />} />
                  <Route path="/explainability" element={<ExplainabilityPage />} />
                  <Route path="/timeline" element={<TimelinePage />} />
                  <Route path="/knowledge-card" element={<KnowledgeCardPage />} />
                  <Route path="/assistant" element={<AiAssistantPage />} />
                  <Route path="/registry" element={<ModelRegistryPage />} />
                  <Route path="/monitoring" element={<MonitoringPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </Router>
  );
}
