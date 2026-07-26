import React, { useState, useEffect } from 'react';
import { 
  Plus, 
  MessageSquare, 
  Trash2, 
  Edit2, 
  Menu, 
  X, 
  PanelLeftClose, 
  PanelLeftOpen 
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useChatStore } from '@/store/chatStore';
import { storage } from '@/services/storage';
import { cn } from '@/lib/utils';

export const Sidebar = () => {
  const { 
    conversations, 
    activeConversationId, 
    setActiveConversation, 
    setConversations, 
    refreshConversations 
  } = useChatStore();
  
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState("");

  const handleNewChat = async () => {
    // This will be handled by the main chat area to trigger first message,
    // but we can just clear the active session here.
    setActiveConversation(null);
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await storage.deleteConversation(id);
    await refreshConversations();
    if (activeConversationId === id) {
      setActiveConversation(null);
    }
  };

  const handleRename = async (id: string) => {
    const conv = await storage.getConversation(id);
    if (conv) {
      conv.title = editValue;
      conv.updatedAt = Date.now();
      await storage.saveConversation(conv);
      await refreshConversations();
    }
    setEditingId(null);
  };

  return (
    <div className={cn(
      "fixed left-0 top-0 h-screen bg-black border-r border-white transition-all duration-200 z-40",
      isCollapsed ? "w-0 overflow-hidden border-r-0" : "w-64",
      "md:relative md:translate-x-0",
      isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
    )}>
      <div className="flex flex-col h-full p-4">
        <Button 
          variant="primary" 
          className="w-full justify-start gap-2 mb-6" 
          onClick={handleNewChat}
        >
          <Plus size={16} />
          <span>New Chat</span>
        </Button>

        <div className="flex-1 overflow-y-auto space-y-2">
          <p className="text-xs text-gray-500 uppercase tracking-wider mb-4 font-medium">
            Conversations
          </p>
          
          {conversations.length === 0 && (
            <p className="text-sm text-gray-600 italic">No conversations yet</p>
          )}

          {conversations.map((conv) => (
            <div 
              key={conv.id}
              onClick={() => setActiveConversation(conv.id)}
              className={cn(
                "group relative flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors",
                activeConversationId === conv.id ? "bg-gray-900" : "hover:bg-gray-900"
              )}
            >
              <MessageSquare size={16} className="text-gray-400" />
              
              {editingId === conv.id ? (
                <input 
                  autoFocus
                  className="bg-transparent text-white text-sm outline-none w-full"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRename(conv.id)}
                  onBlur={() => setEditingId(null)}
                />
              ) : (
                <span className="text-sm truncate flex-1">{conv.title}</span>
              )}

              <div className="hidden group-hover:flex items-center gap-1">
                <button 
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingId(conv.id);
                    setEditValue(conv.title);
                  }}
                  className="p-1 hover:text-white text-gray-500 transition-colors"
                >
                  <Edit2 size={14} />
                </button>
                <button 
                  onClick={(e) => handleDelete(e, conv.id)}
                  className="p-1 hover:text-white text-gray-500 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
