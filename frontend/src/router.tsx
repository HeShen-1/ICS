import { createBrowserRouter, Navigate } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { KnowledgePage } from './pages/KnowledgePage';

function Protected({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
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
  { path: '*', element: <Navigate to="/chat" replace /> },
]);
