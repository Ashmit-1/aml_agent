import { create } from 'zustand';
import { Conversation, ConversationSummary } from '../types';
import { storage } from '../services/storage';

interface ChatState {
  conversations: ConversationSummary[];
  activeConversationId: string | null;
  isLoading: boolean;
  
  setConversations: (convs: ConversationSummary[]) => void;
  setActiveConversation: (id: string | null) => void;
  loadConversations: () => Promise<void>;
  refreshConversations: () => Promise<void>;
  isLoadingState: (loading: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  activeConversationId: null,
  isLoading: false,

  setConversations: (conversations) => set({ conversations }),
  setActiveConversation: (activeConversationId) => set({ activeConversationId }),
  isLoadingState: (isLoading) => set({ isLoading }),

  loadConversations: async () => {
    const convs = await storage.getConversations();
    set({ conversations: convs });
  },

  refreshConversations: async () => {
    const convs = await storage.getConversations();
    set({ conversations: convs });
  },
}));
