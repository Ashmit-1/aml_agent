import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';

export const useAuth = () => {
  const { isLoading, validateToken } = useAuthStore();

  useEffect(() => {
    validateToken();
  }, [validateToken]);

  return { isLoading };
};
