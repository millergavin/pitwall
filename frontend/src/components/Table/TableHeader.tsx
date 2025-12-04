import type { ReactNode } from 'react';

export interface TableHeaderProps {
  children: ReactNode;
  className?: string;
  sticky?: boolean;
  onClick?: () => void;
  title?: string;
}

export const TableHeader = ({ 
  children, 
  className = '', 
  sticky = false,
  onClick,
  title
}: TableHeaderProps) => {
  const stickyClasses = sticky ? 'sticky top-0 z-10' : '';
  const interactiveClasses = onClick 
    ? 'cursor-pointer hover:bg-zinc-900 transition-colors' 
    : '';

  return (
    <thead 
      className={`bg-zinc-950 text-zinc-400 text-xs uppercase tracking-wide ${stickyClasses} ${interactiveClasses} ${className}`}
      onClick={onClick}
      title={title}
    >
      {children}
    </thead>
  );
};

