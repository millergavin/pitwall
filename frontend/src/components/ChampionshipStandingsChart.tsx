import { useMemo, useRef, useEffect, useState } from 'react';
import { Group } from '@visx/group';
import { LinePath } from '@visx/shape';
import { scaleLinear, scalePoint } from '@visx/scale';
import { AxisLeft } from '@visx/axis';
import { GridRows } from '@visx/grid';
import { curveLinear } from '@visx/curve';

interface StandingsDataPoint {
  round_number: number;
  meeting_name: string;
  meeting_short_name: string;
  emoji_flag: string;
  flag_url?: string;
  cumulative_points: number;
  color_hex: string;
  // Driver-specific
  driver_id?: string;
  driver_name?: string;
  name_acronym?: string;
  // Constructor-specific
  team_id?: string;
  team_name?: string;
  display_name?: string;
}

interface ChampionshipStandingsChartProps {
  data: StandingsDataPoint[];
  type: 'drivers' | 'constructors';
  hoveredEntityId?: string | null;
  selectedEntityIds?: Set<string>;
  onHoverMeeting?: (meeting: { round: number; name: string; emoji: string } | null) => void;
  hoveredMeeting?: { round: number; name: string; emoji: string } | null;
  onHoverEntity?: (entityId: string | null) => void;
  onToggleEntity?: (entityId: string) => void;
}

// Margins
const margin = { top: 20, right: 20, bottom: 60, left: 60 };

export const ChampionshipStandingsChart = ({
  data,
  type,
  hoveredEntityId,
  selectedEntityIds,
  onHoverMeeting,
  hoveredMeeting,
  onHoverEntity,
  onToggleEntity,
}: ChampionshipStandingsChartProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 });

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

  // Calculate bounds
  const xMax = width - margin.left - margin.right;
  const yMax = height - margin.top - margin.bottom;

  // Group data by entity (driver or constructor) and add starting point at 0
  const groupedData = useMemo(() => {
    const entityKey = type === 'drivers' ? 'driver_id' : 'team_id';
    const entityNameKey = type === 'drivers' ? 'name_acronym' : 'display_name';
    
    const groups = new Map<string, StandingsDataPoint[]>();
    
    data.forEach((d) => {
      const key = d[entityKey] as string;
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key)!.push(d);
    });
    
    // Sort each group by round_number and add starting point at 0
    groups.forEach((points) => {
      points.sort((a, b) => a.round_number - b.round_number);
      
      // Add a starting point at round 0 with 0 points
      if (points.length > 0) {
        points.unshift({
          ...points[0],
          round_number: 0,
          cumulative_points: 0,
          emoji_flag: '',
        });
      }
    });
    
    return Array.from(groups.entries()).map(([id, points]) => ({
      id,
      name: points[0][entityNameKey] as string,
      color: `#${points[0].color_hex}`, // Add # prefix for hex color
      points,
    }));
  }, [data, type]);

  // Get unique rounds for x-axis, including starting point at 0
  const rounds = useMemo(() => {
    const uniqueRounds = Array.from(
      new Set(data.map((d) => d.round_number))
    ).sort((a, b) => a - b);
    
    // Add round 0 for the starting point
    const roundsWithStart = [0, ...uniqueRounds];
    
    return roundsWithStart.map((round) => {
      const roundData = data.find((d) => d.round_number === round);
      return {
        round,
        emoji: round === 0 ? '' : (roundData?.emoji_flag || ''),
        flagUrl: round === 0 ? '' : (roundData?.flag_url || ''),
      };
    });
  }, [data]);

  // Scales
  const xScale = scalePoint<number>({
    domain: rounds.map((r) => r.round),
    range: [0, xMax],
    padding: 0, // Remove padding so round 0 aligns with y-axis
  });

  const maxPoints = useMemo(
    () => Math.max(...data.map((d) => d.cumulative_points), 0),
    [data]
  );

  const yScale = scaleLinear<number>({
    domain: [0, maxPoints * 1.1], // Add 10% padding at top
    range: [yMax, 0],
    nice: true,
  });

  // Accessors
  const getX = (d: StandingsDataPoint) => xScale(d.round_number) ?? 0;
  const getY = (d: StandingsDataPoint) => yScale(d.cumulative_points) ?? 0;

  if (data.length === 0) {
    return (
      <div ref={containerRef} className="flex items-center justify-center w-full h-full">
        <p className="text-zinc-600">No data available</p>
      </div>
    );
  }

  // Handle mouse move to detect hovered meeting
  const handleMouseMove = (event: React.MouseEvent<SVGSVGElement>) => {
    if (!containerRef.current) return;
    
    const svg = event.currentTarget;
    const point = svg.createSVGPoint();
    point.x = event.clientX;
    point.y = event.clientY;
    const svgPoint = point.matrixTransform(svg.getScreenCTM()?.inverse());
    
    // Adjust for margin
    const x = svgPoint.x - margin.left;
    
    // Always find the closest round (no threshold - edge to edge)
    let closestRound: number | null = null;
    let minDistance = Infinity;
    
    rounds.forEach((r) => {
      const xPos = xScale(r.round) ?? 0;
      const distance = Math.abs(x - xPos);
      if (distance < minDistance && r.round !== 0) {
        minDistance = distance;
        closestRound = r.round;
      }
    });
    
    if (closestRound !== null) {
      const roundData = rounds.find((r) => r.round === closestRound);
      const meetingData = data.find((d) => d.round_number === closestRound);
      if (roundData && meetingData) {
        onHoverMeeting?.({
          round: roundData.round,
          name: meetingData.meeting_short_name,
          emoji: roundData.emoji,
        });
      }
    }
  };
  
  const handleMouseLeave = () => {
    onHoverMeeting?.(null);
    onHoverEntity?.(null);
  };

  return (
    <div ref={containerRef} className="w-full h-full">
      <svg 
        width={width} 
        height={height}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
      <Group left={margin.left} top={margin.top}>
        {/* Grid */}
        <GridRows
          scale={yScale}
          width={xMax}
          stroke="rgba(255, 255, 255, 0.05)"
          strokeDasharray="2,2"
        />

        {/* Lines for each driver/constructor */}
        {groupedData.map((entity) => {
          const isHovered = hoveredEntityId === entity.id;
          const isOtherHovered = hoveredEntityId && hoveredEntityId !== entity.id;
          const hasSelections = selectedEntityIds && selectedEntityIds.size > 0;
          const isSelected = selectedEntityIds?.has(entity.id);
          const isUnselected = hasSelections && !isSelected;
          
          // Determine opacity: selection takes precedence over hover
          let opacity = 1;
          if (isUnselected) {
            opacity = 0.2;
          } else if (isOtherHovered && !hasSelections) {
            opacity = 0.2;
          }
          
          // Determine stroke width: selected or hovered get thicker line
          const strokeWidth = (isSelected || isHovered) ? 3 : 1.5;
          
          // Split the data into before/at and after hovered meeting
          let beforeData = entity.points;
          let afterData: StandingsDataPoint[] = [];
          
          if (hoveredMeeting) {
            const hoveredIndex = entity.points.findIndex(p => p.round_number === hoveredMeeting.round);
            if (hoveredIndex !== -1) {
              beforeData = entity.points.slice(0, hoveredIndex + 1);
              afterData = entity.points.slice(hoveredIndex);
            }
          }
          
          return (
            <g key={entity.id}>
              {/* Main line (up to hovered meeting) */}
              <LinePath<StandingsDataPoint>
                data={beforeData}
                x={getX}
                y={getY}
                stroke={entity.color}
                strokeWidth={strokeWidth}
                strokeOpacity={opacity}
                strokeLinejoin="round"
                curve={curveLinear}
              />
              
              {/* Faded line (after hovered meeting) */}
              {afterData.length > 0 && (
                <LinePath<StandingsDataPoint>
                  data={afterData}
                  x={getX}
                  y={getY}
                  stroke={entity.color}
                  strokeWidth={strokeWidth}
                  strokeOpacity={opacity * 0.2}
                  strokeLinejoin="round"
                  curve={curveLinear}
                />
              )}
              
              {/* Invisible hit area for hover/click detection */}
              <LinePath<StandingsDataPoint>
                data={entity.points}
                x={getX}
                y={getY}
                stroke="transparent"
                strokeWidth={10}
                strokeLinejoin="round"
                curve={curveLinear}
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => onHoverEntity?.(entity.id)}
                onMouseLeave={() => onHoverEntity?.(null)}
                onClick={() => onToggleEntity?.(entity.id)}
              />
            </g>
          );
        })}

        {/* Vertical line for hovered meeting */}
        {hoveredMeeting && (
          <line
            x1={xScale(hoveredMeeting.round) ?? 0}
            x2={xScale(hoveredMeeting.round) ?? 0}
            y1={0}
            y2={yMax}
            stroke="rgba(255, 255, 255, 0.2)"
            strokeWidth={1}
            pointerEvents="none"
          />
        )}

        {/* Axes */}
        <AxisLeft
          scale={yScale}
          stroke="rgba(255, 255, 255, 0.2)"
          tickStroke="rgba(255, 255, 255, 0.2)"
          tickLabelProps={() => ({
            fill: '#ffffff',
            fontSize: 12,
            textAnchor: 'end',
            dx: -4,
            dy: 4,
          })}
        />

        {/* X-axis line */}
        <line
          x1={0}
          x2={xMax}
          y1={yMax}
          y2={yMax}
          stroke="rgba(255, 255, 255, 0.2)"
          strokeWidth={1}
        />

        {/* Circular flag icons for x-axis */}
        {rounds.map((r) => {
          if (r.round === 0 || !r.flagUrl) return null;
          const xPos = xScale(r.round) ?? 0;
          const flagSize = 20;
          const borderWidth = 1.5;
          const totalSize = flagSize + borderWidth * 2;
          const opacity = hoveredMeeting && r.round !== hoveredMeeting.round ? 0.1 : 1;
          
          // Position flags with padding from the axis line
          // totalSize/2 positions the top of the flag, then add extra padding
          const flagYPosition = yMax + totalSize / 2 + 16;
          
          return (
            <g key={`flag-${r.round}`} transform={`translate(${xPos}, ${flagYPosition})`}>
              {/* White border circle (outer) */}
              <circle
                cx={0}
                cy={0}
                r={totalSize / 2}
                fill="white"
                opacity={opacity}
              />
              {/* Circular flag from Iconify (already circular) */}
              <image
                href={r.flagUrl}
                x={-flagSize / 2}
                y={-flagSize / 2}
                width={flagSize}
                height={flagSize}
                opacity={opacity}
                style={{ 
                  transition: 'opacity 0.2s',
                  cursor: 'pointer'
                }}
              />
            </g>
          );
        })}
      </Group>
    </svg>
    </div>
  );
};

