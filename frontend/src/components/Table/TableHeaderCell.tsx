import { ReactNode } from 'react';

export interface TableHeaderCellProps {
  children?: ReactNode;
  align?: 'left' | 'center' | 'right';
  width?: string;
  className?: string;
}

export const TableHeaderCell = ({ 
  children, 
  align = 'left', 
  width,
  className = '' 
}: TableHeaderCellProps) => {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  };

  const widthStyle = width ? { width } : {};

  return (
    <th 
      className={`px-3 py-3 ${alignClasses[align]} ${className}`}
      style={widthStyle}
    >
      {children}
    </th>
  );
};

