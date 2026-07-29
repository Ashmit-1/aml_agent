import { useState, useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';
import { apiFetch } from '@/services/api';

/**
 * Fixed banner at the top of the page that checks backend health on mount.
 * Shows a red warning banner when the backend is unreachable.
 * Retries every 30s while offline. Dismissable by the user.
 */
export const BackendStatusBanner = () => {
  const [status, setStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    let mounted = true;
    let retryTimeout: ReturnType<typeof setTimeout>;

    const checkHealth = async () => {
      try {
        // Any HTTP response (even 401 or 500) means the server is reachable
        await apiFetch('/api/health', { skip401Redirect: true });
        if (!mounted) return;
        setStatus('online');
      } catch {
        // Network error / no response — server is unreachable
        if (!mounted) return;
        setStatus('offline');
        retryTimeout = setTimeout(checkHealth, 30000);
      }
    };

    checkHealth();

    return () => {
      mounted = false;
      clearTimeout(retryTimeout);
    };
  }, []);

  // Only show when offline and not dismissed
  if (status !== 'offline' || dismissed) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-[60] flex items-center justify-center gap-2 px-4 py-2.5 bg-red-900/40 border-b border-red-500/30 backdrop-blur-sm animate-slide-down"
    >
      <AlertTriangle size={16} className="text-red-400 shrink-0" />
      <p className="text-sm text-red-300 text-center">
        Unable to connect to server. Please check your connection.
      </p>
      <button
        onClick={() => setDismissed(true)}
        className="ml-auto text-red-400 hover:text-red-200 transition-colors text-xs underline underline-offset-2 shrink-0"
      >
        Dismiss
      </button>
    </div>
  );
};
