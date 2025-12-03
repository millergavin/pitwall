import type { ReactNode } from 'react';
import { useState } from 'react';

interface TooltipProps {
  children: ReactNode;
  content: string;
  position?: 'top' | 'bottom' | 'left' | 'right';
}

export const Tooltip = ({ children, content, position = 'top' }: TooltipProps) => {
  const [isVisible, setIsVisible] = useState(false);

  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  };

  return (
    <div
      className="relative inline-block"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div
          className={`absolute z-50 px-2 py-1 text-xs bg-zinc-900 text-white rounded-corner whitespace-nowrap pointer-events-none ${positionClasses[position]}`}
        >
          {content}
          {/* Arrow */}
          <div
            className={`absolute ${
              position === 'top'
                ? 'top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-zinc-900'
                : position === 'bottom'
                ? 'bottom-full left-1/2 -translate-x-1/2 border-4 border-transparent border-b-zinc-900'
                : position === 'left'
                ? 'left-full top-1/2 -translate-y-1/2 border-4 border-transparent border-l-zinc-900'
                : 'right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-zinc-900'
            }`}
          />
        </div>
      )}
    </div>
  );
};

