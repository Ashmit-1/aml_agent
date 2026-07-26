export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
}

export interface ConversationSummary {
  id: string;
  title: string;
  updatedAt: number;
}

export type SSEEvent = 
  | { type: 'thinking'; content: string }
  | { type: 'tool_call'; tool: string; arguments: any }
  | { type: 'tool_result'; tool: string; summary: string }
  | { type: 'retry'; retry_count: number; reason: string }
  | { type: 'response'; content: string }
  | { type: 'error'; message: string };
