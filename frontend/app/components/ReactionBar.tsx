'use client';

interface ReactionBarProps {
  onReaction: (type: string) => void;
  onClose: () => void;
}

const REACTIONS = [
  { type: 'heart', emoji: '❤️', label: 'Love' },
  { type: 'laugh', emoji: '😂', label: 'Laugh' },
  { type: 'cry', emoji: '😢', label: 'Sad' },
  { type: 'shocked', emoji: '😮', label: 'Shocked' },
  { type: 'angry', emoji: '😠', label: 'Angry' },
];

export default function ReactionBar({ onReaction, onClose }: ReactionBarProps) {
  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 z-40" 
        onClick={onClose}
      />
      
      {/* Reaction Picker */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 animate-fade-in">
        <div className="flex items-center space-x-1 bg-background-card border border-romantic/20 rounded-full px-2 py-1 shadow-lg">
          {REACTIONS.map(({ type, emoji, label }) => (
            <button
              key={type}
              onClick={() => onReaction(type)}
              className="p-2 hover:bg-romantic/20 rounded-full transition-all hover:scale-125 active:scale-95"
              title={label}
            >
              <span className="text-xl">{emoji}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
