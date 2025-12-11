'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  Heart, ArrowLeft, Lock, Users, Plus, 
  LogIn, Sparkles, Eye, EyeOff
} from 'lucide-react';

type AuthMode = 'join' | 'create';

export default function AuthPage() {
  const router = useRouter();
  
  const [mode, setMode] = useState<AuthMode>('join');
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showSecret, setShowSecret] = useState(false);
  
  // Form fields - join uses roomName now
  const [joinRoomName, setJoinRoomName] = useState('');
  const [roomSecret, setRoomSecret] = useState('');
  const [nickname, setNickname] = useState('');
  const [roomName, setRoomName] = useState('');
  const [newSecret, setNewSecret] = useState('');

  useEffect(() => {
    setIsLoaded(true);
  }, []);

  const handleJoinRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (!joinRoomName.trim()) {
        throw new Error('Please enter the room name');
      }

      if (!roomSecret.trim()) {
        throw new Error('Please enter the room secret');
      }

      if (!nickname.trim()) {
        throw new Error('Please enter your nickname');
      }

      let deviceId = localStorage.getItem('deviceId');
      if (!deviceId) {
        deviceId = crypto.randomUUID();
        localStorage.setItem('deviceId', deviceId);
      }

      const response = await fetch('/api/rooms/join', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_name: joinRoomName.trim(),
          room_secret: roomSecret.trim(),
          nickname: nickname.trim(),
          device_id: deviceId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to join room');
      }

      localStorage.setItem('userId', data.user.id);
      localStorage.setItem('nickname', nickname.trim());
      localStorage.setItem('roomId', data.room.id.toString());

      router.push(`/room/${data.room.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateRoom = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      let deviceId = localStorage.getItem('deviceId');
      if (!deviceId) {
        deviceId = crypto.randomUUID();
        localStorage.setItem('deviceId', deviceId);
      }

      const response = await fetch('/api/rooms/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: roomName,
          room_secret: newSecret,
          creator_nickname: nickname,
          device_id: deviceId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create room');
      }

      localStorage.setItem('userId', data.user.id);
      localStorage.setItem('nickname', nickname);

      router.push(`/room/${data.room.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a0000] overflow-hidden relative">
      {/* Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-br from-[#1a0508] via-[#0d0000] to-[#0a0000]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(139,10,26,0.15)_0%,_transparent_70%)]" />
      </div>

      {/* Content */}
      <div className="relative z-10 min-h-screen flex flex-col">
        {/* Header */}
        <header className={`flex items-center justify-between px-6 py-6 transition-all duration-500 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'}`}>
          <Link href="/" className="flex items-center space-x-2 text-gray-400 hover:text-white transition-colors">
            <ArrowLeft className="w-5 h-5" />
            <span>Back</span>
          </Link>
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#8B0A1A] to-[#5a0610] flex items-center justify-center">
              <Heart className="w-4 h-4 text-white fill-white" />
            </div>
            <span className="font-semibold text-white">Nushur</span>
          </div>
        </header>

        {/* Main Content */}
        <main className="flex-1 flex items-center justify-center px-6 py-12">
          <div className={`w-full max-w-md transition-all duration-700 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}>
            {/* Mode Toggle */}
            <div className="flex bg-[#1a0508] rounded-2xl p-1 mb-8">
              <button
                onClick={() => setMode('join')}
                className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl font-medium transition-all duration-300 ${
                  mode === 'join' 
                    ? 'bg-gradient-to-r from-[#8B0A1A] to-[#a01020] text-white shadow-lg' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <LogIn className="w-4 h-4" />
                <span>Join Room</span>
              </button>
              <button
                onClick={() => setMode('create')}
                className={`flex-1 flex items-center justify-center space-x-2 py-3 rounded-xl font-medium transition-all duration-300 ${
                  mode === 'create' 
                    ? 'bg-gradient-to-r from-[#8B0A1A] to-[#a01020] text-white shadow-lg' 
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                <Plus className="w-4 h-4" />
                <span>Create Room</span>
              </button>
            </div>

            {/* Form Card */}
            <div className="bg-gradient-to-br from-white/[0.05] to-transparent border border-white/[0.08] rounded-3xl p-8 backdrop-blur-sm">
              <div className="text-center mb-8">
                <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#8B0A1A]/20 to-transparent flex items-center justify-center mx-auto mb-4">
                  {mode === 'join' ? (
                    <Users className="w-8 h-8 text-[#8B0A1A]" />
                  ) : (
                    <Sparkles className="w-8 h-8 text-[#D4A574]" />
                  )}
                </div>
                <h1 className="text-2xl font-bold text-white mb-2">
                  {mode === 'join' ? 'Join Your Space' : 'Create New Room'}
                </h1>
                <p className="text-gray-500 text-sm">
                  {mode === 'join' 
                    ? 'Enter your room credentials to connect' 
                    : 'Set up a private room for you and your partner'
                  }
                </p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl mb-6 text-sm">
                  {error}
                </div>
              )}

              <form onSubmit={mode === 'join' ? handleJoinRoom : handleCreateRoom} className="space-y-5">
                {mode === 'join' ? (
                  <>
                    <div>
                      <label className="block text-sm text-gray-400 mb-2">Room Name</label>
                      <input
                        type="text"
                        value={joinRoomName}
                        onChange={(e) => setJoinRoomName(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-[#8B0A1A]/50 transition-colors"
                        placeholder="Enter room name"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-gray-400 mb-2">Room Secret</label>
                      <div className="relative">
                        <input
                          type={showSecret ? 'text' : 'password'}
                          value={roomSecret}
                          onChange={(e) => setRoomSecret(e.target.value)}
                          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 pr-12 text-white placeholder-gray-500 focus:outline-none focus:border-[#8B0A1A]/50 transition-colors"
                          placeholder="Enter room secret"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowSecret(!showSecret)}
                          className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                        >
                          {showSecret ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <label className="block text-sm text-gray-400 mb-2">Room Name</label>
                      <input
                        type="text"
                        value={roomName}
                        onChange={(e) => setRoomName(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-[#8B0A1A]/50 transition-colors"
                        placeholder="Our Private Space"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm text-gray-400 mb-2">Room Secret</label>
                      <div className="relative">
                        <input
                          type={showSecret ? 'text' : 'password'}
                          value={newSecret}
                          onChange={(e) => setNewSecret(e.target.value)}
                          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 pr-12 text-white placeholder-gray-500 focus:outline-none focus:border-[#8B0A1A]/50 transition-colors"
                          placeholder="Create a secret password"
                          required
                          minLength={5}
                        />
                        <button
                          type="button"
                          onClick={() => setShowSecret(!showSecret)}
                          className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 hover:text-white transition-colors"
                        >
                          {showSecret ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Share this with your partner to join</p>
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-sm text-gray-400 mb-2">Your Nickname</label>
                  <input
                    type="text"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-[#8B0A1A]/50 transition-colors"
                    placeholder="How should we call you?"
                    required
                    minLength={2}
                    maxLength={20}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-4 bg-gradient-to-r from-[#8B0A1A] to-[#a01020] text-white font-semibold rounded-xl transition-all duration-300 hover:shadow-lg hover:shadow-[#8B0A1A]/30 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center space-x-2">
                      <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Please wait...</span>
                    </span>
                  ) : (
                    <span className="flex items-center justify-center space-x-2">
                      {mode === 'join' ? <LogIn className="w-5 h-5" /> : <Plus className="w-5 h-5" />}
                      <span>{mode === 'join' ? 'Join Room' : 'Create Room'}</span>
                    </span>
                  )}
                </button>
              </form>

              {/* Security Note */}
              <div className="flex items-center justify-center space-x-2 mt-6 text-gray-600 text-xs">
                <Lock className="w-3 h-3" />
                <span>End-to-end encrypted with AES-256-GCM</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
