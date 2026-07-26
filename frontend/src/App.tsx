import React, { useEffect } from 'react';
import { Sidebar } from './Sidebar';
import { ChatInterface } from './ChatInterface';
import { useChatStore } from '@/store/chatStore';

const App = () => {
  const { loadConversations } = useChatStore();

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  return (
    <div className="flex h-screen bg-black text-white overflow-hidden">
      <Sidebar />
      <main className="flex-1 h-full relative overflow-hidden">
        <ChatInterface />
      </main>
    </div>
  );
};

export default App;
