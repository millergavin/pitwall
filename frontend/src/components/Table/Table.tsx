import type { ReactNode } from 'react';

export interface TableProps {
  children: ReactNode;
  className?: string;
  variant?: 'default' | 'compact' | 'spacious';
}

export const Table = ({ children, className = '', variant = 'default' }: TableProps) => {
  const variantClasses = {
    default: '',
    compact: 'text-sm',
    spacious: 'text-base',
  };

  return (
    <div className="overflow-x-auto">
      <table className={`w-full table-fixed border-collapse ${variantClasses[variant]} ${className}`}>
        {children}
      </table>
    </div>
  );
};

