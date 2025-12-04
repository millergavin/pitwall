import { useState } from 'react';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { TabButton } from '../components/TabButton';
import { 
  Table, 
  TableHeader, 
  TableHeaderCell, 
  TableBody, 
  TableRow, 
  TableCell,
  SparklineCell,
  DriverNameCell,
} from '../components/Table';
import {
  ChampionshipDriverTable,
  ChampionshipConstructorTable,
  SessionResultsTable,
} from '../components/DataTable';

export const Playground = () => {
  const [selectedDrivers, setSelectedDrivers] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<'tables' | 'tabs'>('tables');

  // Mock data for championship driver standings (with trend data)
  const championshipDrivers = [
    { driver_id: '1', driver_number: 1, driver_name: 'Max Verstappen', name_acronym: 'VER', team_name: 'Red Bull Racing', cumulative_points: 575, color_hex: '0600EF', trend: [400, 425, 450, 500, 550, 575] },
    { driver_id: '2', driver_number: 11, driver_name: 'Sergio Perez', name_acronym: 'PER', team_name: 'Red Bull Racing', cumulative_points: 285, color_hex: '0600EF', trend: [200, 220, 240, 255, 270, 285] },
    { driver_id: '3', driver_number: 44, driver_name: 'Lewis Hamilton', name_acronym: 'HAM', team_name: 'Mercedes', cumulative_points: 234, color_hex: '00D2BE', trend: [150, 170, 185, 205, 220, 234] },
    { driver_id: '4', driver_number: 14, driver_name: 'Fernando Alonso', name_acronym: 'ALO', team_name: 'Aston Martin', cumulative_points: 206, color_hex: '006F62', trend: [120, 145, 165, 180, 195, 206] },
    { driver_id: '5', driver_number: 55, driver_name: 'Carlos Sainz', name_acronym: 'SAI', team_name: 'Ferrari', cumulative_points: 200, color_hex: 'DC0000', trend: [130, 150, 165, 180, 190, 200] },
  ];

  // Mock data for championship constructor standings
  const championshipConstructors = [
    { team_id: '1', team_name: 'Red Bull Racing', display_name: 'Red Bull', cumulative_points: 860 },
    { team_id: '2', team_name: 'Mercedes', cumulative_points: 409 },
    { team_id: '3', team_name: 'Ferrari', cumulative_points: 406 },
    { team_id: '4', team_name: 'Aston Martin', cumulative_points: 280 },
    { team_id: '5', team_name: 'McLaren', cumulative_points: 302 },
  ];

  // Mock data for session results (with varied position changes)
  const sessionResults = [
    { driver_id: '1', driver_number: 1, driver_name: 'Max Verstappen', name_acronym: 'VER', team_name: 'Red Bull Racing', grid_position: 1, finish_position: 1, duration_ms: 5403234, gap_to_leader_ms: 0, points: 26, fastest_lap: true },
    { driver_id: '2', driver_number: 11, driver_name: 'Sergio Perez', name_acronym: 'PER', team_name: 'Red Bull Racing', grid_position: 4, finish_position: 2, duration_ms: 5403234, gap_to_leader_ms: 18234, points: 18 },
    { driver_id: '3', driver_number: 44, driver_name: 'Lewis Hamilton', name_acronym: 'HAM', team_name: 'Mercedes', grid_position: 7, finish_position: 3, duration_ms: 5403234, gap_to_leader_ms: 22456, points: 15 },
    { driver_id: '4', driver_number: 14, driver_name: 'Fernando Alonso', name_acronym: 'ALO', team_name: 'Aston Martin', grid_position: 2, finish_position: 4, duration_ms: 5403234, gap_to_leader_ms: 28901, points: 12 },
    { driver_id: '5', driver_number: 55, driver_name: 'Carlos Sainz', name_acronym: 'SAI', team_name: 'Ferrari', grid_position: 3, finish_position: 5, duration_ms: 5403234, gap_to_leader_ms: 32678, points: 10 },
    { driver_id: '6', driver_number: 16, driver_name: 'Charles Leclerc', name_acronym: 'LEC', team_name: 'Ferrari', grid_position: 10, finish_position: 6, duration_ms: 5403234, gap_to_leader_ms: 45123, points: 8 },
  ];

  // Mock data for driver standings (old format for primitive examples)
  const driverStandings = [
    { id: '1', position: 1, name: 'Max Verstappen', acronym: 'VER', team: 'Red Bull Racing', logo: '/assets/teams/red-bull.png', points: 575, pointsAdded: 26 },
    { id: '2', position: 2, name: 'Sergio Perez', acronym: 'PER', team: 'Red Bull Racing', logo: '/assets/teams/red-bull.png', points: 285, pointsAdded: 18 },
    { id: '3', position: 3, name: 'Lewis Hamilton', acronym: 'HAM', team: 'Mercedes', logo: '/assets/teams/mercedes.png', points: 234, pointsAdded: 15 },
    { id: '4', position: 4, name: 'Fernando Alonso', acronym: 'ALO', team: 'Aston Martin', logo: '/assets/teams/aston-martin.png', points: 206, pointsAdded: 12 },
    { id: '5', position: 5, name: 'Carlos Sainz', acronym: 'SAI', team: 'Ferrari', logo: '/assets/teams/ferrari.png', points: 200, pointsAdded: 10 },
  ];

  // Mock data for constructor standings (old format for primitive examples)
  const constructorStandings = [
    { id: '1', position: 1, name: 'Red Bull Racing', logo: '/assets/teams/red-bull.png', points: 860 },
    { id: '2', position: 2, name: 'Mercedes', logo: '/assets/teams/mercedes.png', points: 409 },
    { id: '3', position: 3, name: 'Ferrari', logo: '/assets/teams/ferrari.png', points: 406 },
    { id: '4', position: 4, name: 'Aston Martin', logo: '/assets/teams/aston-martin.png', points: 280 },
    { id: '5', position: 5, name: 'McLaren', logo: '/assets/teams/mclaren.png', points: 302 },
  ];

  // Simple data table
  const simpleData = [
    { id: '1', name: 'Item 1', value: 100, status: 'Active' },
    { id: '2', name: 'Item 2', value: 200, status: 'Active' },
    { id: '3', name: 'Item 3', value: 150, status: 'Inactive' },
    { id: '4', name: 'Item 4', value: 300, status: 'Active' },
  ];

  const handleToggleDriver = (driverId: string) => {
    setSelectedDrivers((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(driverId)) {
        newSet.delete(driverId);
      } else {
        newSet.add(driverId);
      }
      return newSet;
    });
  };

  const handleResetSelection = () => {
    setSelectedDrivers(new Set());
  };

  const hasSelections = selectedDrivers.size > 0;

  return (
    <PageLayout pageTitle="Design System Playground" sidebar={<NavSidebar />}>
      <div className="overflow-y-auto space-y-8">
        {/* Introduction */}
        <div className="bg-black rounded-corner p-6">
          <h2 className="text-white f1-display-bold text-2xl mb-2">
            Design System Playground
          </h2>
          <p className="text-zinc-400 f1-display-regular mb-4">
            A workspace for developing and testing standardized components.
          </p>
          
          <div className="space-y-2 text-sm">
            <div>
              <span className="text-f1-red f1-display-bold">Specialized Components:</span>
              <span className="text-zinc-400 ml-2">Domain-specific tables with built-in behavior</span>
            </div>
            <div>
              <span className="text-blue-400 f1-display-bold">Table Primitives:</span>
              <span className="text-zinc-400 ml-2">Low-level building blocks for custom tables</span>
            </div>
          </div>
        </div>

        {/* Tabs Navigation */}
        <div className="flex gap-2">
          <TabButton
            size="md"
            active={activeTab === 'tables'}
            onClick={() => setActiveTab('tables')}
          >
            Tables
          </TabButton>
          <TabButton
            size="md"
            active={activeTab === 'tabs'}
            onClick={() => setActiveTab('tabs')}
          >
            Tabs
          </TabButton>
        </div>

        {/* Tables Tab Content */}
        {activeTab === 'tables' && (
          <>

        {/* === SPECIALIZED COMPONENTS === */}
        <div className="bg-zinc-900 rounded-corner p-6">
          <h2 className="text-f1-red f1-display-bold text-2xl mb-2">
            🏆 Specialized Components
          </h2>
          <p className="text-zinc-400 f1-display-regular text-sm">
            Pre-built components for specific use cases. These handle domain logic, interactions, and formatting.
          </p>
        </div>

        {/* Championship Driver Table - Team Logo */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              ChampionshipDriverTable - Team Logo
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Championship standings with team logos next to driver names.
              Click rows to select, click header to reset selection.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <ChampionshipDriverTable
              drivers={championshipDrivers}
              season={2025}
              selectedDriverIds={selectedDrivers}
              onToggleDriver={handleToggleDriver}
              onResetSelection={handleResetSelection}
              driverImageType="team-logo"
            />
          </div>
        </div>

        {/* Championship Driver Table - Driver Avatar */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              ChampionshipDriverTable - Driver Avatar
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Championship standings with driver profile pictures in team colors.
              More personal, driver-focused presentation.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <ChampionshipDriverTable
              drivers={championshipDrivers}
              season={2025}
              driverImageType="driver-avatar"
            />
          </div>

          <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
            <div className="text-zinc-300 mb-2">Props:</div>
            <div>drivers: Driver[]</div>
            <div>season: number</div>
            <div>driverImageType?: 'team-logo' | 'driver-avatar' (default: 'team-logo')</div>
            <div>selectedDriverIds?: Set&lt;string&gt;</div>
            <div>onToggleDriver?: (driverId: string) =&gt; void</div>
            <div>onResetSelection?: () =&gt; void</div>
            <div>showPointsAdded?: boolean</div>
            <div>pointsAddedMap?: Map&lt;string, number&gt;</div>
          </div>
        </div>

        {/* Championship Constructor Table */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              ChampionshipConstructorTable
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Constructor championship standings with same interaction pattern as drivers.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <ChampionshipConstructorTable
              constructors={championshipConstructors}
              season={2025}
            />
          </div>
        </div>

        {/* Session Results Table - Team Logo */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              SessionResultsTable - Team Logo
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Race results with team logos and position change indicators.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <SessionResultsTable
              results={sessionResults}
              sessionType="race"
              title="2025 Abu Dhabi Grand Prix - Race Results"
              onDriverClick={(driverId) => console.log('Navigate to driver:', driverId)}
              showPositionChange
              showPoints
              showFastestLap
              driverImageType="team-logo"
            />
          </div>
        </div>

        {/* Session Results Table - Driver Avatar */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              SessionResultsTable - Driver Avatar
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Race results with driver profile pictures for more personality.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <SessionResultsTable
              results={sessionResults}
              sessionType="race"
              title="2025 Abu Dhabi Grand Prix - Race Results"
              onDriverClick={(driverId) => console.log('Navigate to driver:', driverId)}
              showPositionChange
              showPoints
              showFastestLap
              driverImageType="driver-avatar"
            />
          </div>
        </div>

        {/* Session Results Table - Position Change */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              SessionResultsTable - Position Change
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Shows position change indicators in a dedicated column for alignment.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <SessionResultsTable
              results={sessionResults}
              sessionType="race"
              title="2025 Abu Dhabi Grand Prix - Race Results"
              onDriverClick={(driverId) => console.log('Navigate to driver:', driverId)}
              showPositionChange
              showPoints
              showFastestLap
            />
          </div>

          <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
            <div className="text-zinc-300 mb-2">Props:</div>
            <div>results: SessionResult[]</div>
            <div>sessionType: 'race' | 'qualifying' | 'practice' | 'sprint'</div>
            <div>driverImageType?: 'team-logo' | 'driver-avatar' (auto-detected by session type)</div>
            <div>onDriverClick?: (driverId: string) =&gt; void</div>
            <div>showPositionChange?: boolean (default: true)</div>
            <div>showPoints?: boolean (default: true)</div>
            <div>showLaps?: boolean (default: false)</div>
            <div>showFastestLap?: boolean (default: true)</div>
          </div>
        </div>

        {/* === TABLE PRIMITIVES === */}
        <div className="bg-zinc-900 rounded-corner p-6">
          <h2 className="text-blue-400 f1-display-bold text-2xl mb-2">
            🧱 Table Primitives
          </h2>
          <p className="text-zinc-400 f1-display-regular text-sm">
            Low-level building blocks for creating custom table layouts. Use these when you need
            complete control over structure and behavior.
          </p>
        </div>

        {/* Driver Standings Table (Championship Style) */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              Custom Table Example (Using Primitives)
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Example of building a custom table using the primitive components.
              Full control over structure, styling, and interactions.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            {/* Table Header */}
            <div className="mb-4 h-[48px] flex flex-col justify-center">
              <h2 className="f1-display-bold text-sm leading-tight">
                <div>
                  <span className="text-zinc-500">2025</span>{' '}
                  <span className="text-zinc-500">FORMULA 1</span>
                </div>
                <div className="text-white text-base">
                  WORLD DRIVERS' CHAMPIONSHIP
                </div>
              </h2>
            </div>

            <Table>
              <TableHeader 
                onClick={handleResetSelection}
                title="Click to reset selection"
              >
                <tr>
                  <TableHeaderCell width="3rem">Pos</TableHeaderCell>
                  <TableHeaderCell>Driver</TableHeaderCell>
                  <TableHeaderCell align="right" width="4rem">+</TableHeaderCell>
                  <TableHeaderCell align="right" width="4rem">Pts</TableHeaderCell>
                </tr>
              </TableHeader>
              <TableBody>
                {driverStandings.map((driver) => {
                  const isSelected = selectedDrivers.has(driver.id);
                  const isFaded = hasSelections && !isSelected;

                  return (
                    <TableRow
                      key={driver.id}
                      selected={isSelected}
                      faded={isFaded}
                      onClick={() => handleToggleDriver(driver.id)}
                    >
                      <TableCell mono size="xs" color="zinc-500">
                        {driver.position}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="w-6 h-6 bg-zinc-800 rounded flex-shrink-0" />
                          <div className="flex flex-col">
                            <span className="text-white font-extrabold text-sm">
                              {driver.name.split(' ').pop()}
                            </span>
                            <span className="text-zinc-500 f1-display-bold text-xs">
                              {driver.acronym}
                              <span className="inline-block w-3" />
                              #{driver.position}
                            </span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell align="right" mono size="xs" color="zinc-500">
                        +{driver.pointsAdded}
                      </TableCell>
                      <TableCell align="right" mono bold size="base">
                        {driver.points}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Constructor Standings Table */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              Simplified Table (Primitives)
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              A cleaner layout using primitives without complex interactions.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <Table>
              <TableHeader>
                <tr>
                  <TableHeaderCell width="3rem">Pos</TableHeaderCell>
                  <TableHeaderCell>Constructor</TableHeaderCell>
                  <TableHeaderCell align="right" width="4rem">Pts</TableHeaderCell>
                </tr>
              </TableHeader>
              <TableBody>
                {constructorStandings.map((team) => (
                  <TableRow key={team.id}>
                    <TableCell mono size="xs" color="zinc-500">
                      {team.position}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <div className="w-6 h-6 bg-zinc-800 rounded flex-shrink-0" />
                        <span className="text-white">{team.name}</span>
                      </div>
                    </TableCell>
                    <TableCell align="right" mono bold size="base">
                      {team.points}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Sparkline Cell Example */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              Sparkline Cells
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Mini trend charts for showing performance over time. Great for championship standings.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <Table>
              <TableHeader>
                <tr>
                  <TableHeaderCell width="3rem">Pos</TableHeaderCell>
                  <TableHeaderCell>Driver</TableHeaderCell>
                  <TableHeaderCell align="right" width="4rem">Pts</TableHeaderCell>
                  <TableHeaderCell align="right" width="80px">Trend</TableHeaderCell>
                </tr>
              </TableHeader>
              <TableBody>
                {championshipDrivers.map((driver, index) => (
                  <TableRow key={driver.driver_id}>
                    <TableCell mono size="xs" color="zinc-500">
                      {index + 1}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="text-white font-extrabold text-sm">
                          {driver.name_acronym}
                        </span>
                        <span className="text-zinc-500 text-xs">
                          {driver.team_name}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell align="right" mono bold size="base">
                      {driver.cumulative_points}
                    </TableCell>
                    <SparklineCell
                      data={driver.trend}
                      color={`#${driver.color_hex}`}
                      width={60}
                      height={24}
                    />
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
            <div className="text-zinc-300 mb-2">SparklineCell Props:</div>
            <div>data: number[] (array of values to plot)</div>
            <div>color: string (line color, e.g., '#FF0000')</div>
            <div>width?: number (default: 60)</div>
            <div>height?: number (default: 24)</div>
            <div>strokeWidth?: number (default: 2)</div>
            <div>align?: 'left' | 'center' | 'right' (default: 'right')</div>
          </div>
        </div>

        {/* Driver Name Cell Variants */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              DriverNameCell Variants
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Different formats for displaying driver information based on context.
            </p>
          </div>

          <div className="space-y-4">
            {/* Variant 1: Last Name + Acronym/Number */}
            <div className="bg-zinc-950 p-4 rounded-corner">
              <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                Last Name + Acronym/Number (Default)
              </div>
              <Table>
                <TableBody>
                  <TableRow hoverable={false}>
                    <TableCell>
                      <DriverNameCell
                        driverName="Max Verstappen"
                        nameAcronym="VER"
                        driverNumber={1}
                        teamName="Red Bull Racing"
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <div className="mt-2 text-zinc-500 text-xs f1-display-regular">
                nameFormat="last-name" showTeamName=false
              </div>
            </div>

            {/* Variant 2: Full Name + Team Name */}
            <div className="bg-zinc-950 p-4 rounded-corner">
              <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                Full Name + Team Name
              </div>
              <Table>
                <TableBody>
                  <TableRow hoverable={false}>
                    <TableCell>
                      <DriverNameCell
                        driverName="Max Verstappen"
                        nameAcronym="VER"
                        driverNumber={1}
                        teamName="Red Bull Racing"
                        nameFormat="full-name"
                        showTeamName={true}
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <div className="mt-2 text-zinc-500 text-xs f1-display-regular">
                nameFormat="full-name" showTeamName=true
              </div>
            </div>

            {/* Variant 3: Last Name + Team Name */}
            <div className="bg-zinc-950 p-4 rounded-corner">
              <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                Last Name + Team Name
              </div>
              <Table>
                <TableBody>
                  <TableRow hoverable={false}>
                    <TableCell>
                      <DriverNameCell
                        driverName="Max Verstappen"
                        nameAcronym="VER"
                        driverNumber={1}
                        teamName="Red Bull Racing"
                        nameFormat="last-name"
                        showTeamName={true}
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <div className="mt-2 text-zinc-500 text-xs f1-display-regular">
                nameFormat="last-name" showTeamName=true
              </div>
            </div>

            {/* Variant 4: Last Name + Points (Leader) */}
            <div className="bg-zinc-950 p-4 rounded-corner">
              <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                Last Name + Points (Leader)
              </div>
              <Table>
                <TableBody>
                  <TableRow hoverable={false}>
                    <TableCell>
                      <DriverNameCell
                        driverName="Max Verstappen"
                        nameAcronym="VER"
                        driverNumber={1}
                        teamName="Red Bull Racing"
                        showPoints={true}
                        points={575}
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <div className="mt-2 text-zinc-500 text-xs f1-display-regular">
                showPoints=true points=575
              </div>
            </div>

            {/* Variant 5: Last Name + Points + Delta */}
            <div className="bg-zinc-950 p-4 rounded-corner">
              <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                Last Name + Points + Delta (Non-Leader)
              </div>
              <Table>
                <TableBody>
                  <TableRow hoverable={false}>
                    <TableCell>
                      <DriverNameCell
                        driverName="Sergio Perez"
                        nameAcronym="PER"
                        driverNumber={11}
                        teamName="Red Bull Racing"
                        showPoints={true}
                        points={285}
                        deltaFromLeader={290}
                      />
                    </TableCell>
                  </TableRow>
                </TableBody>
              </Table>
              <div className="mt-2 text-zinc-500 text-xs f1-display-regular">
                showPoints=true points=285 deltaFromLeader=290
              </div>
            </div>
          </div>

          <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
            <div className="text-zinc-300 mb-2">DriverNameCell Props:</div>
            <div>driverName: string</div>
            <div>nameAcronym: string</div>
            <div>driverNumber?: number</div>
            <div>teamName?: string</div>
            <div>imageType?: 'team-logo' | 'driver-avatar'</div>
            <div>nameFormat?: 'last-name' | 'full-name' (default: 'last-name')</div>
            <div className="text-zinc-300 mt-2">Second Line Display (priority order):</div>
            <div>showPoints?: boolean (highest priority)</div>
            <div>points?: number</div>
            <div>deltaFromLeader?: number</div>
            <div>showTeamName?: boolean</div>
            <div>showNumber?: boolean (default: true, used with acronym)</div>
          </div>
        </div>

        {/* Simple Data Table */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              Simple Data Table
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Basic table with minimal styling for general data display.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <Table>
              <TableHeader sticky>
                <tr>
                  <TableHeaderCell>Name</TableHeaderCell>
                  <TableHeaderCell align="right">Value</TableHeaderCell>
                  <TableHeaderCell align="center">Status</TableHeaderCell>
                </tr>
              </TableHeader>
              <TableBody>
                {simpleData.map((item) => (
                  <TableRow key={item.id} hoverable={false}>
                    <TableCell>{item.name}</TableCell>
                    <TableCell align="right" mono>
                      {item.value}
                    </TableCell>
                    <TableCell align="center">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          item.status === 'Active'
                            ? 'bg-green-900/30 text-green-400'
                            : 'bg-zinc-800 text-zinc-500'
                        }`}
                      >
                        {item.status}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Compact Variant */}
        <div className="bg-black rounded-corner p-6">
          <div className="mb-4">
            <h3 className="text-white f1-display-bold text-xl mb-2">
              Compact Table Variant
            </h3>
            <p className="text-zinc-400 f1-display-regular text-sm mb-4">
              Denser spacing for displaying more data in less space.
            </p>
          </div>

          <div className="bg-zinc-950 p-4 rounded-corner">
            <Table variant="compact">
              <TableHeader>
                <tr>
                  <TableHeaderCell>Driver</TableHeaderCell>
                  <TableHeaderCell align="center">Number</TableHeaderCell>
                  <TableHeaderCell>Team</TableHeaderCell>
                  <TableHeaderCell align="right">Points</TableHeaderCell>
                </tr>
              </TableHeader>
              <TableBody>
                {driverStandings.map((driver) => (
                  <TableRow key={driver.id}>
                    <TableCell size="xs">
                      <div className="flex flex-col">
                        <span className="text-white">{driver.name}</span>
                        <span className="text-zinc-500 text-xs f1-display-regular">
                          {driver.acronym}
                          <span className="inline-block w-3" />
                          #{driver.position}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell align="center" mono size="xs" color="zinc-500">
                      {driver.position}
                    </TableCell>
                    <TableCell size="xs" color="zinc-400">
                      {driver.team}
                    </TableCell>
                    <TableCell align="right" mono size="xs">
                      {driver.points}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>

        {/* Component Props Reference */}
        <div className="bg-black rounded-corner p-6">
          <h3 className="text-white f1-display-bold text-xl mb-4">
            Component Props Reference
          </h3>
          
          <div className="space-y-6">
            {/* Table Props */}
            <div>
              <h4 className="text-white f1-display-bold text-base mb-2">Table</h4>
              <div className="bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div>variant: 'default' | 'compact' | 'spacious'</div>
                <div>className?: string</div>
              </div>
            </div>

            {/* TableHeader Props */}
            <div>
              <h4 className="text-white f1-display-bold text-base mb-2">TableHeader</h4>
              <div className="bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div>sticky?: boolean</div>
                <div>onClick?: () =&gt; void</div>
                <div>title?: string</div>
                <div>className?: string</div>
              </div>
            </div>

            {/* TableRow Props */}
            <div>
              <h4 className="text-white f1-display-bold text-base mb-2">TableRow</h4>
              <div className="bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div>selected?: boolean</div>
                <div>faded?: boolean</div>
                <div>hoverable?: boolean (default: true)</div>
                <div>onClick?: () =&gt; void</div>
                <div>onMouseEnter?: () =&gt; void</div>
                <div>onMouseLeave?: () =&gt; void</div>
                <div>className?: string</div>
              </div>
            </div>

            {/* TableCell Props */}
            <div>
              <h4 className="text-white f1-display-bold text-base mb-2">TableCell</h4>
              <div className="bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div>align?: 'left' | 'center' | 'right'</div>
                <div>mono?: boolean</div>
                <div>bold?: boolean</div>
                <div>size?: 'xs' | 'sm' | 'base' | 'lg'</div>
                <div>color?: 'white' | 'zinc-400' | 'zinc-500' | 'zinc-600'</div>
                <div>className?: string</div>
              </div>
            </div>

            {/* TableHeaderCell Props */}
            <div>
              <h4 className="text-white f1-display-bold text-base mb-2">TableHeaderCell</h4>
              <div className="bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div>align?: 'left' | 'center' | 'right'</div>
                <div>width?: string</div>
                <div>className?: string</div>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Example */}
        <div className="bg-black rounded-corner p-6">
          <h3 className="text-white f1-display-bold text-xl mb-4">
            Usage Example
          </h3>
          <div className="bg-zinc-950 p-4 rounded overflow-x-auto">
            <pre className="text-zinc-400 text-sm f1-display-regular">
{`import {
  Table,
  TableHeader,
  TableHeaderCell,
  TableBody,
  TableRow,
  TableCell,
} from '../components/Table';

<Table>
  <TableHeader>
    <tr>
      <TableHeaderCell>Name</TableHeaderCell>
      <TableHeaderCell align="right">Value</TableHeaderCell>
    </tr>
  </TableHeader>
  <TableBody>
    {data.map((item) => (
      <TableRow key={item.id}>
        <TableCell>{item.name}</TableCell>
        <TableCell align="right" mono>
          {item.value}
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>`}
            </pre>
          </div>
        </div>
          </>
        )}

        {/* Tabs Tab Content */}
        {activeTab === 'tabs' && (
          <>
            {/* Tabs Overview */}
            <div className="bg-zinc-900 rounded-corner p-6">
              <h2 className="text-blue-400 f1-display-bold text-2xl mb-2">
                🗂️ Tab Components
              </h2>
              <p className="text-zinc-400 f1-display-regular text-sm">
                Tab navigation components for switching between different views or content sections.
              </p>
            </div>

            {/* TabButton Component */}
            <div className="bg-black rounded-corner p-6">
              <div className="mb-4">
                <h3 className="text-white f1-display-bold text-xl mb-2">
                  TabButton - Default Variant
                </h3>
                <p className="text-zinc-400 f1-display-regular text-sm mb-4">
                  Original tab button with F1 red active state and solid backgrounds.
                </p>
              </div>

              {/* Size Variants */}
              <div className="space-y-6">
                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    Small Size
                  </div>
                  <div className="flex gap-2">
                    <TabButton size="sm" active>Active</TabButton>
                    <TabButton size="sm">Inactive</TabButton>
                    <TabButton size="sm" disabled>Disabled</TabButton>
                  </div>
                </div>

                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    Medium Size (Default)
                  </div>
                  <div className="flex gap-2">
                    <TabButton size="md" active>Active</TabButton>
                    <TabButton size="md">Inactive</TabButton>
                    <TabButton size="md" disabled>Disabled</TabButton>
                  </div>
                </div>

                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    Large Size
                  </div>
                  <div className="flex gap-2">
                    <TabButton size="lg" active>Active</TabButton>
                    <TabButton size="lg">Inactive</TabButton>
                    <TabButton size="lg" disabled>Disabled</TabButton>
                  </div>
                </div>
              </div>

              <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div className="text-zinc-300 mb-2">Props:</div>
                <div>variant?: 'default' | 'ghost' (default: 'default')</div>
                <div>size?: 'sm' | 'md' | 'lg' (default: 'md')</div>
                <div>active?: boolean (default: false)</div>
                <div>disabled?: boolean</div>
                <div>children: ReactNode</div>
                <div>className?: string</div>
                <div>...props: ButtonHTMLAttributes</div>
              </div>
            </div>

            {/* TabButton Ghost Variant */}
            <div className="bg-black rounded-corner p-6">
              <div className="mb-4">
                <h3 className="text-white f1-display-bold text-xl mb-2">
                  TabButton - Ghost Variant
                </h3>
                <p className="text-zinc-400 f1-display-regular text-sm mb-4">
                  Subtle tab style with zinc-700 active background and no borders.
                </p>
              </div>

              {/* Size Variants */}
              <div className="space-y-6">
                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    Small Size
                  </div>
                  <div className="flex gap-2">
                    <TabButton variant="ghost" size="sm" active>Active</TabButton>
                    <TabButton variant="ghost" size="sm">Inactive</TabButton>
                    <TabButton variant="ghost" size="sm" disabled>Disabled</TabButton>
                  </div>
                </div>

                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    Medium Size (Default)
                  </div>
                  <div className="flex gap-2">
                    <TabButton variant="ghost" size="md" active>Active</TabButton>
                    <TabButton variant="ghost" size="md">Inactive</TabButton>
                    <TabButton variant="ghost" size="md" disabled>Disabled</TabButton>
                  </div>
                </div>

                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    Large Size
                  </div>
                  <div className="flex gap-2">
                    <TabButton variant="ghost" size="lg" active>Active</TabButton>
                    <TabButton variant="ghost" size="lg">Inactive</TabButton>
                    <TabButton variant="ghost" size="lg" disabled>Disabled</TabButton>
                  </div>
                </div>

                <div className="bg-zinc-950 p-4 rounded-corner">
                  <div className="text-zinc-400 text-sm mb-3 f1-display-bold">
                    In Context
                  </div>
                  <div className="flex gap-2">
                    <TabButton variant="ghost" active>Overview</TabButton>
                    <TabButton variant="ghost">Details</TabButton>
                    <TabButton variant="ghost">Analytics</TabButton>
                    <TabButton variant="ghost">Settings</TabButton>
                  </div>
                </div>
              </div>

              <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div className="text-zinc-300 mb-2">Ghost Variant Styling:</div>
                <div>Active: bg-zinc-700 + text-white</div>
                <div>Inactive: bg-transparent + text-zinc-600</div>
                <div>Hover: Subtle background + lighter text</div>
              </div>
            </div>

            {/* Tab Group Example */}
            <div className="bg-black rounded-corner p-6">
              <div className="mb-4">
                <h3 className="text-white f1-display-bold text-xl mb-2">
                  Tab Group Pattern
                </h3>
                <p className="text-zinc-400 f1-display-regular text-sm mb-4">
                  How to use TabButtons together for switching content.
                </p>
              </div>

              <div className="bg-zinc-950 p-4 rounded-corner">
                <div className="flex gap-2 mb-4">
                  <TabButton active>Overview</TabButton>
                  <TabButton>Details</TabButton>
                  <TabButton>Analytics</TabButton>
                  <TabButton>Settings</TabButton>
                </div>
                
                <div className="bg-zinc-900 p-4 rounded-corner text-zinc-400">
                  Tab content would go here...
                </div>
              </div>

              <div className="mt-4 bg-zinc-950 p-4 rounded text-sm text-zinc-400 f1-display-regular">
                <div className="text-zinc-300 mb-2">Usage Example:</div>
                <pre className="text-xs">{`const [activeTab, setActiveTab] = useState('overview');

<div className="flex gap-2">
  <TabButton
    active={activeTab === 'overview'}
    onClick={() => setActiveTab('overview')}
  >
    Overview
  </TabButton>
  <TabButton
    active={activeTab === 'details'}
    onClick={() => setActiveTab('details')}
  >
    Details
  </TabButton>
</div>

{activeTab === 'overview' && <OverviewContent />}
{activeTab === 'details' && <DetailsContent />}`}</pre>
              </div>
            </div>

            {/* Design Guidelines */}
            <div className="bg-black rounded-corner p-6">
              <div className="mb-4">
                <h3 className="text-white f1-display-bold text-xl mb-2">
                  Design Guidelines
                </h3>
              </div>

              <div className="space-y-3 text-sm">
                <div>
                  <span className="text-white f1-display-bold">Active State:</span>
                  <span className="text-zinc-400 ml-2">F1 red background with white text</span>
                </div>
                <div>
                  <span className="text-white f1-display-bold">Inactive State:</span>
                  <span className="text-zinc-400 ml-2">Dark background with zinc-500 text, hover to lighter</span>
                </div>
                <div>
                  <span className="text-white f1-display-bold">Spacing:</span>
                  <span className="text-zinc-400 ml-2">Use gap-2 between tabs for consistent spacing</span>
                </div>
                <div>
                  <span className="text-white f1-display-bold">Typography:</span>
                  <span className="text-zinc-400 ml-2">Uppercase button text with proper letter spacing</span>
                </div>
                <div>
                  <span className="text-white f1-display-bold">Accessibility:</span>
                  <span className="text-zinc-400 ml-2">Focus-visible ring, disabled state support</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </PageLayout>
  );
};
