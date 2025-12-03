import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
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
  grid_position: number | null;
  finish_position: number | null;
  duration_ms: number | null;
  gap_to_leader_ms: number | null;
  fastest_lap: boolean | null;
  status: string;
  points: number | null;
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
  const [driversRoster, setDriversRoster] = useState<any[]>([]);
  const [teamsRoster, setTeamsRoster] = useState<any[]>([]);
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
            .slice(0, 10); // Top 10 instead of 3
          
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
        const [drivers, constructors, driversRosterData, teamsRosterData] = await Promise.all([
          api.standings.drivers(currentSeason),
          api.standings.constructors(currentSeason),
          api.driversRoster(currentSeason),
          api.teamsRoster(currentSeason),
        ]);
        
        setDriverStandings(drivers);
        setConstructorStandings(constructors);
        setDriversRoster(driversRosterData);
        setTeamsRoster(teamsRosterData);
        
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

  // Get top 10 drivers with their last 5 rounds
  const getTop10DriversWithSparkline = () => {
    if (!driverStandings.length) return [];
    
    const latestRound = Math.max(...driverStandings.map(d => d.round_number));
    const latestStandings = driverStandings
      .filter(d => d.round_number === latestRound)
      .sort((a, b) => b.cumulative_points - a.cumulative_points)
      .slice(0, 10);
    
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

  // Get top 10 constructors with their last 5 rounds
  const getTop10ConstructorsWithSparkline = () => {
    if (!constructorStandings.length) return [];
    
    const latestRound = Math.max(...constructorStandings.map(d => d.round_number));
    const latestStandings = constructorStandings
      .filter(d => d.round_number === latestRound)
      .sort((a, b) => b.cumulative_points - a.cumulative_points)
      .slice(0, 10);
    
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

  const top10Drivers = getTop10DriversWithSparkline();
  const top10Constructors = getTop10ConstructorsWithSparkline();

  return (
    <PageLayout pageTitle="Dashboard" sidebar={<NavSidebar />}>
      <div className="flex flex-col h-full">
        {/* Championship Snapshots - 3 equal columns on desktop, stack on mobile */}
        <motion.div 
          className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6 flex-1 min-h-0 overflow-y-auto lg:overflow-hidden"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: {
                staggerChildren: 0.1,
              },
            },
          }}
        >
          {/* Latest Meeting - Column 1 */}
          {latestMeeting && (
            <motion.div 
              className="flex flex-col min-h-[500px] lg:h-full"
              variants={{
                hidden: { opacity: 0, y: 20 },
                visible: { opacity: 1, y: 0 },
              }}
            >
              <motion.div
                onClick={() => navigate(`/grand-prix/${latestMeeting.meeting_id}`)}
                className="relative overflow-hidden rounded-corner cursor-pointer bg-black h-full flex flex-col"
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
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
                      LATEST GRAND PRIX
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
                  <div className="z-10 flex-1 flex flex-col justify-end overflow-auto">
                    <div className="text-zinc-300 text-sm f1-display-regular mb-2">
                      {formatDate(latestMeeting.date_start)} - {formatDate(latestMeeting.date_end)}
                    </div>
                    <h2
                      className="text-white f1-display-bold text-3xl leading-tight uppercase mb-3"
                      style={{ textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)' }}
                    >
                      {latestMeeting.season} {latestMeeting.meeting_short_name}
                    </h2>

                    {/* Race Results Summary */}
                    {topFinishers.length > 0 && (
                      <div className="bg-black/60 backdrop-blur-sm rounded-lg p-3 lg:p-6 space-y-4 lg:space-y-8 max-h-[80%] overflow-auto">
                        {topFinishers.map((finisher, idx) => {
                          const positionChange = finisher.grid_position && finisher.finish_position
                            ? finisher.grid_position - finisher.finish_position
                            : null;
                          const isFastestLap = finisher.driver_name === fastestLapDriver;
                          
                          return (
                            <div key={finisher.driver_id} className="flex items-center justify-between gap-2 lg:gap-3">
                              <div className="flex items-center gap-2 lg:gap-3 flex-shrink-0 min-w-0" style={{ maxWidth: '50%' }}>
                                <div className="text-white f1-display-bold text-sm lg:text-base w-6 lg:w-8 flex-shrink-0">
                                  {idx + 1}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="text-white f1-display-bold text-xs lg:text-sm truncate">
                                    {finisher.driver_name}
                                  </div>
                                  <div className="text-zinc-400 text-[9px] lg:text-[10px] f1-display-regular truncate">
                                    {finisher.team_name}
                                  </div>
                                </div>
                                {isFastestLap && (
                                  <div className="w-4 h-4 lg:w-5 lg:h-5 bg-purple-600 rounded flex items-center justify-center flex-shrink-0 ml-1">
                                    <FontAwesomeIcon icon={faStopwatch} className="text-white text-[8px] lg:text-[10px]" />
                                  </div>
                                )}
                              </div>
                              <div className="flex items-center gap-2 lg:gap-3 flex-shrink-0">
                                {/* Grid position and change */}
                                {finisher.grid_position && (
                                  <div className="text-center min-w-[40px] lg:min-w-[48px]">
                                    <div className="text-zinc-400 text-[9px] lg:text-[10px] f1-display-regular">
                                      P{finisher.grid_position}
                                    </div>
                                    {positionChange !== null && positionChange !== 0 && (
                                      <div className={`text-[9px] lg:text-[10px] f1-display-bold ${positionChange > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                        {positionChange > 0 ? `+${positionChange}` : positionChange}
                                      </div>
                                    )}
                                  </div>
                                )}
                                {/* Time */}
                                <div className="text-right min-w-16 lg:min-w-24">
                                  <div className="text-white f1-display-regular text-[10px] lg:text-xs">
                                    {idx === 0 ? formatDuration(finisher.duration_ms) : formatGap(finisher.gap_to_leader_ms)}
                                  </div>
                                </div>
                                {/* Points */}
                                {finisher.points !== null && finisher.points > 0 && (
                                  <div className="text-white f1-display-regular text-[10px] lg:text-xs min-w-12 lg:min-w-16 text-right">
                                    +{finisher.points}
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                {/* Hover effect */}
                <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
              </motion.div>
            </motion.div>
          )}

          {/* Driver Championship - Column 2 */}
          <motion.div 
            onClick={() => navigate('/championship')}
            className="bg-black rounded-corner p-6 flex flex-col h-full overflow-hidden cursor-pointer"
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0 },
            }}
            whileHover={{ y: -4 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            <div className="mb-4">
              <h2 className="text-white f1-display-bold text-xl">
                Driver Championship
              </h2>
            </div>
            
            {/* Top 3 Drivers with Images */}
            {top10Drivers.length >= 3 && (
              <div className="mb-4">
                <div className="grid grid-cols-3 gap-2">
                  {top10Drivers.slice(0, 3).map((driver, idx) => {
                    const driverData = driversRoster.find((d: any) => d.driver_id === driver.driver_id);
                    const headshot = driverData?.headshot_override || driverData?.headshot_url;
                    
                    return (
                      <div
                        key={driver.driver_id}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/drivers/${driver.driver_id}`);
                        }}
                        className="relative aspect-[3/4] rounded-corner overflow-hidden cursor-pointer group"
                        style={{ backgroundColor: `#${driver.color_hex}` }}
                      >
                        {headshot && (
                          <img
                            src={headshot}
                            alt={driver.driver_name || ''}
                            className="w-full h-full object-cover object-top group-hover:scale-105 transition-transform duration-300"
                          />
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                        <div className="absolute bottom-0 left-0 right-0 p-2">
                          <div className="text-white f1-display-bold text-2xl leading-none mb-0.5">
                            P{idx + 1}
                          </div>
                          <div className="text-white text-[10px] f1-display-regular leading-tight">
                            {driver.name_acronym}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            <div className="space-y-3 overflow-auto flex-1">
              {top10Drivers.map((driver, idx) => (
                <div
                  key={driver.driver_id}
                  onClick={(e) => {
                    e.stopPropagation();
                    navigate(`/drivers/${driver.driver_id}`);
                  }}
                  className="flex items-center justify-between p-3 rounded cursor-pointer hover:bg-zinc-900 transition-colors"
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
          </motion.div>

          {/* Constructor Championship - Column 3 */}
          <motion.div 
            onClick={() => navigate('/championship')}
            className="bg-black rounded-corner p-6 flex flex-col h-full overflow-hidden cursor-pointer"
            variants={{
              hidden: { opacity: 0, y: 20 },
              visible: { opacity: 1, y: 0 },
            }}
            whileHover={{ y: -4 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            <div className="mb-4">
              <h2 className="text-white f1-display-bold text-xl">
                Constructor Championship
              </h2>
            </div>
            
            {/* Top 3 Teams with Car Images */}
            {top10Constructors.length >= 3 && (
              <div className="mb-4">
                <div className="grid grid-cols-3 gap-2">
                  {top10Constructors.slice(0, 3).map((team, idx) => {
                    const teamData = teamsRoster.find((t: any) => t.team_id === team.team_id);
                    const carImage = teamData?.car_image_url;
                    
                    return (
                      <div
                        key={team.team_id}
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate('/championship');
                        }}
                        className="relative aspect-[3/4] rounded-corner overflow-hidden cursor-pointer group"
                        style={{ backgroundColor: `#${team.color_hex}` }}
                      >
                        {carImage && (
                          <img
                            src={carImage}
                            alt={team.team_name || ''}
                            className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-300"
                          />
                        )}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                        <div className="absolute bottom-0 left-0 right-0 p-2">
                          <div className="text-white f1-display-bold text-2xl leading-none mb-0.5">
                            P{idx + 1}
                          </div>
                          {team.logo_url && (
                            <img src={team.logo_url} alt={team.team_name} className="w-8 h-8 object-contain" />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
            
            <div className="space-y-3 overflow-auto flex-1">
              {top10Constructors.map((team, idx) => (
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
          </motion.div>
        </motion.div>
      </div>
    </PageLayout>
  );
};
