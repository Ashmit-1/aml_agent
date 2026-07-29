import { Link } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';

export const LandingFooter = () => {
  const { isAuthenticated } = useAuthStore();

  return (
    <footer className="py-20 px-4 border-t border-white/10">
      <div className="max-w-2xl mx-auto text-center space-y-8">
        <h2 className="text-3xl md:text-4xl font-medium">
          Ready to analyse transactions?
        </h2>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          {!isAuthenticated && (
            <Link to="/signup">
              <Button className="bg-white text-black hover:bg-gray-200 px-8 py-6 text-base">
                Sign Up
              </Button>
            </Link>
          )}
          <Link to={isAuthenticated ? '/chat' : '/login'}>
            <Button
              variant="secondary"
              className="px-8 py-6 text-base"
            >
              {isAuthenticated ? 'Go to Chat' : 'Login'}
            </Button>
          </Link>
        </div>
      </div>
    </footer>
  );
};
