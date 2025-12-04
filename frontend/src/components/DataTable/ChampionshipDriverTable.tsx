import { 
  Table, 
  TableHeader, 
  TableHeaderCell, 
  TableBody, 
  TableRow, 
  TableCell,
  DriverNameCell,
  PositionCell,
} from '../Table';
import type { DriverImageType } from '../Table';

interface Driver {
  driver_id: string;
  driver_number?: number;
  driver_name: string;
  name_acronym: string;
  team_name: string;
  logo_url?: string;
  cumulative_points: number;
  color_hex?: string;
  headshot_url?: string | null;
  headshot_override?: string | null;
}

interface ChampionshipDriverTableProps {
  drivers: Driver[];
  season: number;
  hoveredDriverId?: string | null;
  selectedDriverIds?: Set<string>;
  onHoverDriver?: (driverId: string | null) => void;
  onToggleDriver?: (driverId: string) => void;
  onResetSelection?: () => void;
  showPointsAdded?: boolean;
  pointsAddedMap?: Map<string, number>;
  title?: string;
  subtitle?: string;
  driverImageType?: DriverImageType;
}

export const ChampionshipDriverTable = ({
  drivers,
  season,
  selectedDriverIds,
  onHoverDriver,
  onToggleDriver,
  onResetSelection,
  showPointsAdded = false,
  pointsAddedMap,
  title,
  subtitle,
  driverImageType = 'team-logo',
}: ChampionshipDriverTableProps) => {
  const hasSelections = selectedDriverIds && selectedDriverIds.size > 0;

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
            {title || "WORLD DRIVERS' CHAMPIONSHIP"}
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
            <TableHeaderCell>Driver</TableHeaderCell>
            {showPointsAdded && <TableHeaderCell align="right" width="4rem">+</TableHeaderCell>}
            <TableHeaderCell align="right" width="4rem">Pts</TableHeaderCell>
          </tr>
        </TableHeader>
        <TableBody>
          {drivers.map((driver, index) => {
            const isSelected = selectedDriverIds?.has(driver.driver_id);
            const isFaded = hasSelections && !isSelected;
            const pointsAdded = pointsAddedMap?.get(driver.driver_id) || 0;

            return (
              <TableRow
                key={driver.driver_id}
                selected={isSelected}
                faded={isFaded}
                onClick={() => onToggleDriver?.(driver.driver_id)}
                onMouseEnter={() => onHoverDriver?.(driver.driver_id)}
                onMouseLeave={() => onHoverDriver?.(null)}
              >
                {/* Position */}
                <PositionCell position={index + 1} />

                {/* Driver Name with Team Logo or Avatar */}
                <TableCell>
                  <DriverNameCell
                    driverName={driver.driver_name}
                    nameAcronym={driver.name_acronym}
                    driverNumber={driver.driver_number}
                    teamLogoUrl={driver.logo_url}
                    teamName={driver.team_name}
                    headshotUrl={driver.headshot_url}
                    headshotOverride={driver.headshot_override}
                    teamColor={driver.color_hex}
                    imageType={driverImageType}
                  />
                </TableCell>

                {/* Points Added (conditional) */}
                {showPointsAdded && (
                  <TableCell align="right" mono size="xs" color="zinc-500">
                    +{pointsAdded}
                  </TableCell>
                )}

                {/* Cumulative Points */}
                <TableCell align="right" mono bold size="base">
                  {driver.cumulative_points}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
};

