import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { BackendStatusBanner } from '@/components/ui/BackendStatusBanner';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { AuthRedirect } from '@/components/AuthRedirect';
import { LandingPage } from '@/components/landing/LandingPage';
import { LoginPage } from '@/components/auth/LoginPage';
import { SignupPage } from '@/components/auth/SignupPage';
import { ChatInterface } from '@/components/ChatInterface';

/**
 * Wraps routes with a subtle fade-in-up animation on route change.
 * The `key={location.pathname}` forces React to treat each route as a new
 * element, triggering the CSS animation each time the path changes.
 */
const AnimatedRoutes = () => {
  const location = useLocation();

  return (
    <div key={location.pathname} className="animate-fade-in-up min-h-screen">
      <Routes location={location}>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/login"
          element={
            <AuthRedirect>
              <LoginPage />
            </AuthRedirect>
          }
        />
        <Route
          path="/signup"
          element={
            <AuthRedirect>
              <SignupPage />
            </AuthRedirect>
          }
        />
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatInterface />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
};

const App = () => {
  const { isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <BrowserRouter>
      <BackendStatusBanner />
      <AnimatedRoutes />
    </BrowserRouter>
  );
};

export default App;
