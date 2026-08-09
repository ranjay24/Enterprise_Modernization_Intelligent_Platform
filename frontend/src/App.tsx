import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppLayout } from '@/layouts/AppLayout';
import { AuthProvider, useAuth } from '@/auth/AuthContext';
import DashboardPage from '@/pages/DashboardPage';
import UploadPage from '@/pages/UploadPage';
import AnalysisPage from '@/pages/AnalysisPage';
import ResultsPage from '@/pages/ResultsPage';
import JobsPage from '@/pages/JobsPage';
import ArchitecturePage from '@/pages/ArchitecturePage';
import ModernizationStudioPage from '@/pages/ModernizationStudioPage';
import StudioIndexPage from '@/pages/StudioIndexPage';
import MigrationPlannerPage from '@/pages/MigrationPlannerPage';
import ReportsPage from '@/pages/ReportsPage';
import SettingsPage from '@/pages/SettingsPage';
import LoginPage from '@/pages/LoginPage';
import SignupPage from '@/pages/SignupPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const AUTH_ROUTES = new Set(['/login', '/signup']);

function SplashScreen() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-[var(--bg-base)]">
      <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--accent-blue)] to-[var(--accent-purple)] animate-pulse" />
      <p className="text-sm text-[var(--text-muted)]">Loading EMIP…</p>
    </div>
  );
}

function AppRoutes() {
  const { status } = useAuth();
  const location = useLocation();
  const onAuthRoute = AUTH_ROUTES.has(location.pathname);

  if (status === 'loading') return <SplashScreen />;

  if (status === 'unauthenticated' && !onAuthRoute) {
    return <Navigate to="/login" replace />;
  }
  if (status === 'authenticated' && onAuthRoute) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/jobs" element={<JobsPage />} />
        <Route path="/jobs/:jobId" element={<AnalysisPage />} />
        <Route path="/jobs/:jobId/results" element={<ResultsPage />} />
        <Route path="/jobs/:jobId/studio" element={<ModernizationStudioPage />} />
        <Route path="/architecture" element={<ArchitecturePage />} />
        <Route path="/studio" element={<StudioIndexPage />} />
        <Route path="/migration" element={<MigrationPlannerPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
