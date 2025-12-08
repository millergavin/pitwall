import { useMemo, useRef, useEffect, useState } from 'react';
import { Group } from '@visx/group';
import { LinePath } from '@visx/shape';
import { scaleLinear } from '@visx/scale';
import { GridColumns } from '@visx/grid';
import { curveBasis } from '@visx/curve';

export interface LapChartData {
  driver_id: string;
  driver_number: number;
  driver_name: string;
  name_acronym: string;
  team_id: string;
  team_name: string;
  display_name?: string;
  color_hex: string;
  lap_number: number;
  position: number;
}

export interface ClassificationData {
  driver_id: string;
  grid_position: number | null;
  finish_position: number | null;
  laps_completed: number | null;
}

interface LapChartProps {
  data: LapChartData[];
  classification?: ClassificationData[];
}

// Margins
const margin = { top: 20, right: 120, bottom: 40, left: 60 };

export const LapChart = ({ data, classification = [] }: LapChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 600 });
  const [hoveredDriverId, setHoveredDriverId] = useState<string | null>(null);

  // Measure container and update dimensions
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      if (entries[0]) {
        const { width, height } = entries[0].contentRect;
        setDimensions({ width, height });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  const { width, height } = dimensions;

  // Process data for chart
  const chartData = useMemo(() => {
    if (!data.length) return { drivers: [], maxLap: 0, maxPosition: 0 };

    // Create a map of classification data for quick lookup
    const classificationMap = new Map<string, ClassificationData>();
    classification.forEach((entry) => {
      classificationMap.set(entry.driver_id, entry);
    });

    // Group data by driver
    const driversMap = new Map<string, {
      driver_id: string;
      driver_number: number;
      driver_name: string;
      name_acronym: string;
      color_hex: string;
      positions: { lap: number; position: number }[];
    }>();

    let maxLap = 0;
    let maxPosition = 0;

    data.forEach((row) => {
      if (!driversMap.has(row.driver_id)) {
        driversMap.set(row.driver_id, {
          driver_id: row.driver_id,
          driver_number: row.driver_number,
          driver_name: row.driver_name,
          name_acronym: row.name_acronym,
          color_hex: row.color_hex,
          positions: [],
        });
      }

      const driver = driversMap.get(row.driver_id)!;
      driver.positions.push({
        lap: row.lap_number,
        position: row.position,
      });

      maxLap = Math.max(maxLap, row.lap_number);
      maxPosition = Math.max(maxPosition, row.position);
    });

    // Process each driver's positions
    driversMap.forEach((driver) => {
      const classData = classificationMap.get(driver.driver_id);
      
      // Sort positions by lap
      driver.positions.sort((a, b) => a.lap - b.lap);

      // Add grid position at lap 0 (start)
      if (classData?.grid_position) {
        driver.positions.unshift({
          lap: 0,
          position: classData.grid_position,
        });
        maxPosition = Math.max(maxPosition, classData.grid_position);
      }

      // Update final lap with finish position if available
      if (driver.positions.length > 0 && classData?.finish_position) {
        const lastLap = driver.positions[driver.positions.length - 1].lap;
        // Replace the last position with finish position
        driver.positions[driver.positions.length - 1] = {
          lap: lastLap,
          position: classData.finish_position,
        };
        maxPosition = Math.max(maxPosition, classData.finish_position);
      }
    });

    // Recalculate maxLap from all processed positions (including lap 0)
    driversMap.forEach((driver) => {
      driver.positions.forEach((pos) => {
        maxLap = Math.max(maxLap, pos.lap);
      });
    });

    // Sort drivers by starting position (grid position)
    const drivers = Array.from(driversMap.values()).sort((a, b) => {
      const aStart = a.positions.find(p => p.lap === 0)?.position || 
                     a.positions.find(p => p.lap === 1)?.position || 999;
      const bStart = b.positions.find(p => p.lap === 0)?.position || 
                     b.positions.find(p => p.lap === 1)?.position || 999;
      return aStart - bStart;
    });

    return { drivers, maxLap, maxPosition };
  }, [data, classification]);

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-full min-h-[400px]">
        <p className="text-zinc-500">No lap chart data available</p>
      </div>
    );
  }

  const { drivers, maxLap, maxPosition } = chartData;

  // Calculate bounds
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  // Create scales
  const xScale = useMemo(
    () =>
      scaleLinear<number>({
        domain: [0, maxLap], // Include lap 0 (grid position)
        range: [0, xMax],
        nice: false,
      }),
    [maxLap, xMax]
  );

  const yScale = useMemo(
    () =>
      scaleLinear<number>({
        domain: [1, maxPosition],
        range: [0, yMax], // Position 1 at top (y=0), maxPosition at bottom (y=yMax)
        nice: false,
      }),
    [maxPosition, yMax]
  );

  // Accessor functions
  const getX = (d: { lap: number; position: number }) => xScale(d.lap);
  const getY = (d: { lap: number; position: number }) => yScale(d.position);

  const handleMouseLeave = () => {
    setHoveredDriverId(null);
  };

  return (
    <div ref={containerRef} className="w-full h-full min-h-[400px]">
      <svg 
        width={width} 
        height={height}
        onMouseLeave={handleMouseLeave}
      >
        <Group left={margin.left} top={margin.top}>
          {/* Horizontal grid lines - one for each position */}
          {Array.from({ length: maxPosition }, (_, i) => i + 1).map((position) => {
            const y = yScale(position);
            return (
              <line
                key={`grid-h-${position}`}
                x1={0}
                x2={xMax}
                y1={y}
                y2={y}
                stroke="rgba(255, 255, 255, 0.2)"
                strokeWidth={1}
              />
            );
          })}
          <GridColumns
            scale={xScale}
            height={yMax}
            stroke="rgba(255, 255, 255, 0.05)"
            strokeDasharray="2,2"
          />

          {/* Driver position lines */}
          {drivers.map((driver) => {
            const color = driver.color_hex?.startsWith('#')
              ? driver.color_hex
              : `#${driver.color_hex || '666'}`;
            
            const isHovered = hoveredDriverId === driver.driver_id;
            const isOtherHovered = hoveredDriverId && hoveredDriverId !== driver.driver_id;
            
            // Determine opacity: fade others when one is hovered
            const opacity = isOtherHovered ? 0.2 : 1;
            
            // Determine stroke width: thicker when hovered
            const strokeWidth = isHovered ? 3 : 2;

            return (
              <g
                key={driver.driver_id}
                onMouseEnter={() => setHoveredDriverId(driver.driver_id)}
                onMouseLeave={() => setHoveredDriverId(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Invisible wider path for easier hover detection */}
                <LinePath
                  data={driver.positions}
                  x={getX}
                  y={getY}
                  stroke="transparent"
                  strokeWidth={8}
                  curve={curveBasis}
                />
                {/* Visible line */}
                <LinePath
                  data={driver.positions}
                  x={getX}
                  y={getY}
                  stroke={color}
                  strokeWidth={strokeWidth}
                  strokeOpacity={opacity}
                  curve={curveBasis}
                />
              </g>
            );
          })}
        </Group>

        {/* Axes */}
        <Group left={margin.left} top={margin.top}>
          {/* Y-axis labels - one for each position */}
          {Array.from({ length: maxPosition }, (_, i) => i + 1).map((position) => {
            const y = yScale(position);
            return (
              <text
                key={`y-label-${position}`}
                x={-8}
                y={y}
                fill="#71717a"
                fontSize={10}
                fontFamily="var(--font-mono)"
                textAnchor="end"
                dominantBaseline="middle"
              >
                {position}
              </text>
            );
          })}
          
          {/* Y-axis label */}
          <text
            x={-30}
            y={yMax / 2}
            fill="#71717a"
            fontSize={12}
            fontFamily="var(--font-sans)"
            textAnchor="middle"
            transform={`rotate(-90 ${-30} ${yMax / 2})`}
          >
            Position
          </text>

          {/* X-axis line */}
          <line
            x1={0}
            x2={xMax}
            y1={yMax}
            y2={yMax}
            stroke="#71717a"
            strokeWidth={1}
          />

          {/* X-axis ticks and labels */}
          {(() => {
            const ticks = xScale.ticks(Math.min(20, maxLap + 1));
            // Ensure lap 0 is included if we have grid positions
            const hasLap0 = data.some(d => d.lap_number === 0) || 
                           classification.some(c => c.grid_position !== null);
            const allTicks = hasLap0 && !ticks.includes(0) ? [0, ...ticks] : ticks;
            
            return allTicks.map((lap) => {
              const xPos = xScale(lap) ?? 0;
              return (
                <g key={`x-tick-${lap}`}>
                  <line
                    x1={xPos}
                    x2={xPos}
                    y1={yMax}
                    y2={yMax + 5}
                    stroke="#71717a"
                    strokeWidth={1}
                  />
                  <text
                    x={xPos}
                    y={yMax + 20}
                    fill="#71717a"
                    fontSize={10}
                    fontFamily="var(--font-mono)"
                    textAnchor="middle"
                  >
                    {lap === 0 ? 'Grid' : lap}
                  </text>
                </g>
              );
            });
          })()}

          {/* X-axis label */}
          <text
            x={xMax / 2}
            y={yMax + 40}
            fill="#71717a"
            fontSize={12}
            fontFamily="var(--font-sans)"
            textAnchor="middle"
          >
            Lap
          </text>
        </Group>

        {/* Driver labels on the right */}
        <Group left={margin.left + xMax} top={margin.top}>
          {drivers.map((driver) => {
            if (driver.positions.length === 0) return null;
            
            const lastPosition = driver.positions[driver.positions.length - 1];
            const color = driver.color_hex?.startsWith('#')
              ? driver.color_hex
              : `#${driver.color_hex || '666'}`;
            
            const isHovered = hoveredDriverId === driver.driver_id;
            const isOtherHovered = hoveredDriverId && hoveredDriverId !== driver.driver_id;
            
            // Match opacity with the line
            const opacity = isOtherHovered ? 0.2 : 1;
            const fontWeight = isHovered ? 'bold' : 'normal';

            return (
              <text
                key={driver.driver_id}
                x={8}
                y={yScale(lastPosition.position)}
                fill={color}
                fontSize={12}
                fontFamily="var(--font-sans)"
                dominantBaseline="middle"
                opacity={opacity}
                fontWeight={fontWeight}
                onMouseEnter={() => setHoveredDriverId(driver.driver_id)}
                onMouseLeave={() => setHoveredDriverId(null)}
                style={{ cursor: 'pointer' }}
              >
                {driver.name_acronym}
              </text>
            );
          })}
        </Group>
      </svg>
    </div>
  );
};
