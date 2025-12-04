import { ReactNode } from 'react';

export interface TableCellProps {
  children?: ReactNode;
  align?: 'left' | 'center' | 'right';
  className?: string;
  mono?: boolean;
  bold?: boolean;
  size?: 'xs' | 'sm' | 'base' | 'lg';
  color?: 'white' | 'zinc-400' | 'zinc-500' | 'zinc-600';
}

export const TableCell = ({ 
  children, 
  align = 'left',
  className = '',
  mono = false,
  bold = false,
  size = 'sm',
  color = 'white',
}: TableCellProps) => {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  const sizeClasses = {
    xs: 'text-xs',
    sm: 'text-sm',
    base: 'text-base',
    lg: 'text-lg',
  };

  const colorClasses = {
    white: 'text-white',
    'zinc-400': 'text-zinc-400',
    'zinc-500': 'text-zinc-500',
    'zinc-600': 'text-zinc-600',
  };

  const monoClass = mono ? 'font-mono' : '';
  const boldClass = bold ? 'font-bold' : '';

  return (
    <td 
      className={`px-3 py-3 ${alignClasses[align]} ${sizeClasses[size]} ${colorClasses[color]} ${monoClass} ${boldClass} ${className}`}
    >
      {children}
    </td>
  );
};

