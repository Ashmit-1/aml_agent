import { useEffect, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatInterface } from './components/ChatInterface';
import { useChatStore } from '@/store/chatStore';
import { chatService } from '@/services/chatApi';

const App = () => {
  const { loadConversations } = useChatStore();
  const [backendStatus, setBackendStatus] = useState<'checking' | 'online' | 'offline'>('checking');

  useEffect(() => {
    loadConversations();
    
    // Health check on app load
    chatService.getHealth()
      .then((data) => {
        setBackendStatus(data.status === 'ok' ? 'online' : 'offline');
      })
      .catch(() => {
        setBackendStatus('offline');
      });
  }, [loadConversations]);

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 h-full relative overflow-hidden">
        {backendStatus === 'offline' && (
          <div className="absolute top-0 left-0 right-0 z-50 bg-black border-b border-red-500/30 px-4 py-2 text-center">
            <p className="text-xs text-red-400 flex items-center justify-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 inline-block" />
              Unable to connect to backend server. Please check your connection.
            </p>
          </div>
        )}
        {backendStatus === 'checking' && (
          <div className="absolute top-0 left-0 right-0 z-50 bg-black border-b border-gray-800 px-4 py-2 text-center">
            <p className="text-xs text-gray-500 flex items-center justify-center gap-2">
              <span className="h-1.5 w-1.5 rounded-full bg-gray-500 animate-pulse inline-block" />
              Connecting to backend...
            </p>
          </div>
        )}
        <ChatInterface />
      </main>
    </div>
  );
};

export default App;
