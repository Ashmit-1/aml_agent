import { Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { FluxGuardLogo } from '@/components/FluxGuardLogo';
import { UserMenu } from '@/components/UserMenu';

export const HeroSection = () => {
  const { isAuthenticated } = useAuthStore();

  return (
    <section className="relative flex flex-col items-center justify-center min-h-[80vh] px-4 text-center">
      {/* User menu in top-right when logged in */}
      {isAuthenticated && (
        <div className="fixed top-4 right-4 z-50">
          <UserMenu align="right" />
        </div>
      )}

      <div className="max-w-3xl mx-auto space-y-8">
        {/* Logo */}
        <div className="flex justify-center">
          <div className="flex items-center justify-center">
            <FluxGuardLogo size={48} />
          </div>
        </div>

        {/* Title */}
        <h1 className="text-4xl md:text-6xl font-medium tracking-tight">
          FluxGuard
        </h1>

        {/* Subtitle */}
        <p className="text-lg md:text-xl text-gray-400 max-w-2xl mx-auto">
          An AI-powered agent that analyses ~9.5M synthetic bank transactions to
          detect money-laundering patterns
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link to="/chat">
            <Button className="bg-white text-black hover:bg-gray-200 px-8 py-6 text-base">
              Try Now
            </Button>
          </Link>

          {isAuthenticated ? (
            <Link to="/chat">
              <Button
                variant="secondary"
                className="px-8 py-6 text-base"
              >
                Go to Chat
              </Button>
            </Link>
          ) : (
            <Link to="/login">
              <Button
                variant="secondary"
                className="px-8 py-6 text-base"
              >
                Login
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Decorative gradient */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black to-transparent" />
    </section>
  );
};
