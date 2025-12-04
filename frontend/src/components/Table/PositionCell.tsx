import { TableCell } from './TableCell';

interface PositionCellProps {
  position: number | string;
  className?: string;
}

export const PositionCell = ({ position, className = '' }: PositionCellProps) => {
  return (
    <TableCell 
      mono 
      size="base" 
      color="zinc-500" 
      className={`f1-display-bold ${className}`}
    >
      {position}
    </TableCell>
  );
};

