import localforage from 'localforage';
import type { Conversation, ConversationSummary } from '../types';

const STORE_KEYS = {
  INDEX: 'conversation:index',
};

export const storage = {
  async getConversations(): Promise<ConversationSummary[]> {
    return (await localforage.getItem<ConversationSummary[]>(STORE_KEYS.INDEX)) || [];
  },

  async getConversation(id: string): Promise<Conversation | null> {
    return await localforage.getItem<Conversation>(`conversation:${id}`);
  },

  async saveConversation(conversation: Conversation): Promise<void> {
    conversation.updatedAt = Date.now();
    await localforage.setItem(`conversation:${conversation.id}`, conversation);
    
    const index = await this.getConversations();
    const existingIdx = index.findIndex(c => c.id === conversation.id);
    
    const summary: ConversationSummary = {
      id: conversation.id,
      title: conversation.title,
      updatedAt: conversation.updatedAt,
    };

    if (existingIdx > -1) {
      index[existingIdx] = summary;
    } else {
      index.push(summary);
    }
    
    // Sort by updatedAt descending
    index.sort((a, b) => b.updatedAt - a.updatedAt);
    await localforage.setItem(STORE_KEYS.INDEX, index);
  },

  async deleteConversation(id: string): Promise<void> {
    await localforage.removeItem(`conversation:${id}`);
    const index = await this.getConversations();
    const newIndex = index.filter(c => c.id !== id);
    await localforage.setItem(STORE_KEYS.INDEX, newIndex);
  },

  async createConversation(firstMessage: string): Promise<Conversation> {
    const id = crypto.randomUUID();
    const conversation: Conversation = {
      id,
      title: firstMessage.slice(0, 40) + (firstMessage.length > 40 ? '...' : ''),
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [{ role: 'user', content: firstMessage }],
    };
    await this.saveConversation(conversation);
    return conversation;
  }
};
