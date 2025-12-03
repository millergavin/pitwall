import { useState, useEffect } from 'react';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { TeamCard, type TeamCardData } from '../components/TeamCard';
import { api } from '../api/client';

export const Teams = () => {
  const [season, setSeason] = useState(2025);
  const [teams, setTeams] = useState<TeamCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTeams = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.teamsRoster(season);
        setTeams(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load teams');
      } finally {
        setLoading(false);
      }
    };

    fetchTeams();
  }, [season]);

  // Generate available seasons (2023-2025 for now)
  const availableSeasons = [2023, 2024, 2025];

  return (
    <PageLayout pageTitle="Teams" sidebar={<NavSidebar />}>
      <div className="space-y-6 overflow-y-auto flex-1">
        {/* Season Selector */}
        <div className="flex items-center gap-4">
          <label className="text-zinc-400 text-sm">Season:</label>
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

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center h-[400px]">
            <p className="text-zinc-600">Loading teams...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex items-center justify-center h-[400px]">
            <p className="text-f1-red">{error}</p>
          </div>
        )}

        {/* Teams Grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            {teams.map((team) => (
              <TeamCard
                key={team.team_id}
                team={team}
                onClick={() => {
                  // TODO: Navigate to team detail page
                  console.log('Clicked team:', team.team_name);
                }}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && teams.length === 0 && (
          <div className="flex items-center justify-center h-[400px]">
            <p className="text-zinc-600">No teams found for {season} season</p>
          </div>
        )}
      </div>
    </PageLayout>
  );
};

