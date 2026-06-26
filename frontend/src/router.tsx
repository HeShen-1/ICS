import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { KnowledgePage } from './pages/KnowledgePage';
import { StatsPage } from './pages/StatsPage';
import { AgentPage } from './pages/AgentPage';
import { useAuthStore } from './stores/authStore';

function Protected({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    path: '/chat',
    element: <Protected><ChatPage /></Protected>,
  },
  {
    path: '/chat/:sessionId',
    element: <Protected><ChatPage /></Protected>,
  },
  {
    path: '/knowledge',
    element: <Protected><KnowledgePage /></Protected>,
  },
  {
    path: '/stats',
    element: <Protected><StatsPage /></Protected>,
  },
  {
    path: '/agent',
    element: <Protected><AgentPage /></Protected>,
  },
  { path: '*', element: <Navigate to="/chat" replace /> },
]);
