'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { 
  Heart, ArrowLeft, MoreVertical, X, Shield, ShieldCheck
} from 'lucide-react';
import Link from 'next/link';
import ChatBubble from '../../components/ChatBubble';
import MessageInput from '../../components/MessageInput';

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

interface User {
  id: string;
  nickname: string;
  is_online: boolean;
}

interface Room {
  id: number;
  name: string;
  status: string;
  nsfw_mode: string;
  users: User[];
}

interface ConsentStatus {
  room_id: number;
  nsfw_mode: string;
  partner_a_consent: boolean;
  partner_b_consent: boolean;
  both_consented: boolean;
  your_consent?: boolean;
}

export default function RoomPage() {
  const params = useParams();
  const router = useRouter();
  const roomId = params.id as string;
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [room, setRoom] = useState<Room | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isTyping, setIsTyping] = useState<string[]>([]);
  const [showReactions, setShowReactions] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [consentStatus, setConsentStatus] = useState<ConsentStatus | null>(null);
  const [myConsent, setMyConsent] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  const userId = typeof window !== 'undefined' ? localStorage.getItem('userId') : null;
  const nickname = typeof window !== 'undefined' ? localStorage.getItem('nickname') : null;

  // Redirect if not logged in
  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem('userId')) {
      router.push('/auth');
    }
  }, [router]);

  // Scroll to bottom on new messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load consent status
  const loadConsentStatus = async () => {
    try {
      const response = await fetch(`/api/rooms/${roomId}/consent`);
      const data = await response.json();
      setConsentStatus(data);
      // Determine my consent based on partner role
      const users = room?.users || [];
      const myIndex = users.findIndex(u => u.id === userId);
      if (myIndex === 0) {
        setMyConsent(data.partner_a_consent);
      } else {
        setMyConsent(data.partner_b_consent);
      }
    } catch (error) {
      console.error('Failed to load consent status:', error);
    }
  };

  // Toggle NSFW consent
  const toggleNSFWConsent = async () => {
    try {
      const newConsent = !myConsent;
      const response = await fetch(`/api/rooms/${roomId}/consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          consent: newConsent
        })
      });
      const data = await response.json();
      setConsentStatus(data);
      setMyConsent(newConsent);
    } catch (error) {
      console.error('Failed to toggle consent:', error);
    }
  };

  // Load room data
  useEffect(() => {
    const loadRoom = async () => {
      try {
        const response = await fetch(`/api/rooms/${roomId}`);
        const data = await response.json();
        setRoom(data);
      } catch (error) {
        console.error('Failed to load room:', error);
      }
    };

    const loadHistory = async () => {
      try {
        const response = await fetch(`/api/chat/history/${roomId}`);
        const data = await response.json();
        setMessages(data.messages);
      } catch (error) {
        console.error('Failed to load history:', error);
      }
    };

    loadRoom();
    loadHistory();
  }, [roomId]);

  // Load consent when room is loaded
  useEffect(() => {
    if (room && userId) {
      loadConsentStatus();
    }
  }, [room, userId]);

  // WebSocket connection
  useEffect(() => {
    if (!userId || !roomId) return;

    const deviceId = localStorage.getItem('deviceId') || 'default';
    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'}/api/chat/ws/${roomId}/${userId}?device_id=${deviceId}`;
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.event) {
        case 'new_message':
          setMessages(prev => [...prev, data.data]);
          break;
        case 'typing_status':
          setIsTyping(data.data.typing_users.filter((id: string) => id !== userId));
          break;
        case 'reaction_added':
        case 'reaction_removed':
          setMessages(prev => prev.map(msg => 
            msg.id === data.data.message_id 
              ? { ...msg, reactions: data.data.reactions }
              : msg
          ));
          break;
        case 'message_remembered':
          setMessages(prev => prev.map(msg =>
            msg.id === data.data.message_id
              ? { ...msg, is_remembered: true }
              : msg
          ));
          break;
        case 'user_joined':
        case 'user_left':
          // Reload room data
          fetch(`/api/rooms/${roomId}`)
            .then(res => res.json())
            .then(data => setRoom(data));
          break;
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [userId, roomId]);

  // Send message via WebSocket
  const sendMessage = useCallback((content: string, mentionBot: boolean = false) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      event: 'message',
      data: {
        content,
        type: 'text',
        mention_bot: mentionBot || content.toLowerCase().startsWith('@bot'),
      },
    }));
  }, []);

  // Send typing indicator
  const sendTyping = useCallback((isTyping: boolean) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      event: 'typing',
      data: { is_typing: isTyping },
    }));
  }, []);

  // Add reaction
  const addReaction = useCallback((messageId: string, reactionType: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;

    wsRef.current.send(JSON.stringify({
      event: 'reaction',
      data: {
        message_id: messageId,
        reaction_type: reactionType,
        action: 'add',
      },
    }));
    setShowReactions(null);
  }, []);

  // Remember message
  const rememberMessage = async (messageId: string, category: string = 'general') => {
    try {
      await fetch(`/api/memory/remember?user_id=${userId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message_id: messageId,
          category,
        }),
      });
    } catch (error) {
      console.error('Failed to remember:', error);
    }
  };

  const partner = room?.users.find(u => u.id !== userId);

  return (
    <div className="flex flex-col h-[100dvh] bg-[#0a0000] overflow-hidden">
      {/* Gradient Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-[#1a0508] via-[#0d0000] to-[#0a0000]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(139,10,26,0.1)_0%,_transparent_50%)]" />
      </div>

      {/* Header */}
      <header className="relative z-20 flex items-center justify-between px-4 py-3 bg-[#0d0000]/80 backdrop-blur-lg border-b border-white/5">
        <div className="flex items-center space-x-3">
          <Link href="/" className="p-2 -ml-2 text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#8B0A1A] to-[#5a0610] flex items-center justify-center">
              <Heart className="w-5 h-5 text-white fill-white" />
            </div>
            <div>
              <h1 className="font-semibold text-white text-sm">
                {room?.name || `Room ${roomId}`}
              </h1>
              <p className="text-xs text-gray-500">
                {partner ? (
                  <span className="flex items-center space-x-1.5">
                    <span>{partner.nickname}</span>
                    <span className={`w-1.5 h-1.5 rounded-full ${partner.is_online ? 'bg-green-500' : 'bg-gray-500'}`} />
                  </span>
                ) : (
                  'Waiting for partner...'
                )}
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          {consentStatus?.both_consented && (
            <span className="text-[10px] px-2 py-1 rounded-full font-medium bg-pink-500/10 text-pink-400">
              🔥 NSFW
            </span>
          )}
          <span className={`text-[10px] px-2 py-1 rounded-full font-medium ${isConnected ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {isConnected ? 'Live' : 'Offline'}
          </span>
          <button 
            onClick={() => setShowSettings(true)}
            className="p-2 text-gray-400 hover:text-white transition-colors"
          >
            <MoreVertical className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Messages Container */}
      <div className="relative z-10 flex-1 overflow-y-auto">
        <div className="px-4 py-4 space-y-3 min-h-full">
          {/* Empty State */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <div className="w-20 h-20 rounded-full bg-[#8B0A1A]/10 flex items-center justify-center mb-4">
                <Heart className="w-10 h-10 text-[#8B0A1A]" />
              </div>
              <h3 className="text-lg font-semibold text-white mb-2">Start Your Conversation</h3>
              <p className="text-gray-500 text-sm max-w-xs">
                Send your first message or mention <span className="text-[#D4A574]">@bot</span> to chat with AI
              </p>
            </div>
          )}

          {/* Messages */}
          {messages.map((message) => (
            <ChatBubble
              key={message.id}
              message={message}
              isOwn={message.sender_id === userId}
              onLongPress={() => setShowReactions(message.id)}
              onRemember={() => rememberMessage(message.id)}
              showReactionBar={showReactions === message.id}
              onReaction={(type) => addReaction(message.id, type)}
              onCloseReactions={() => setShowReactions(null)}
            />
          ))}
          
          {/* Typing indicator */}
          {isTyping.length > 0 && (
            <div className="flex items-center space-x-3 px-4 py-2">
              <div className="flex space-x-1">
                <span className="w-2 h-2 bg-[#8B0A1A] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-[#8B0A1A] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-[#8B0A1A] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
              <span className="text-gray-500 text-sm">{partner?.nickname || 'Partner'} is typing...</span>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="relative z-20">
        <MessageInput
          onSend={sendMessage}
          onTyping={sendTyping}
          roomId={parseInt(roomId)}
          userId={userId || ''}
        />
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div 
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setShowSettings(false)}
          />
          <div className="relative w-full sm:max-w-md bg-[#1a0508] rounded-t-3xl sm:rounded-2xl border border-white/10 overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
              <h2 className="text-lg font-semibold text-white">Room Settings</h2>
              <button 
                onClick={() => setShowSettings(false)}
                className="p-2 -mr-2 text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* NSFW Consent Section */}
              <div className="space-y-4">
                <div className="flex items-center space-x-3">
                  {consentStatus?.both_consented ? (
                    <ShieldCheck className="w-6 h-6 text-pink-400" />
                  ) : (
                    <Shield className="w-6 h-6 text-gray-400" />
                  )}
                  <div>
                    <h3 className="font-medium text-white">NSFW Mode</h3>
                    <p className="text-xs text-gray-500">
                      Both partners must consent to enable
                    </p>
                  </div>
                </div>

                {/* Consent Status */}
                <div className="bg-white/5 rounded-xl p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Your consent</span>
                    <button
                      onClick={toggleNSFWConsent}
                      className={`relative w-12 h-6 rounded-full transition-colors ${
                        myConsent ? 'bg-pink-500' : 'bg-gray-600'
                      }`}
                    >
                      <span 
                        className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                          myConsent ? 'left-7' : 'left-1'
                        }`}
                      />
                    </button>
                  </div>
                  
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Partner&apos;s consent</span>
                    <span className={`text-sm ${
                      (consentStatus?.partner_a_consent && consentStatus?.partner_b_consent) 
                        ? 'text-pink-400' 
                        : myConsent 
                          ? (consentStatus?.partner_a_consent || consentStatus?.partner_b_consent ? 'text-pink-400' : 'text-gray-500')
                          : 'text-gray-500'
                    }`}>
                      {consentStatus?.both_consented 
                        ? '✓ Consented' 
                        : myConsent 
                          ? 'Waiting...'
                          : 'Not requested'}
                    </span>
                  </div>

                  {consentStatus?.both_consented && (
                    <div className="pt-2 border-t border-white/10">
                      <p className="text-xs text-pink-400 text-center">
                        🔥 NSFW mode is active! The AI can now be more flirty.
                      </p>
                    </div>
                  )}
                </div>

                <p className="text-xs text-gray-500 text-center">
                  This unlocks romantic AI responses. Both partners can revoke consent anytime.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
