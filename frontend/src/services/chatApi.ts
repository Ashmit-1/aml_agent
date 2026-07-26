import type { ChatMessage } from '../types';

export const chatService = {
  async getHealth() {
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/health`);
    return res.json();
  },

  async *streamChat(message: string, history: ChatMessage[]) {
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No reader available");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      let currentEvent = null;
      let currentData = "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          currentData = line.slice(6).trim();
        } else if (line === "" && currentEvent && currentData) {
          try {
            const parsed = JSON.parse(currentData);
            if (currentEvent === "step") {
              yield { type: 'step', data: parsed };
            } else if (currentEvent === "done") {
              yield { type: 'done' };
            } else if (currentEvent === "error") {
              yield { type: 'error', data: parsed };
            }
          } catch (e) {
            console.error("Parsing error", e);
          }
          currentEvent = null;
          currentData = "";
        }
      }
    }
  }
};
