'use client';

import { useState } from 'react';
import { Heart, Bookmark, Eye, EyeOff, Bot, Image as ImageIcon, Volume2 } from 'lucide-react';
import ReactionBar from './ReactionBar';
import RememberButton from './RememberButton';

interface Message {
  id: string;
  room_id: number;
  sender_id: string;
  content: string;
  message_type: 'text' | 'image' | 'audio' | 'system' | 'bot';
  media_url?: string;
  view_once: boolean;
  view_once_available: boolean;
  reply_to_id?: string;
  reactions: Record<string, string[]>;
  is_remembered: boolean;
  created_at: string;
}

interface ChatBubbleProps {
  message: Message;
  isOwn: boolean;
  onLongPress: () => void;
  onRemember: () => void;
  showReactionBar: boolean;
  onReaction: (type: string) => void;
  onCloseReactions: () => void;
}

const REACTION_EMOJIS: Record<string, string> = {
  heart: '❤️',
  laugh: '😂',
  cry: '😢',
  shocked: '😮',
  angry: '😠',
};

export default function ChatBubble({
  message,
  isOwn,
  onLongPress,
  onRemember,
  showReactionBar,
  onReaction,
  onCloseReactions,
}: ChatBubbleProps) {
  const [viewOnceRevealed, setViewOnceRevealed] = useState(false);
  const [longPressTimer, setLongPressTimer] = useState<NodeJS.Timeout | null>(null);

  const handleTouchStart = () => {
    const timer = setTimeout(() => {
      onLongPress();
    }, 500);
    setLongPressTimer(timer);
  };

  const handleTouchEnd = () => {
    if (longPressTimer) {
      clearTimeout(longPressTimer);
      setLongPressTimer(null);
    }
  };

  const handleViewOnce = async () => {
    if (!message.view_once || !message.view_once_available || viewOnceRevealed) return;
    
    setViewOnceRevealed(true);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
      setViewOnceRevealed(false);
    }, 5000);

    // Mark as viewed on server
    try {
      await fetch(`/api/chat/view-once/${message.id}`, { method: 'POST' });
    } catch (error) {
      console.error('Failed to mark as viewed:', error);
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  // Get all reactions with counts
  const reactionCounts = Object.entries(message.reactions || {}).reduce((acc, [type, users]) => {
    if (users.length > 0) {
      acc.push({ type, count: users.length, emoji: REACTION_EMOJIS[type] });
    }
    return acc;
  }, [] as { type: string; count: number; emoji: string }[]);

  // System message style
  if (message.message_type === 'system') {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-gray-500 bg-background-secondary px-3 py-1 rounded-full">
          {message.content}
        </span>
      </div>
    );
  }

  // Bot message style
  const isBot = message.message_type === 'bot';

  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} relative`}>
      <div
        className={`relative max-w-[75%] group ${isOwn ? 'order-2' : 'order-1'}`}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleTouchStart}
        onMouseUp={handleTouchEnd}
        onMouseLeave={handleTouchEnd}
        onContextMenu={(e) => {
          e.preventDefault();
          onLongPress();
        }}
      >
        {/* Reaction Bar */}
        {showReactionBar && (
          <ReactionBar
            onReaction={onReaction}
            onClose={onCloseReactions}
          />
        )}

        {/* Message Bubble */}
        <div
          className={`
            rounded-2xl px-4 py-2 
            ${isBot 
              ? 'bg-gradient-to-br from-purple-600/30 to-romantic/30 border border-purple-500/30' 
              : isOwn 
                ? 'bg-romantic rounded-br-md' 
                : 'bg-background-card rounded-bl-md'
            }
            ${message.is_remembered ? 'ring-2 ring-gold/50' : ''}
          `}
        >
          {/* Bot indicator */}
          {isBot && (
            <div className="flex items-center space-x-1 text-xs text-purple-400 mb-1">
              <Bot className="w-3 h-3" />
              <span>AI Assistant</span>
            </div>
          )}

          {/* Content based on type */}
          {message.message_type === 'text' || message.message_type === 'bot' ? (
            <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          ) : message.message_type === 'image' ? (
            <div 
              className="relative cursor-pointer"
              onClick={message.view_once ? handleViewOnce : undefined}
            >
              {message.view_once && !viewOnceRevealed ? (
                <div className="w-48 h-48 bg-black/50 rounded-lg flex flex-col items-center justify-center space-y-2">
                  {message.view_once_available ? (
                    <>
                      <EyeOff className="w-8 h-8 text-romantic" />
                      <span className="text-xs text-gray-400">Tap to view once</span>
                    </>
                  ) : (
                    <>
                      <Eye className="w-8 h-8 text-gray-500" />
                      <span className="text-xs text-gray-500">Already viewed</span>
                    </>
                  )}
                </div>
              ) : (
                <img
                  src={message.media_url}
                  alt="Shared image"
                  className={`max-w-48 max-h-64 rounded-lg object-cover ${message.view_once ? 'animate-pulse' : ''}`}
                />
              )}
            </div>
          ) : message.message_type === 'audio' ? (
            <div className="flex items-center space-x-2 min-w-32">
              <button className="p-2 bg-romantic/20 rounded-full hover:bg-romantic/30 transition-colors">
                <Volume2 className="w-4 h-4 text-romantic" />
              </button>
              <div className="flex-1 h-1 bg-gray-600 rounded-full">
                <div className="w-0 h-full bg-romantic rounded-full" />
              </div>
              <span className="text-xs text-gray-400">0:00</span>
            </div>
          ) : null}

          {/* Timestamp and status */}
          <div className={`flex items-center space-x-1 mt-1 ${isOwn ? 'justify-end' : 'justify-start'}`}>
            <span className="text-[10px] text-gray-400">
              {formatTime(message.created_at)}
            </span>
            {message.is_remembered && (
              <Bookmark className="w-3 h-3 text-gold fill-gold" />
            )}
          </div>
        </div>

        {/* Reactions */}
        {reactionCounts.length > 0 && (
          <div className={`flex space-x-1 mt-1 ${isOwn ? 'justify-end' : 'justify-start'}`}>
            {reactionCounts.map(({ type, count, emoji }) => (
              <button
                key={type}
                onClick={() => onReaction(type)}
                className="flex items-center space-x-0.5 bg-background-secondary px-1.5 py-0.5 rounded-full text-xs hover:bg-background-card transition-colors"
              >
                <span>{emoji}</span>
                {count > 1 && <span className="text-gray-400">{count}</span>}
              </button>
            ))}
          </div>
        )}

        {/* Remember Button (shown on hover for non-remembered messages) */}
        {!message.is_remembered && !isBot && (
          <div className={`absolute top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity ${isOwn ? '-left-10' : '-right-10'}`}>
            <RememberButton onClick={onRemember} />
          </div>
        )}
      </div>
    </div>
  );
}
