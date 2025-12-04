interface SparklineProps {
  data: number[];
  color: string;
  width?: number;
  height?: number;
  strokeWidth?: number;
  className?: string;
}

export const Sparkline = ({
  data,
  color,
  width = 60,
  height = 24,
  strokeWidth = 2,
  className = '',
}: SparklineProps) => {
  if (!data.length) return null;

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;

  const padding = 2;

  const normalizedPoints = data.map((value, i) => ({
    x: padding + (i * (width - 2 * padding) / (data.length - 1 || 1)),
    y: height - padding - ((value - min) / range) * (height - 2 * padding),
  }));

  const pathData = normalizedPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
    .join(' ');

  return (
    <svg width={width} height={height} className={`inline-block ${className}`}>
      <path
        d={pathData}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
};

