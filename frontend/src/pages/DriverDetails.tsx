import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { faArrowLeft, faTrophy, faMedal, faFlagCheckered, faStopwatch } from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';

interface DriverInfo {
  driver_id: string;
  driver_number: number;
  first_name: string;
  last_name: string;
  full_name: string;
  name_acronym: string;
  country_code: string;
  headshot_url: string | null;
  headshot_override: string | null;
  wikipedia_id: string | null;
  birthdate: string | null;
  primary_team_id: string;
  primary_team_name: string;
  color_hex: string;
  team_logo_url: string | null;
  team_display_name: string | null;
}

interface SeasonStats {
  total_points: number;
  wins: number;
  podiums: number;
  points_finishes: number;
  races_entered: number;
  fastest_laps: number;
}

interface RecentResult {
  round_number: number;
  meeting_short_name: string;
  session_type: string;
  finish_position: number | null;
  grid_position: number | null;
  session_points: number;
  fastest_lap: boolean;
  status: string;
  country_code: string;
  emoji_flag: string;
}

interface SeasonProgression {
  round_number: number;
  meeting_short_name: string;
  cumulative_points: number;
  session_points: number;
  finish_position: number | null;
  emoji_flag: string;
}

interface DriverDetailData {
  driver: DriverInfo;
  season_stats: SeasonStats;
  championship_position: number;
  recent_results: RecentResult[];
  season_progression: SeasonProgression[];
}

export const DriverDetails = () => {
  const { driverId } = useParams<{ driverId: string }>();
  const navigate = useNavigate();
  const [season, setSeason] = useState(2025);
  const [data, setData] = useState<DriverDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!driverId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const driverData = await api.driverDetail(driverId, season);
        setData(driverData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load driver details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [driverId, season]);

  const formatPosition = (position: number | null) => {
    if (!position) return '-';
    const suffix = position === 1 ? 'st' : position === 2 ? 'nd' : position === 3 ? 'rd' : 'th';
    return `${position}${suffix}`;
  };

  const getPositionColor = (position: number | null) => {
    if (!position) return 'text-zinc-400';
    if (position === 1) return 'text-yellow-400';
    if (position === 2) return 'text-zinc-300';
    if (position === 3) return 'text-orange-400';
    if (position <= 10) return 'text-green-400';
    return 'text-zinc-400';
  };

  const getSessionTypeLabel = (sessionType: string) => {
    switch (sessionType) {
      case 'race': return 'Race';
      case 'sprint': return 'Sprint';
      case 'quali': return 'Qualifying';
      case 'sprint_quali': return 'Sprint Qualifying';
      default: return sessionType;
    }
  };

  // Generate available seasons (2023-2025 for now)
  const availableSeasons = [2023, 2024, 2025];

  if (loading) {
    return (
      <PageLayout pageTitle="Driver" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      </PageLayout>
    );
  }

  if (error || !data) {
    return (
      <PageLayout pageTitle="Driver" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <p className="text-f1-red text-lg">{error || 'Driver not found'}</p>
        </div>
      </PageLayout>
    );
  }

  const { driver, season_stats, championship_position, recent_results, season_progression } = data;
  const headshotUrl = driver.headshot_override || driver.headshot_url;

  return (
    <PageLayout 
      pageTitle={driver.full_name}
      sidebar={<NavSidebar />}
    >
      <div className="flex flex-col h-full gap-6 overflow-y-auto">
        {/* Back button and season selector */}
        <div className="flex items-center justify-between flex-shrink-0">
          <Button 
            variant="text" 
            size="sm"
            icon={faArrowLeft}
            onClick={() => navigate('/drivers')}
          >
            Back to Drivers
          </Button>

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

        {/* Hero Section */}
        <div 
          className="relative rounded-corner overflow-hidden"
          style={{ 
            height: '280px',
            background: `linear-gradient(135deg, #${driver.color_hex}20 0%, #${driver.color_hex}40 100%)`,
          }}
        >
          {/* Dark overlay */}
          <div
            className="absolute inset-0 bg-black/60"
          />

          {/* Content */}
          <div className="absolute inset-0 flex items-end p-8">
            <div className="flex items-end gap-6 w-full">
              {/* Driver headshot */}
              {headshotUrl && (
                <div className="w-48 h-48 rounded-corner overflow-hidden bg-zinc-900 flex-shrink-0">
                  <img
                    src={headshotUrl}
                    alt={driver.full_name}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              
              {/* Driver info */}
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-3">
                  <div 
                    className="text-white px-3 py-1 rounded text-sm f1-display-bold"
                    style={{ backgroundColor: `#${driver.color_hex}` }}
                  >
                    #{driver.driver_number}
                  </div>
                  {driver.team_logo_url && (
                    <img 
                      src={driver.team_logo_url} 
                      alt={driver.primary_team_name}
                      className="h-8 object-contain"
                    />
                  )}
                </div>
                <h1
                  className="text-white f1-display-bold text-5xl leading-tight uppercase mb-2"
                  style={{
                    textShadow: '0 2px 12px rgba(0, 0, 0, 0.9)',
                  }}
                >
                  {driver.full_name}
                </h1>
                <h2
                  className="text-zinc-300 f1-display-regular text-2xl leading-tight"
                  style={{
                    textShadow: '0 2px 8px rgba(0, 0, 0, 0.9)',
                  }}
                >
                  {driver.team_display_name || driver.primary_team_name}
                </h2>
              </div>

              {/* Championship position badge */}
              {championship_position && (
                <div className="text-right flex-shrink-0">
                  <div className="text-zinc-400 text-sm f1-display-regular mb-1">
                    Championship Position
                  </div>
                  <div className={`f1-display-bold text-6xl ${getPositionColor(championship_position)}`}>
                    {formatPosition(championship_position)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Season Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <div className="bg-black rounded-corner p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faTrophy} className="text-yellow-400 text-sm" />
              <div className="text-zinc-400 text-sm f1-display-regular">Points</div>
            </div>
            <div className="text-white f1-display-bold text-3xl">
              {season_stats.total_points}
            </div>
          </div>

          <div className="bg-black rounded-corner p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faTrophy} className="text-yellow-400 text-sm" />
              <div className="text-zinc-400 text-sm f1-display-regular">Wins</div>
            </div>
            <div className="text-white f1-display-bold text-3xl">
              {season_stats.wins}
            </div>
          </div>

          <div className="bg-black rounded-corner p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faMedal} className="text-orange-400 text-sm" />
              <div className="text-zinc-400 text-sm f1-display-regular">Podiums</div>
            </div>
            <div className="text-white f1-display-bold text-3xl">
              {season_stats.podiums}
            </div>
          </div>

          <div className="bg-black rounded-corner p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faFlagCheckered} className="text-green-400 text-sm" />
              <div className="text-zinc-400 text-sm f1-display-regular">Points Finishes</div>
            </div>
            <div className="text-white f1-display-bold text-3xl">
              {season_stats.points_finishes}
            </div>
          </div>

          <div className="bg-black rounded-corner p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faStopwatch} className="text-purple-400 text-sm" />
              <div className="text-zinc-400 text-sm f1-display-regular">Fastest Laps</div>
            </div>
            <div className="text-white f1-display-bold text-3xl">
              {season_stats.fastest_laps}
            </div>
          </div>

          <div className="bg-black rounded-corner p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faFlagCheckered} className="text-zinc-400 text-sm" />
              <div className="text-zinc-400 text-sm f1-display-regular">Races</div>
            </div>
            <div className="text-white f1-display-bold text-3xl">
              {season_stats.races_entered}
            </div>
          </div>
        </div>

        {/* Two column layout for results and progression */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Results */}
          <div className="bg-black rounded-corner p-6">
            <h2 className="text-white f1-display-bold text-xl mb-4">Recent Results</h2>
            <div className="space-y-3">
              {recent_results.map((result) => (
                <div
                  key={`${result.round_number}-${result.session_type}`}
                  className="flex items-center justify-between p-3 bg-zinc-950 rounded hover:bg-zinc-900 transition-colors"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className="text-2xl">{result.emoji_flag}</div>
                    <div className="flex-1">
                      <div className="text-white f1-display-bold text-sm">
                        {result.meeting_short_name}
                      </div>
                      <div className="text-zinc-500 text-xs f1-display-regular">
                        {getSessionTypeLabel(result.session_type)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    {result.grid_position && (
                      <div className="text-center min-w-[48px]">
                        <div className="text-zinc-400 text-[10px] f1-display-regular">
                          Grid P{result.grid_position}
                        </div>
                      </div>
                    )}
                    <div className={`f1-display-bold text-lg ${getPositionColor(result.finish_position)}`}>
                      {formatPosition(result.finish_position)}
                    </div>
                    {result.fastest_lap && (
                      <div className="w-5 h-5 bg-purple-600 rounded flex items-center justify-center">
                        <FontAwesomeIcon icon={faStopwatch} className="text-white text-[10px]" />
                      </div>
                    )}
                    {result.session_points > 0 && (
                      <div className="text-white f1-display-regular text-sm min-w-12 text-right">
                        +{result.session_points}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Season Progression Chart */}
          <div className="bg-black rounded-corner p-6">
            <h2 className="text-white f1-display-bold text-xl mb-4">Season Progression</h2>
            <div className="space-y-2">
              {season_progression.map((round) => {
                const maxPoints = Math.max(...season_progression.map(r => r.cumulative_points));
                const widthPercent = maxPoints > 0 ? (round.cumulative_points / maxPoints) * 100 : 0;
                
                return (
                  <div
                    key={round.round_number}
                    className="flex items-center gap-2"
                  >
                    <div className="text-zinc-500 text-xs f1-display-regular w-6">
                      R{round.round_number}
                    </div>
                    <div className="flex-1 relative h-8">
                      <div 
                        className="absolute inset-y-0 left-0 rounded transition-all"
                        style={{ 
                          width: `${widthPercent}%`,
                          backgroundColor: `#${driver.color_hex}`,
                        }}
                      />
                      <div className="absolute inset-0 flex items-center px-2">
                        <span className="text-white text-xs f1-display-bold z-10">
                          {round.cumulative_points} pts
                        </span>
                      </div>
                    </div>
                    <div className={`text-xs f1-display-bold w-12 text-right ${getPositionColor(round.finish_position)}`}>
                      {formatPosition(round.finish_position)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

