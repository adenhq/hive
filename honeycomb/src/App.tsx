import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AgentControlLayout } from './components/agent-control/AgentControlLayout';
import { DataPanel } from './components/agent-control/DataPanel';
import { AnalyticsPanel } from './components/agent-control/AnalyticsPanel';
import { CostControls } from './components/agent-control/CostControls';
import { WorkersPanel } from './components/agent-control/WorkersPanel';
import { NotFoundPage } from './pages/NotFoundPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ProtectedRoute } from './components/auth/ProtectedRoute';

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/:org/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/:org/register" element={<RegisterPage />} />

        {/* Protected routes */}
        <Route path="/" element={<Navigate to="/agents" replace />} />
        <Route
          element={
            <ProtectedRoute>
              <AgentControlLayout />
            </ProtectedRoute>
          }
        >
          <Route path="agents" element={<WorkersPanel />} />
          <Route path="data" element={<DataPanel />} />
          <Route path="performance-dashboard" element={<AnalyticsPanel />} />
          <Route path="cost-control" element={<CostControls />} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  );
}
