import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { faStopwatch } from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';

interface MeetingData {
  meeting_id: string;
  season: number;
  round_number: number;
  meeting_official_name: string;
  meeting_short_name: string;
  circuit_name: string;
  circuit_short_name: string;
  circuit_id: string;
  location: string;
  country_code: string;
  country_name: string;
  flag_url: string | null;
  date_start: string;
  date_end: string;
}

interface SessionData {
  session_id: string;
  session_type: string;
  start_time: string;
  winner_driver_name: string | null;
}

interface ClassificationData {
  driver_id: string;
  driver_number: number;
  driver_name: string;
  name_acronym: string;
  team_name: string;
  finish_position: number | null;
  duration_ms: number | null;
  gap_to_leader_ms: number | null;
  fastest_lap: boolean | null;
  status: string;
}

interface StandingsData {
  round_number: number;
  cumulative_points: number;
  driver_id?: string;
  driver_name?: string;
  name_acronym?: string;
  team_id?: string;
  team_name?: string;
  display_name?: string;
  color_hex: string;
  logo_url?: string;
}

export const Dashboard = () => {
  const navigate = useNavigate();
  const [latestMeeting, setLatestMeeting] = useState<MeetingData | null>(null);
  const [, setRaceSession] = useState<SessionData | null>(null);
  const [topFinishers, setTopFinishers] = useState<ClassificationData[]>([]);
  const [fastestLapDriver, setFastestLapDriver] = useState<string | null>(null);
  const [coverImageUrl, setCoverImageUrl] = useState<string | null>(null);
  const [driverStandings, setDriverStandings] = useState<StandingsData[]>([]);
  const [constructorStandings, setConstructorStandings] = useState<StandingsData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        // Fetch latest meeting
        const currentYear = new Date().getFullYear();
        const years = [currentYear, currentYear - 1];
        
        let foundMeeting: MeetingData | null = null;
        let foundRaceSession: SessionData | null = null;
        
        for (const year of years) {
          const meetings = await api.meetings(year);
          if (meetings.length > 0) {
            // Get most recent meeting
            const sortedMeetings = meetings.sort((a: MeetingData, b: MeetingData) => 
              new Date(b.date_start).getTime() - new Date(a.date_start).getTime()
            );
            foundMeeting = sortedMeetings[0];
            
            // Fetch sessions for this meeting
            const sessions = await api.meetingSessions(foundMeeting!.meeting_id);
            foundRaceSession = sessions.find((s: SessionData) => s.session_type === 'race') || null;
            
            if (foundRaceSession) break;
          }
        }
        
        setLatestMeeting(foundMeeting);
        setRaceSession(foundRaceSession);

        // Fetch race results if we have a race session
        if (foundRaceSession) {
          const classification = await api.sessionClassification(foundRaceSession.session_id);
          const sortedResults = classification
            .filter((c: ClassificationData) => c.finish_position !== null)
            .sort((a: ClassificationData, b: ClassificationData) => 
              (a.finish_position || 999) - (b.finish_position || 999)
            )
            .slice(0, 3);
          
          setTopFinishers(sortedResults);
          
          // Find fastest lap driver
          const fastestLap = classification.find((c: ClassificationData) => c.fastest_lap);
          if (fastestLap) {
            setFastestLapDriver(fastestLap.driver_name);
          }
        }

        // Fetch cover image for the meeting
        if (foundMeeting) {
          try {
            const images = await api.images({
              circuitId: foundMeeting.circuit_id,
              coverOnly: true,
            });
            if (images && images.length > 0) {
              setCoverImageUrl(`/assets/circuit_image/${images[0].file_path}`);
            }
          } catch {
            // Ignore image errors
          }
        }

        // Fetch championship standings
        const currentSeason = currentYear;
        const [drivers, constructors] = await Promise.all([
          api.standings.drivers(currentSeason),
          api.standings.constructors(currentSeason),
        ]);
        
        setDriverStandings(drivers);
        setConstructorStandings(constructors);
        
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatDuration = (ms: number | null) => {
    if (ms === null || ms === undefined) return '-';
    const totalSeconds = Math.floor(ms / 1000);
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    const milliseconds = ms % 1000;

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
    }
    return `${minutes}:${seconds.toString().padStart(2, '0')}.${milliseconds.toString().padStart(3, '0')}`;
  };

  const formatGap = (gapMs: number | null) => {
    if (gapMs === null || gapMs === undefined) return '-';
    const totalSeconds = gapMs / 1000;
    return `+${totalSeconds.toFixed(3)}s`;
  };

  // Get top 5 drivers with their last 5 rounds
  const getTop5DriversWithSparkline = () => {
    if (!driverStandings.length) return [];
    
    const latestRound = Math.max(...driverStandings.map(d => d.round_number));
    const latestStandings = driverStandings
      .filter(d => d.round_number === latestRound)
      .sort((a, b) => b.cumulative_points - a.cumulative_points)
      .slice(0, 5);
    
    const leaderPoints = latestStandings[0]?.cumulative_points || 0;
    
    return latestStandings.map(driver => {
      const driverHistory = driverStandings
        .filter(d => d.driver_id === driver.driver_id)
        .sort((a, b) => a.round_number - b.round_number)
        .slice(-5);
      
      return {
        ...driver,
        deltaFromLeader: leaderPoints - driver.cumulative_points,
        history: driverHistory,
      };
    });
  };

  // Get top 5 constructors with their last 5 rounds
  const getTop5ConstructorsWithSparkline = () => {
    if (!constructorStandings.length) return [];
    
    const latestRound = Math.max(...constructorStandings.map(d => d.round_number));
    const latestStandings = constructorStandings
      .filter(d => d.round_number === latestRound)
      .sort((a, b) => b.cumulative_points - a.cumulative_points)
      .slice(0, 5);
    
    const leaderPoints = latestStandings[0]?.cumulative_points || 0;
    
    return latestStandings.map(team => {
      const teamHistory = constructorStandings
        .filter(d => d.team_id === team.team_id)
        .sort((a, b) => a.round_number - b.round_number)
        .slice(-5);
      
      return {
        ...team,
        deltaFromLeader: leaderPoints - team.cumulative_points,
        history: teamHistory,
      };
    });
  };

  const MiniSparkline = ({ data, color }: { data: StandingsData[]; color: string }) => {
    if (!data.length) return null;
    
    const points = data.map(d => d.cumulative_points);
    const max = Math.max(...points);
    const min = Math.min(...points);
    const range = max - min || 1;
    
    const width = 60;
    const height = 24;
    const padding = 2;
    
    const normalizedPoints = points.map((p, i) => ({
      x: padding + (i * (width - 2 * padding) / (points.length - 1 || 1)),
      y: height - padding - ((p - min) / range) * (height - 2 * padding),
    }));
    
    const pathData = normalizedPoints
      .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`)
      .join(' ');
    
    return (
      <svg width={width} height={height} className="inline-block">
        <path
          d={pathData}
          fill="none"
          stroke={color}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  };

  if (loading) {
    return (
      <PageLayout pageTitle="Dashboard" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout pageTitle="Dashboard" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <p className="text-f1-red text-lg">{error}</p>
        </div>
      </PageLayout>
    );
  }

  const top5Drivers = getTop5DriversWithSparkline();
  const top5Constructors = getTop5ConstructorsWithSparkline();

  return (
    <PageLayout pageTitle="Dashboard" sidebar={<NavSidebar />}>
      <div className="flex flex-col h-full gap-6">
        {/* Latest Meeting */}
        {latestMeeting && (
          <div>
            <h2 className="text-zinc-400 text-sm f1-display-regular mb-3 uppercase tracking-wide">
              Latest Grand Prix
            </h2>
            <div
              onClick={() => navigate(`/grand-prix/${latestMeeting.meeting_id}`)}
              className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.01] active:scale-[0.99] bg-black"
              style={{ height: '320px' }}
            >
              {/* Cover image */}
              {coverImageUrl ? (
                <div className="absolute inset-0">
                  <img
                    src={coverImageUrl}
                    alt={latestMeeting.circuit_name}
                    className="w-full h-full object-cover"
                  />
                  <div
                    className="absolute inset-0"
                    style={{
                      background: 'linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 50%, rgba(0,0,0,0.3) 80%, rgba(0,0,0,0.1) 100%)',
                    }}
                  />
                </div>
              ) : (
                <div className="absolute inset-0 bg-black" />
              )}

              {/* Content */}
              <div className="relative h-full flex flex-col justify-between p-6">
                {/* Top section */}
                <div className="flex justify-between items-start">
                  <div className="bg-f1-red text-white px-3 py-1 rounded text-sm f1-display-bold">
                    ROUND {latestMeeting.round_number}
                  </div>
                  {latestMeeting.flag_url && (
                    <div className="w-10 h-10 rounded-full overflow-hidden shadow-lg">
                      <img
                        src={latestMeeting.flag_url}
                        alt={latestMeeting.country_name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                </div>

                {/* Bottom section */}
                <div className="z-10">
                  <div className="text-zinc-300 text-sm f1-display-regular mb-2">
                    {formatDate(latestMeeting.date_start)} - {formatDate(latestMeeting.date_end)}
                  </div>
                  <h2
                    className="text-white f1-display-bold text-4xl leading-tight uppercase mb-3"
                    style={{ textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)' }}
                  >
                    {latestMeeting.season} {latestMeeting.meeting_short_name}
                  </h2>

                  {/* Race Results Summary */}
                  {topFinishers.length > 0 && (
                    <div className="bg-black/60 backdrop-blur-sm rounded-lg p-4 space-y-2">
                      {topFinishers.map((finisher, idx) => (
                        <div key={finisher.driver_id} className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="text-white f1-display-bold text-lg w-6">
                              {idx + 1}
                            </div>
                            <div>
                              <div className="text-white f1-display-bold text-base">
                                {finisher.driver_name}
                              </div>
                              <div className="text-zinc-400 text-xs f1-display-regular">
                                {finisher.team_name}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-white f1-display-regular text-sm">
                              {idx === 0 ? formatDuration(finisher.duration_ms) : formatGap(finisher.gap_to_leader_ms)}
                            </div>
                          </div>
                        </div>
                      ))}
                      
                      {/* Fastest Lap Chip */}
                      {fastestLapDriver && (
                        <div className="pt-2 mt-2 border-t border-zinc-700">
                          <div className="inline-flex items-center gap-2 bg-purple-600 text-white px-3 py-1 rounded text-xs f1-display-bold">
                            <FontAwesomeIcon icon={faStopwatch} />
                            <span>{fastestLapDriver}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Hover effect */}
              <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
            </div>
          </div>
        )}

        {/* Championship Snapshots */}
        <div className="grid grid-cols-2 gap-6">
          {/* Driver Championship */}
          <div 
            onClick={() => navigate('/championship')}
            className="bg-black rounded-corner p-6 cursor-pointer hover:bg-zinc-900 transition-colors"
          >
            <h2 className="text-white f1-display-bold text-xl mb-4">
              Driver Championship
            </h2>
            <div className="space-y-3">
              {top5Drivers.map((driver, idx) => (
                <div
                  key={driver.driver_id}
                  className="flex items-center justify-between p-3 rounded"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className="text-zinc-400 f1-display-bold text-sm w-6">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="text-white f1-display-bold text-base">
                        {driver.driver_name}
                      </div>
                      <div className="text-zinc-500 text-xs f1-display-regular">
                        {driver.cumulative_points} pts
                        {driver.deltaFromLeader > 0 && (
                          <span className="ml-2">(-{driver.deltaFromLeader})</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <MiniSparkline 
                    data={driver.history} 
                    color={`#${driver.color_hex}`}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Constructor Championship */}
          <div 
            onClick={() => navigate('/championship')}
            className="bg-black rounded-corner p-6 cursor-pointer hover:bg-zinc-900 transition-colors"
          >
            <h2 className="text-white f1-display-bold text-xl mb-4">
              Constructor Championship
            </h2>
            <div className="space-y-3">
              {top5Constructors.map((team, idx) => (
                <div
                  key={team.team_id}
                  className="flex items-center justify-between p-3 rounded"
                >
                  <div className="flex items-center gap-3 flex-1">
                    <div className="text-zinc-400 f1-display-bold text-sm w-6">
                      {idx + 1}
                    </div>
                    <div className="flex items-center gap-2 flex-1">
                      {team.logo_url && (
                        <img src={team.logo_url} alt={team.team_name} className="w-5 h-5 object-contain" />
                      )}
                      <div className="flex-1">
                        <div className="text-white f1-display-bold text-base">
                          {team.display_name || team.team_name}
                        </div>
                        <div className="text-zinc-500 text-xs f1-display-regular">
                          {team.cumulative_points} pts
                          {team.deltaFromLeader > 0 && (
                            <span className="ml-2">(-{team.deltaFromLeader})</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                  <MiniSparkline 
                    data={team.history} 
                    color={`#${team.color_hex}`}
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};
