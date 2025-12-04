import { 
  Table, 
  TableHeader, 
  TableHeaderCell, 
  TableBody, 
  TableRow, 
  TableCell,
  PositionCell,
} from '../Table';

interface Constructor {
  team_id: string;
  team_name: string;
  display_name?: string;
  logo_url?: string;
  cumulative_points: number;
  color_hex?: string;
}

interface ChampionshipConstructorTableProps {
  constructors: Constructor[];
  season: number;
  hoveredConstructorId?: string | null;
  selectedConstructorIds?: Set<string>;
  onHoverConstructor?: (constructorId: string | null) => void;
  onToggleConstructor?: (constructorId: string) => void;
  onResetSelection?: () => void;
  showPointsAdded?: boolean;
  pointsAddedMap?: Map<string, number>;
  title?: string;
  subtitle?: string;
}

export const ChampionshipConstructorTable = ({
  constructors,
  season,
  selectedConstructorIds,
  onHoverConstructor,
  onToggleConstructor,
  onResetSelection,
  showPointsAdded = false,
  pointsAddedMap,
  title,
  subtitle,
}: ChampionshipConstructorTableProps) => {
  const hasSelections = selectedConstructorIds && selectedConstructorIds.size > 0;

  return (
    <div>
      {/* Table Title */}
      <div className="mb-4 h-[48px] flex flex-col justify-center">
        <h2 className="f1-display-bold text-sm leading-tight">
          <div>
            <span className="text-zinc-500">{season}</span>{' '}
            <span className="text-zinc-500">FORMULA 1</span>
          </div>
          <div className="text-white text-base">
            {title || "WORLD CONSTRUCTORS' CHAMPIONSHIP"}
          </div>
          {subtitle && (
            <div className="text-zinc-400 text-xs">{subtitle}</div>
          )}
        </h2>
      </div>

      {/* Table */}
      <Table>
        <TableHeader 
          onClick={onResetSelection}
          title={onResetSelection ? "Click to reset selection" : undefined}
        >
          <tr>
            <TableHeaderCell width="3rem"></TableHeaderCell>
            <TableHeaderCell>Constructor</TableHeaderCell>
            {showPointsAdded && <TableHeaderCell align="right" width="4rem">+</TableHeaderCell>}
            <TableHeaderCell align="right" width="4rem">Pts</TableHeaderCell>
          </tr>
        </TableHeader>
        <TableBody>
          {constructors.map((constructor, index) => {
            const isSelected = selectedConstructorIds?.has(constructor.team_id);
            const isFaded = hasSelections && !isSelected;
            const pointsAdded = pointsAddedMap?.get(constructor.team_id) || 0;

            return (
              <TableRow
                key={constructor.team_id}
                selected={isSelected}
                faded={isFaded}
                onClick={() => onToggleConstructor?.(constructor.team_id)}
                onMouseEnter={() => onHoverConstructor?.(constructor.team_id)}
                onMouseLeave={() => onHoverConstructor?.(null)}
              >
                {/* Position */}
                <PositionCell position={index + 1} />

                {/* Constructor Name + Logo */}
                <TableCell>
                  <div className="flex items-center gap-2">
                    {constructor.logo_url ? (
                      <img
                        src={constructor.logo_url}
                        alt={`${constructor.team_name} logo`}
                        className="w-6 h-6 object-contain flex-shrink-0"
                      />
                    ) : (
                      <div className="w-6 h-6 bg-zinc-800 rounded flex-shrink-0" />
                    )}
                    <span className="text-white">
                      {constructor.display_name || constructor.team_name}
                    </span>
                  </div>
                </TableCell>

                {/* Points Added (conditional) */}
                {showPointsAdded && (
                  <TableCell align="right" mono size="xs" color="zinc-500">
                    +{pointsAdded}
                  </TableCell>
                )}

                {/* Cumulative Points */}
                <TableCell align="right" mono bold size="base">
                  {constructor.cumulative_points}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
};

