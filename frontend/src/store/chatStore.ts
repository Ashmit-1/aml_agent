import { create } from 'zustand';
import type { ConversationSummary } from '../types';
import { storage } from '../services/storage';

interface ChatState {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  isLoading: boolean;
  sidebarOpen: boolean;
  
  setConversations: (convs: ConversationSummary[]) => void;
  setActiveConversation: (id: string | null) => void;
  setSidebarOpen: (open: boolean) => void;
  loadConversations: () => Promise<void>;
  refreshConversations: () => Promise<void>;
  setLoading: (loading: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeConversationId: null,
  isLoading: false,
  sidebarOpen: false,

  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (activeConversationId) => set({ activeConversationId }),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  setLoading: (isLoading) => set({ isLoading }),

  loadConversations: async () => {
    set({ isLoading: true });
    const convs = await storage.getConversations();
    set({ conversations: convs, isLoading: false });
  },

  refreshConversations: async () => {
    const convs = await storage.getConversations();
    set({ conversations: convs });
  },
}));
