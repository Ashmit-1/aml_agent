import type { Conversation, ConversationSummary } from '../types';
export declare const storage: {
    getConversations(): Promise<ConversationSummary[]>;
    getConversation(id: string): Promise<Conversation | null>;
    saveConversation(conversation: Conversation): Promise<void>;
    deleteConversation(id: string): Promise<void>;
    createConversation(firstMessage: string): Promise<Conversation>;
};
