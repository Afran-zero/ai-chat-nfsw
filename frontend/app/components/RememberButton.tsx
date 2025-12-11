'use client';

import { Bookmark } from 'lucide-react';

interface RememberButtonProps {
  onClick: () => void;
}

export default function RememberButton({ onClick }: RememberButtonProps) {
  return (
    <button
      onClick={onClick}
      className="p-1.5 bg-gold/20 hover:bg-gold/30 rounded-full text-gold transition-all hover:scale-110 active:scale-95"
      title="Tap to Remember"
    >
      <Bookmark className="w-4 h-4" />
    </button>
  );
}
