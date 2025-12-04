import { Sparkline } from '../Sparkline';
import { TableCell } from './TableCell';

interface SparklineCellProps {
  data: number[];
  color: string;
  width?: number;
  height?: number;
  strokeWidth?: number;
  align?: 'left' | 'center' | 'right';
  className?: string;
}

export const SparklineCell = ({
  data,
  color,
  width = 60,
  height = 24,
  strokeWidth = 2,
  align = 'right',
  className = '',
}: SparklineCellProps) => {
  return (
    <TableCell align={align} className={className}>
      <Sparkline
        data={data}
        color={color}
        width={width}
        height={height}
        strokeWidth={strokeWidth}
      />
    </TableCell>
  );
};

