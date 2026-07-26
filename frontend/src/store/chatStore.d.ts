import type { ConversationSummary } from '../types';
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
export declare const useChatStore: import("zustand").UseBoundStore<import("zustand").StoreApi<ChatState>>;
export {};
