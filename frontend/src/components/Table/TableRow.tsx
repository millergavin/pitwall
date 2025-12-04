import { ReactNode } from 'react';

export interface TableRowProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  selected?: boolean;
  faded?: boolean;
  hoverable?: boolean;
}

export const TableRow = ({ 
  children, 
  className = '',
  onClick,
  onMouseEnter,
  onMouseLeave,
  selected = false,
  faded = false,
  hoverable = true,
}: TableRowProps) => {
  const hoverClasses = hoverable ? 'hover:bg-overlay-50' : '';
  const selectedClasses = selected ? 'bg-overlay-100' : '';
  const fadedClasses = faded ? 'opacity-40' : '';
  const interactiveClasses = onClick ? 'cursor-pointer' : '';

  return (
    <tr 
      className={`border-t border-zinc-900 transition-all ${hoverClasses} ${selectedClasses} ${fadedClasses} ${interactiveClasses} ${className}`}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {children}
    </tr>
  );
};

