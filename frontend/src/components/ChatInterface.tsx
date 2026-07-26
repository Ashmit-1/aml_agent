import React, { useState, useEffect, useRef } from 'react';
import { 
  Brain, 
  Search, 
  TrendingUp, 
  ShieldAlert, 
  BarChart3, 
  Database, 
  Terminal, 
  CheckCircle2, 
  AlertTriangle, 
  MessageSquare, 
  Send, 
  User, 
  Bot, 
  Loader2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useChatStore } from '@/store/chatStore';
import { storage } from '@/services/storage';
import { chatService } from '@/services/chatApi';
import { ChatMessage } from '@/types';
import { cn } from '@/lib/utils';

const TOOL_ICONS: Record<string, React.ReactNode> = {
  search_transactions: <Search size={16} />,
  get_high_value_transactions: <TrendingUp size={16} />,
  get_suspicious_patterns: <ShieldAlert size={16} />,
  get_summary_statistics: <BarChart3 size={16} />,
  run_sql_query: <Database size={16} />,
  run_python_code: <Terminal size={16} />,
};

const ToolStep = ({ event }: { event: any }) => {
  const [isOpen, setIsOpen] = useState(true);
  
  const __icon = event.type === 'tool_call' 
    ? (TOOL_ICONS[event.tool] || <Search size={16} />) 
    : event.type === 'tool_result' 
      ? <CheckCircle2 size={16} /> 
      : event.type === 'thinking' 
        ? <Brain size={16} /> 
        : <AlertTriangle size={16} />;

  const __label = event.type === 'tool_call' 
    ? `Calling ${event.tool}` 
    : event.type === 'tool_result' 
      ? `Result from ${event.tool}` 
      : event.type === 'thinking' 
        ? `Thinking...` 
        : `Retrying (${event.retry_count}/3)...`;

  return (
    <Card className="my-2 overflow-hidden border-gray-800">
      <div 
        className="flex items-center justify-between p-2 cursor-pointer hover:bg-gray-900 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2 text-sm text-gray-300">
          {__icon}
          <span>{__label}</span>
        </div>
        {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </div>
      {isOpen && (
        <div className="p-2 pt-0 text-xs font-mono text-gray-400 border-t border-gray-800 mt-2 max-h-40 overflow-y-auto">
          <pre className="whitespace-pre-wrap">
            {event.type === 'tool_call' 
              ? JSON.stringify(event.arguments, null, 2) 
              : event.type === 'tool_result' 
                ? event.summary 
                : event.type === 'thinking' 
                  ? event.content 
                  : event.reason}
          </pre>
        </div>
      )}
    </Card>
  );
};

const ChatBubble = ({ role, content, steps }: { role: 'user' | 'assistant', content: string, steps?: any[] }) => {
  return (
    <div className={cn(
      "flex w-full gap-4 mb-6", 
      role === 'user' ? "justify-end" : "justify-start"
    )}>
      <div className={cn(
        "flex gap-4 max-w-3xl", 
        role === 'user' ? "flex-row-reverse" : "flex-row"
      )}>
        <div className={cn(
          "h-8 w-8 rounded-full flex items-center justify-center border border-white",
          role === 'user' ? "bg-white text-black" : "bg-black text-white"
        )}>
          {role === 'user' ? <User size={16} /> : <Bot size={16} />}
        </div>
        
        <div className="flex flex-col gap-3">
          {steps && steps.length > 0 && (
            <div className="flex flex-col gap-2">
              {steps.map((step, idx) => (
                <ToolStep key={idx} event={step} />
              ))}
            </div>
          )}
          
          <div className={cn(
            "p-3 rounded-md text-sm",
            role === 'user' 
              ? "bg-white text-black rounded-tr-none" 
              : "bg-black border border-white text-white rounded-tl-none"
          )}>
            <ReactMarkdown remarkGfm className="prose prose-invert max-w-none text-inherit">
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

export const ChatInterface = () => {
  const { 
    activeConversationId, 
    setActiveConversation, 
    refreshConversations 
  } = useChatStore();
  
  const [messages, setMessages] = useState<any[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (activeConversationId) {
      storage.getConversation(activeConversationId).then(conv => {
        if (conv) setMessages(conv.messages);
      });
    } else {
      setMessages([]);
    }
  }, [activeConversationId]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMsg = input.trim();
    setInput("");
    setIsTyping(true);

    let currentConvId = activeConversationId;
    let conversation: any = null;

    try {
      if (!currentConvId) {
        conversation = await storage.createConversation(userMsg);
        currentConvId = conversation.id;
        setActiveConversation(currentConvId);
      } else {
        conversation = await storage.getConversation(currentConvId);
        if (!conversation) throw new Error("Conversation not found");
        
        // Update existing conversation with new user message
        conversation.messages.push({ role: 'user' as const, content: userMsg });
        await storage.saveConversation(conversation);
      }

      setMessages(conversation.messages);

      const history = conversation.messages
        .slice(0, -1) // All except the very last user message (backend wants it in 'message' field)
        .map((m: any) => ({ role: m.role, content: m.content }));

      const stream = chatService.streamChat(userMsg, history);
      
      // Add a placeholder for the assistant's streaming response
      const assistantMsgIndex = conversation.messages.length;
      setMessages(prev => [...prev, { 
        role: 'assistant' as const, 
        content: '', 
        steps: [] 
      }]);

      let finalAssistantContent = '';
      let finalSteps: any[] = [];

      for await (const event of stream) {
        if (event.type === 'step') {
          const stepData = event.data;
          
          if (stepData.type === 'response') {
            finalAssistantContent = stepData.content;
            setMessages(prev => {
              const updated = [...prev];
              if (updated[assistantMsgIndex]) updated[assistantMsgIndex].content = stepData.content;
              return updated;
            });
          } else {
            finalSteps.push(stepData);
            setMessages(prev => {
              const updated = [...prev];
              if (updated[assistantMsgIndex]) {
                updated[assistantMsgIndex].steps = [...(updated[assistantMsgIndex].steps || []), stepData];
              }
              return updated;
            });
          }
        } else if (event.type === 'error') {
          finalAssistantContent = `**Error:** ${event.data.message}`;
          setMessages(prev => {
            const updated = [...prev];
            if (updated[assistantMsgIndex]) updated[assistantMsgIndex].content = finalAssistantContent;
            return updated;
          });
          break;
        }
      }

      // PERSISTENCE: Save final state after stream completion
      conversation.messages.push({ 
        role: 'assistant' as const, 
        content: finalAssistantContent || 'No response received.' 
      });
      await storage.saveConversation(conversation);
      
    } catch (err: any) {
      const errorMsg = { role: 'assistant' as const, content: `Error: ${err.message}` };
      setMessages(prev => [...prev, errorMsg]);
      
      if (conversation && currentConvId) {
        conversation.messages.push(errorMsg);
        await storage.saveConversation(conversation);
      }
    } finally {
      setIsTyping(false);
      refreshConversations();
    }
  };

  return (
    <div className="flex flex-col h-screen bg-black text-white">
      <div className="flex-1 overflow-hidden flex flex-col max-w-4xl mx-auto w-full">
        <ScrollArea className="flex-1 p-4 overflow-y-auto">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-4">
              <div className="h-16 w-16 rounded-full border border-white flex items-center justify-center mb-4">
                <Bot size={32} />
              </div_
              <h1 className="text-2xl font-medium">Agent Intelligence</h1>
              <p className="text-gray-500 max-w-md">
                Ask me about the dataset. I can search transactions, 
                analyze patterns, and run Python code to find answers.
              </p>
            </div_
          )}
          {messages.map((msg, idx) => (
            <ChatBubble key={idx} role={msg.role} content={msg.content} steps={msg.steps} />
          ))}
          <div ref={scrollRef} />
        </ScrollArea>

        <div className="p-4 border-t border-white/10">
          <form 
            onSubmit={handleSend}
            className="relative max-w-3xl mx-auto flex gap-2"
          >
            <Input 
              placeholder="Message agent..." 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="bg-black text-white border-white"
            />
            <Button 
              type="submit" 
              disabled={isTyping} 
              className="shrink-0"
            >
              {isTyping ? <Loader2 className="animate-spin" size={18} /> : <Send size={18} />}
            </Button>
          </form>
        </div_
      </div_
    </div_
  );
};
