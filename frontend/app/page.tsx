'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { 
  Shield, Heart, Brain, Lock, MessageCircle, 
  Sparkles, Users, Eye, ChevronRight, Star
} from 'lucide-react';

// Dynamically import DarkVeil with no SSR
const DarkVeil = dynamic(() => import('./components/DarkVeil'), {
  ssr: false,
  loading: () => <div className="absolute inset-0 bg-gradient-to-br from-[#1a0508] via-[#0d0000] to-[#0a0000]" />
});

const features = [
  {
    icon: Brain,
    title: 'AI Relationship Coach',
    description: 'Intelligent orchestrated workflows that adapt to your conversation context'
  },
  {
    icon: Heart,
    title: 'Intimate Playground',
    description: 'Consent-aware NSFW mode with automatic persona switching'
  },
  {
    icon: Lock,
    title: 'End-to-End Encryption',
    description: 'AES-256-GCM encryption for all your messages and media'
  },
  {
    icon: Eye,
    title: 'View Once Media',
    description: 'Self-destructing images that disappear after viewing'
  },
  {
    icon: Sparkles,
    title: 'Memory System',
    description: 'Tap to Remember important moments stored in vector memory'
  },
  {
    icon: Users,
    title: 'Private Two-Person Rooms',
    description: 'Exclusive spaces for you and your partner only'
  }
];

export default function LandingPage() {
  const [mousePosition, setMousePosition] = useState({ x: 50, y: 50 });
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    setIsLoaded(true);
    
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div className="min-h-screen bg-[#0a0000] overflow-hidden relative">
      {/* WebGL Animated Background */}
      <div className="fixed inset-0 z-0">
        {/* Base gradient */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#1a0508] via-[#0d0000] to-[#0a0000]" />
        
        {/* DarkVeil shader */}
        <DarkVeil 
          hueShift={-10}
          noiseIntensity={0.03}
          scanlineIntensity={0.05}
          speed={0.3}
          warpAmount={0.2}
          resolutionScale={0.8}
        />
        
        {/* Overlay gradient for depth */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#0a0000] via-transparent to-transparent opacity-60" />
      </div>

      {/* Content */}
      <div className="relative z-10">
        {/* Navigation */}
        <nav className={`flex items-center justify-between px-6 md:px-12 py-6 transition-all duration-700 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-4'}`}>
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#8B0A1A] to-[#5a0610] flex items-center justify-center shadow-lg shadow-[#8B0A1A]/30">
              <Heart className="w-6 h-6 text-white fill-white" />
            </div>
            <span className="text-2xl font-bold text-white tracking-tight">Nushur</span>
          </div>
          <Link 
            href="/auth"
            className="px-5 py-2.5 text-sm font-medium text-[#D4A574] hover:text-white border border-[#D4A574]/30 hover:border-[#D4A574] rounded-full transition-all duration-300 hover:bg-[#D4A574]/10"
          >
            Sign In
          </Link>
        </nav>

        {/* Hero Section */}
        <section className="px-6 md:px-12 pt-16 md:pt-28 pb-20">
          <div className="max-w-5xl mx-auto text-center">
            {/* Badge */}
            <div className={`inline-flex items-center space-x-2 px-4 py-2 rounded-full bg-[#8B0A1A]/10 border border-[#8B0A1A]/30 mb-8 transition-all duration-700 delay-100 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <Shield className="w-4 h-4 text-[#8B0A1A]" />
              <span className="text-sm text-gray-300">Private & Encrypted</span>
            </div>

            {/* Main Title */}
            <h1 className={`text-6xl md:text-8xl lg:text-9xl font-bold mb-6 transition-all duration-700 delay-200 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <span className="text-white tracking-tight">Nushur</span>
            </h1>

            {/* Subtitle */}
            <p className={`text-xl md:text-2xl text-gray-400 mb-4 transition-all duration-700 delay-300 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              Private Chat Platform with
            </p>
            <p className={`text-2xl md:text-4xl font-semibold mb-8 transition-all duration-700 delay-400 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#8B0A1A] via-[#c41e3a] to-[#D4A574]">
                Orchestrated AI Workflow
              </span>
            </p>

            {/* Description */}
            <p className={`text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-12 leading-relaxed transition-all duration-700 delay-500 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              Your intimate space for connection. <span className="text-gray-400">AI-powered relationship coaching</span> and 
              <span className="text-gray-400"> consent-aware NSFW playground</span>, wrapped in military-grade encryption.
            </p>

            {/* CTA Buttons */}
            <div className={`flex flex-col sm:flex-row items-center justify-center gap-4 transition-all duration-700 delay-600 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <Link
                href="/auth"
                className="group relative px-10 py-4 bg-gradient-to-r from-[#8B0A1A] to-[#a01020] text-white font-semibold rounded-full overflow-hidden transition-all duration-300 hover:shadow-xl hover:shadow-[#8B0A1A]/40 hover:scale-105 active:scale-95"
              >
                <span className="relative z-10 flex items-center space-x-2">
                  <span>Get Started</span>
                  <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </span>
                <div className="absolute inset-0 bg-gradient-to-r from-[#a01020] to-[#8B0A1A] opacity-0 group-hover:opacity-100 transition-opacity" />
              </Link>
              <Link
                href="/auth?demo=true"
                className="px-10 py-4 text-gray-300 hover:text-white font-medium rounded-full border border-gray-700 hover:border-[#8B0A1A]/50 transition-all duration-300 hover:bg-[#8B0A1A]/5"
              >
                Try Demo Room
              </Link>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="px-6 md:px-12 py-20 md:py-28">
          <div className="max-w-6xl mx-auto">
            <div className={`text-center mb-16 transition-all duration-700 delay-700 ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
              <h2 className="text-3xl md:text-5xl font-bold text-white mb-4">
                Everything You Need
              </h2>
              <p className="text-gray-500 text-lg max-w-xl mx-auto">
                Built for couples who value privacy, intimacy, and intelligent assistance
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {features.map((feature, index) => (
                <div
                  key={feature.title}
                  className={`group p-6 rounded-2xl bg-gradient-to-br from-white/[0.03] to-transparent border border-white/[0.05] hover:border-[#8B0A1A]/40 transition-all duration-500 hover:bg-[#8B0A1A]/5 cursor-pointer ${isLoaded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}
                  style={{ transitionDelay: `${800 + index * 100}ms` }}
                >
                  <div className="w-14 h-14 rounded-xl bg-[#8B0A1A]/10 flex items-center justify-center mb-5 group-hover:bg-[#8B0A1A]/20 group-hover:scale-110 transition-all duration-300">
                    <feature.icon className="w-7 h-7 text-[#8B0A1A]" />
                  </div>
                  <h3 className="text-xl font-semibold text-white mb-3 group-hover:text-[#D4A574] transition-colors">
                    {feature.title}
                  </h3>
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="px-6 md:px-12 py-20 md:py-28">
          <div className={`max-w-4xl mx-auto text-center transition-all duration-700 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}>
            <div className="p-10 md:p-14 rounded-3xl bg-gradient-to-br from-[#8B0A1A]/20 via-[#8B0A1A]/10 to-transparent border border-[#8B0A1A]/20 relative overflow-hidden">
              {/* Glow effect */}
              <div className="absolute inset-0 bg-gradient-to-t from-[#8B0A1A]/10 to-transparent" />
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-px bg-gradient-to-r from-transparent via-[#8B0A1A]/50 to-transparent" />
              
              <div className="relative z-10">
                <div className="flex items-center justify-center space-x-1 mb-6">
                  {[...Array(5)].map((_, i) => (
                    <Star key={i} className="w-5 h-5 text-[#D4A574] fill-[#D4A574]" />
                  ))}
                </div>
                <h3 className="text-3xl md:text-4xl font-bold text-white mb-4">
                  Start Your Private Journey
                </h3>
                <p className="text-gray-400 mb-8 max-w-lg mx-auto text-lg">
                  Create your encrypted room and invite your partner. 
                  Your conversations stay between you two—always.
                </p>
                <Link
                  href="/auth"
                  className="inline-flex items-center space-x-2 px-10 py-4 bg-white text-[#8B0A1A] font-semibold rounded-full hover:bg-gray-100 transition-all duration-300 hover:scale-105 active:scale-95 shadow-lg shadow-white/10"
                >
                  <MessageCircle className="w-5 h-5" />
                  <span>Create Your Room</span>
                </Link>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="px-6 md:px-12 py-8 border-t border-white/5">
          <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-2">
              <Heart className="w-4 h-4 text-[#8B0A1A] fill-[#8B0A1A]" />
              <span className="text-sm text-gray-500">Nushur © 2025</span>
            </div>
            <div className="flex items-center space-x-6 text-sm text-gray-500">
              <span>Private</span>
              <span className="text-[#8B0A1A]">•</span>
              <span>Encrypted</span>
              <span className="text-[#8B0A1A]">•</span>
              <span>Secure</span>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
