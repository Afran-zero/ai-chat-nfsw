'use client';

import { useState, useRef, useEffect, KeyboardEvent, ChangeEvent } from 'react';
import { Send, Paperclip, Mic, Image as ImageIcon, X, Eye } from 'lucide-react';

interface MessageInputProps {
  onSend: (content: string, mentionBot?: boolean) => void;
  onTyping: (isTyping: boolean) => void;
  roomId: number;
  userId: string;
}

export default function MessageInput({ onSend, onTyping, roomId, userId }: MessageInputProps) {
  const [message, setMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [showMediaOptions, setShowMediaOptions] = useState(false);
  const [viewOnce, setViewOnce] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setMessage(value);

    // Handle typing indicator
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    if (value.length > 0) {
      onTyping(true);
      typingTimeoutRef.current = setTimeout(() => {
        onTyping(false);
      }, 2000);
    } else {
      onTyping(false);
    }
  };

  const handleSend = () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage) return;

    const mentionBot = trimmedMessage.toLowerCase().includes('@bot');
    onSend(trimmedMessage, mentionBot);
    setMessage('');
    onTyping(false);

    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setShowMediaOptions(false);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('room_id', roomId.toString());
      formData.append('user_id', userId);
      formData.append('view_once', viewOnce.toString());

      const response = await fetch('/api/chat/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      setViewOnce(false);
    } catch (error) {
      console.error('Failed to upload:', error);
      alert('Failed to upload file. Please try again.');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        await uploadAudio(audioBlob);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('Failed to start recording:', error);
      alert('Please allow microphone access to record voice messages.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadAudio = async (blob: Blob) => {
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('file', blob, 'voice-message.webm');
      formData.append('room_id', roomId.toString());
      formData.append('user_id', userId);
      formData.append('type', 'audio');

      const response = await fetch('/api/chat/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }
    } catch (error) {
      console.error('Failed to upload audio:', error);
      alert('Failed to send voice message. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="border-t border-romantic/20 bg-background-card p-3">
      {/* Media Options Popup */}
      {showMediaOptions && (
        <div className="absolute bottom-20 left-4 bg-background-secondary border border-romantic/20 rounded-lg p-2 space-y-1 shadow-lg animate-fade-in">
          <button
            onClick={() => {
              setViewOnce(false);
              fileInputRef.current?.click();
            }}
            className="flex items-center space-x-2 w-full px-3 py-2 hover:bg-romantic/20 rounded-lg transition-colors"
          >
            <ImageIcon className="w-4 h-4 text-romantic" />
            <span className="text-sm">Send Image</span>
          </button>
          <button
            onClick={() => {
              setViewOnce(true);
              fileInputRef.current?.click();
            }}
            className="flex items-center space-x-2 w-full px-3 py-2 hover:bg-romantic/20 rounded-lg transition-colors"
          >
            <Eye className="w-4 h-4 text-gold" />
            <span className="text-sm">View Once Image</span>
          </button>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileSelect}
      />

      <div className="flex items-end space-x-2">
        {/* Attachment Button */}
        <button
          onClick={() => setShowMediaOptions(!showMediaOptions)}
          disabled={isUploading}
          className="p-2.5 text-gray-400 hover:text-romantic hover:bg-romantic/10 rounded-full transition-colors disabled:opacity-50"
        >
          {showMediaOptions ? (
            <X className="w-5 h-5" />
          ) : (
            <Paperclip className="w-5 h-5" />
          )}
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (@bot to chat with AI)"
            className="w-full bg-background-secondary border border-romantic/20 rounded-2xl px-4 py-2.5 text-white placeholder-gray-500 resize-none focus:outline-none focus:border-romantic/50 transition-colors"
            rows={1}
            disabled={isUploading || isRecording}
          />
        </div>

        {/* Voice or Send Button */}
        {message.trim() ? (
          <button
            onClick={handleSend}
            disabled={isUploading}
            className="p-2.5 bg-romantic hover:bg-romantic-dark text-white rounded-full transition-colors disabled:opacity-50"
          >
            <Send className="w-5 h-5" />
          </button>
        ) : (
          <button
            onMouseDown={startRecording}
            onMouseUp={stopRecording}
            onTouchStart={startRecording}
            onTouchEnd={stopRecording}
            disabled={isUploading}
            className={`p-2.5 rounded-full transition-colors ${
              isRecording 
                ? 'bg-red-500 hover:bg-red-600 animate-pulse' 
                : 'text-gray-400 hover:text-romantic hover:bg-romantic/10'
            }`}
          >
            <Mic className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Recording Indicator */}
      {isRecording && (
        <div className="flex items-center justify-center space-x-2 mt-2 text-red-400 text-sm">
          <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          <span>Recording... Release to send</span>
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && (
        <div className="flex items-center justify-center space-x-2 mt-2 text-romantic text-sm">
          <div className="w-4 h-4 border-2 border-romantic border-t-transparent rounded-full animate-spin" />
          <span>Uploading...</span>
        </div>
      )}
    </div>
  );
}
