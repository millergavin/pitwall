import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { faArrowLeft, faTrophy, faMedal, faFlagCheckered, faStopwatch } from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';

interface TeamInfo {
  team_id: string;
  team_name: string;
  display_name: string | null;
  color_hex: string;
  logo_url: string | null;
  car_image_url: string | null;
}

interface SeasonStats {
  total_points: number;
  wins: number;
  podiums: number;
  points_finishes: number;
  races_entered: number;
  fastest_laps: number;
}

interface Driver {
  driver_id: string;
  driver_number: number;
  full_name: string;
  name_acronym: string;
  headshot_url: string | null;
  headshot_override: string | null;
  driver_points: number;
}

interface RecentResult {
  round_number: number;
  meeting_short_name: string;
  session_type: string;
  session_points: number;
  country_code: string;
  emoji_flag: string;
}

interface SeasonProgression {
  round_number: number;
  meeting_short_name: string;
  cumulative_points: number;
  session_points: number;
  emoji_flag: string;
}

interface TeamDetailData {
  team: TeamInfo;
  season_stats: SeasonStats;
  championship_position: number;
  drivers: Driver[];
  recent_results: RecentResult[];
  season_progression: SeasonProgression[];
}

export const TeamDetails = () => {
  const { teamId } = useParams<{ teamId: string }>();
  const navigate = useNavigate();
  const [season, setSeason] = useState(2025);
  const [data, setData] = useState<TeamDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!teamId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const teamData = await api.teamDetail(teamId, season);
        setData(teamData);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load team details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [teamId, season]);

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
      <PageLayout pageTitle="Team" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      </PageLayout>
    );
  }

  if (error || !data) {
    return (
      <PageLayout pageTitle="Team" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <p className="text-f1-red text-lg">{error || 'Team not found'}</p>
        </div>
      </PageLayout>
    );
  }

  const { team, season_stats, championship_position, drivers, recent_results, season_progression } = data;

  return (
    <PageLayout 
      pageTitle={team.display_name || team.team_name}
      sidebar={<NavSidebar />}
    >
      <div className="flex flex-col h-full overflow-hidden">
        {/* Back button and season selector - Fixed at top */}
        <div className="flex items-center justify-between flex-shrink-0 mb-6">
          <Button 
            variant="text" 
            size="sm"
            icon={faArrowLeft}
            onClick={() => navigate('/teams')}
          >
            Back to Teams
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

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto space-y-4 lg:space-y-6">
        {/* Hero Section */}
        <div 
          className="relative rounded-corner overflow-hidden"
          style={{ 
            height: '224px',
            background: `linear-gradient(135deg, #${team.color_hex}20 0%, #${team.color_hex}40 100%)`,
          }}
        >
          {/* Dark overlay */}
          <div
            className="absolute inset-0 bg-black/60"
          />

          {/* Content */}
          <div className="absolute inset-0 flex items-end p-4 lg:p-8">
            <div className="flex items-end gap-3 lg:gap-6 w-full">
              {/* Team logo */}
              {team.logo_url && (
                <div className="w-32 h-32 lg:w-48 lg:h-48 rounded-corner overflow-hidden bg-zinc-900 flex items-center justify-center flex-shrink-0 p-4 lg:p-6">
                  <img
                    src={team.logo_url}
                    alt={team.team_name}
                    className="w-full h-full object-contain"
                  />
                </div>
              )}
              
              {/* Team info */}
              <div className="flex-1">
                <h1
                  className="text-white f1-display-bold text-3xl lg:text-5xl leading-tight uppercase mb-1 lg:mb-2"
                  style={{
                    textShadow: '0 2px 12px rgba(0, 0, 0, 0.9)',
                  }}
                >
                  {team.display_name || team.team_name}
                </h1>
              </div>

              {/* Championship position badge */}
              {championship_position && (
                <div className="text-right flex-shrink-0">
                  <div className="text-zinc-400 text-[10px] lg:text-sm f1-display-regular mb-1">
                    Championship Position
                  </div>
                  <div className={`f1-display-bold text-4xl lg:text-6xl ${getPositionColor(championship_position)}`}>
                    {formatPosition(championship_position)}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Current Drivers */}
        <div className="bg-black rounded-corner p-4 lg:p-6">
          <h2 className="text-white f1-display-bold text-lg lg:text-xl mb-3 lg:mb-4">Current Drivers</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 lg:gap-4">
            {drivers.map((driver) => {
              const headshotUrl = driver.headshot_override || driver.headshot_url;
              return (
                <div
                  key={driver.driver_id}
                  onClick={() => navigate(`/drivers/${driver.driver_id}`)}
                  className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.02]"
                  style={{
                    backgroundColor: `#${team.color_hex}`,
                    aspectRatio: '21 / 9',
                  }}
                >
                  {/* Halftone texture overlay */}
                  <div
                    className="absolute inset-0 pointer-events-none opacity-50"
                    style={{
                      backgroundImage: 'url(/assets/textures/halftone.webp)',
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                      backgroundRepeat: 'no-repeat',
                      mixBlendMode: 'multiply',
                    }}
                  />
                  {/* Dark gradient for text readability */}
                  <div className="absolute inset-0 bg-gradient-to-r from-black/50 to-transparent pointer-events-none" />
                  
                  {/* Driver info */}
                  <div className="absolute inset-0 flex items-center justify-between p-4">
                    <div className="z-10">
                      <div className="text-white/80 text-xs f1-display-regular mb-0.5">
                        #{driver.driver_number}
                      </div>
                      <h3 className="text-white f1-display-bold text-lg lg:text-xl mb-1">{driver.full_name}</h3>
                      <div className="text-white/90 f1-display-regular text-sm">
                        {driver.driver_points} pts
                      </div>
                    </div>
                    
                    {/* Driver headshot */}
                    {headshotUrl && (
                      <div className="absolute right-0 bottom-0 h-full w-1/2 overflow-hidden">
                        <img
                          src={headshotUrl}
                          alt={driver.full_name}
                          className="absolute top-0 left-0 w-full h-auto min-h-full object-cover object-top"
                        />
                      </div>
                    )}
                  </div>
                  
                  {/* Hover effect */}
                  <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity" />
                </div>
              );
            })}
          </div>
        </div>

        {/* Season Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 lg:gap-4">
          <div className="bg-black rounded-corner p-4 lg:p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faTrophy} className="text-yellow-400 text-sm" />
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular">Points</div>
            </div>
            <div className="text-white f1-display-bold text-2xl lg:text-3xl">
              {season_stats.total_points}
            </div>
          </div>

          <div className="bg-black rounded-corner p-4 lg:p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faTrophy} className="text-yellow-400 text-sm" />
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular">Wins</div>
            </div>
            <div className="text-white f1-display-bold text-2xl lg:text-3xl">
              {season_stats.wins}
            </div>
          </div>

          <div className="bg-black rounded-corner p-4 lg:p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faMedal} className="text-orange-400 text-sm" />
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular">Podiums</div>
            </div>
            <div className="text-white f1-display-bold text-2xl lg:text-3xl">
              {season_stats.podiums}
            </div>
          </div>

          <div className="bg-black rounded-corner p-4 lg:p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faFlagCheckered} className="text-green-400 text-sm" />
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular">Points Finishes</div>
            </div>
            <div className="text-white f1-display-bold text-2xl lg:text-3xl">
              {season_stats.points_finishes}
            </div>
          </div>

          <div className="bg-black rounded-corner p-4 lg:p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faStopwatch} className="text-purple-400 text-sm" />
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular">Fastest Laps</div>
            </div>
            <div className="text-white f1-display-bold text-2xl lg:text-3xl">
              {season_stats.fastest_laps}
            </div>
          </div>

          <div className="bg-black rounded-corner p-4 lg:p-6">
            <div className="flex items-center gap-2 mb-2">
              <FontAwesomeIcon icon={faFlagCheckered} className="text-zinc-400 text-sm" />
              <div className="text-zinc-400 text-xs lg:text-sm f1-display-regular">Races</div>
            </div>
            <div className="text-white f1-display-bold text-2xl lg:text-3xl">
              {season_stats.races_entered}
            </div>
          </div>
        </div>

        {/* Two column layout for results and progression */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
          {/* Recent Results */}
          <div className="bg-black rounded-corner p-4 lg:p-6">
            <h2 className="text-white f1-display-bold text-lg lg:text-xl mb-3 lg:mb-4">Recent Results</h2>
            <div className="space-y-2 lg:space-y-3">
              {recent_results.map((result) => (
                <div
                  key={`${result.round_number}-${result.session_type}`}
                  className="flex items-center justify-between p-2 lg:p-3 bg-zinc-950 rounded hover:bg-zinc-900 transition-colors"
                >
                  <div className="flex items-center gap-2 lg:gap-3 flex-1">
                    <div className="text-lg lg:text-2xl">{result.emoji_flag}</div>
                    <div className="flex-1">
                      <div className="text-white f1-display-bold text-xs lg:text-sm">
                        {result.meeting_short_name}
                      </div>
                      <div className="text-zinc-500 text-[10px] lg:text-xs f1-display-regular">
                        {getSessionTypeLabel(result.session_type)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 lg:gap-4">
                    {result.session_points > 0 && (
                      <div className="text-white f1-display-regular text-xs lg:text-sm min-w-10 lg:min-w-12 text-right">
                        +{result.session_points}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Season Progression Chart */}
          <div className="bg-black rounded-corner p-4 lg:p-6">
            <h2 className="text-white f1-display-bold text-lg lg:text-xl mb-3 lg:mb-4">Season Progression</h2>
            <div className="space-y-1 lg:space-y-2">
              {season_progression.map((round) => {
                const maxPoints = Math.max(...season_progression.map(r => r.cumulative_points));
                const widthPercent = maxPoints > 0 ? (round.cumulative_points / maxPoints) * 100 : 0;
                
                return (
                  <div
                    key={round.round_number}
                    className="flex items-center gap-1 lg:gap-2"
                  >
                    <div className="text-zinc-500 text-[10px] lg:text-xs f1-display-regular w-5 lg:w-6">
                      R{round.round_number}
                    </div>
                    <div className="flex-1 relative h-6 lg:h-8">
                      <div 
                        className="absolute inset-y-0 left-0 rounded transition-all"
                        style={{ 
                          width: `${widthPercent}%`,
                          backgroundColor: `#${team.color_hex}`,
                        }}
                      />
                      <div className="absolute inset-0 flex items-center px-1 lg:px-2">
                        <span className="text-white text-[10px] lg:text-xs f1-display-bold z-10">
                          {round.cumulative_points} pts
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        </div>
      </div>
    </PageLayout>
  );
};


