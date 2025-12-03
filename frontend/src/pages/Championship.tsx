import { useState, useEffect } from 'react';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { ChampionshipStandingsChart } from '../components/ChampionshipStandingsChart';
import { StandingsTable } from '../components/StandingsTable';
import { TabButton } from '../components/TabButton';
import { api } from '../api/client';

type StandingsType = 'drivers' | 'constructors';

export const Championship = () => {
  const [standingsType, setStandingsType] = useState<StandingsType>('drivers');
  const [season, setSeason] = useState(2025); // Default to current season
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hoveredEntityId, setHoveredEntityId] = useState<string | null>(null);
  const [selectedEntityIds, setSelectedEntityIds] = useState<Set<string>>(new Set());
  const [hoveredMeeting, setHoveredMeeting] = useState<{
    round: number;
    name: string;
    emoji: string;
  } | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const standingsData = standingsType === 'drivers'
          ? await api.standings.drivers(season)
          : await api.standings.constructors(season);
        setData(standingsData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [standingsType, season]);

  // Toggle entity selection
  const handleToggleEntity = (entityId: string) => {
    setSelectedEntityIds((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(entityId)) {
        newSet.delete(entityId);
      } else {
        newSet.add(entityId);
      }
      return newSet;
    });
  };

  // Reset selection (show all)
  const handleResetSelection = () => {
    setSelectedEntityIds(new Set());
  };

  // Generate available seasons (2023-2025 for now)
  const availableSeasons = [2023, 2024, 2025];

  return (
    <PageLayout pageTitle="Championship" sidebar={<NavSidebar />}>
      <div className="flex flex-col h-full">
        {/* Controls */}
        <div className="flex items-center gap-4 mb-4 flex-shrink-0">
          <div className="flex gap-2">
            <TabButton
              size="md"
              active={standingsType === 'drivers'}
              onClick={() => setStandingsType('drivers')}
            >
              Drivers
            </TabButton>
            <TabButton
              size="md"
              active={standingsType === 'constructors'}
              onClick={() => setStandingsType('constructors')}
            >
              Constructors
            </TabButton>
          </div>

          {/* Season Selector */}
          <select
            value={season}
            onChange={(e) => setSeason(Number(e.target.value))}
            className="px-3 py-2 bg-zinc-950 border border-zinc-900 text-white rounded-corner text-sm hover:bg-zinc-900 transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-f1-red"
          >
            {availableSeasons.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        {/* Chart and Table Layout */}
        <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
          {/* Standings Table */}
          {!loading && !error && (
            <div className="bg-1 p-4 rounded-corner lg:w-[400px] flex-shrink-0 overflow-auto">
              <StandingsTable
                data={data}
                type={standingsType}
                season={season}
                onHoverEntity={setHoveredEntityId}
                hoveredEntityId={hoveredEntityId}
                selectedEntityIds={selectedEntityIds}
                onToggleEntity={handleToggleEntity}
                onResetSelection={handleResetSelection}
                hoveredMeeting={hoveredMeeting}
              />
            </div>
          )}

          {/* Chart */}
          <div className="bg-1 p-4 rounded-corner flex-1 min-h-0 overflow-auto">
            {loading && (
              <div className="flex items-center justify-center h-full">
                <p className="text-zinc-600">Loading...</p>
              </div>
            )}
            
            {error && (
              <div className="flex items-center justify-center h-full">
                <p className="text-f1-red">{error}</p>
              </div>
            )}
            
            {!loading && !error && (
              <ChampionshipStandingsChart
                data={data}
                type={standingsType}
                hoveredEntityId={hoveredEntityId}
                selectedEntityIds={selectedEntityIds}
                onHoverMeeting={setHoveredMeeting}
                hoveredMeeting={hoveredMeeting}
                onHoverEntity={setHoveredEntityId}
                onToggleEntity={handleToggleEntity}
              />
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

