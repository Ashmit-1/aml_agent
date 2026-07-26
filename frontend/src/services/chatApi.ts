import type { ChatMessage } from '../types';

export const chatService = {
  async getHealth() {
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/health`);
    return res.json();
  },

  async *streamChat(message: string, history: ChatMessage[]) {
    // Inject markdown formatting instruction for the LLM (not shown in UI)
    const markdownInstruction: ChatMessage = {
      role: 'user',
      content: 'You MUST format your response using Markdown syntax. Use **bold**, *italic*, `inline code`, code blocks with language tags (```), headings (##, ###), bullet lists, numbered lists, tables, and blockquotes to make answers clear and well-structured. Always put code in proper code blocks with language specification.',
    };
    const augmentedHistory = [markdownInstruction, ...history];

    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history: augmentedHistory }),
    });

    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

    const reader = response.body?.getReader();
    if (!reader) throw new Error("No reader available");

    const decoder = new TextDecoder();
    let buffer = "";
    // Move these OUTSIDE the while loop so they persist across chunk boundaries
    let currentEvent: string | null = null;
    let currentData = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep the last (potentially incomplete) line in the buffer for the next chunk
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          currentData = line.slice(6).trim();
        } else if (line === "") {
          // Empty line = end of an SSE event
          if (currentEvent && currentData) {
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
              console.error("SSE parse error:", e);
            }
            // Reset both after a completed event
            currentEvent = null;
            currentData = "";
          }
          // If currentEvent/currentData are empty, this is a blank line — skip
        }
      }
    }
  }
};
