import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { FontAwesomeIcon } from '../lib/fontawesome';
import { faChevronUp, faChevronDown } from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';
import { ChampionshipDriverRow, type ChampionshipDriverData } from '../components/ChampionshipDriverRow';
import { ChampionshipTeamRow, type ChampionshipTeamData } from '../components/ChampionshipTeamRow';

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
  team_logo_url?: string | null;
  color_hex?: string;
  headshot_url?: string | null;
  headshot_override?: string | null;
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
  first_name?: string;
  last_name?: string;
  headshot_url?: string | null;
  headshot_override?: string | null;
  team_id?: string;
  team_name?: string;
  display_name?: string;
  color_hex: string;
  logo_url?: string;
}

export const Dashboard = () => {
  const navigate = useNavigate();
  const [latestMeeting, setLatestMeeting] = useState<MeetingData | null>(null);
  const [hasRaceData, setHasRaceData] = useState(false);
  const [topFinishers, setTopFinishers] = useState<ClassificationData[]>([]);
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
        let resultSession: SessionData | null = null;
        let raceDataFound = false;
        
        for (const year of years) {
          const meetings = await api.meetings(year);
          if (meetings.length > 0) {
            // Sort meetings by date (most recent first)
            const sortedMeetings = meetings.sort((a: MeetingData, b: MeetingData) => 
              new Date(b.date_start).getTime() - new Date(a.date_start).getTime()
            );
            
            // Find the most recent meeting with race/sprint data OR a current meeting
            for (const meeting of sortedMeetings) {
              const sessions = await api.meetingSessions(meeting.meeting_id);
              
              // Check for race session first, then sprint
              const raceSession = sessions.find((s: SessionData) => s.session_type === 'race');
              const sprintSession = sessions.find((s: SessionData) => s.session_type === 'sprint');
              
              if (raceSession) {
                foundMeeting = meeting;
                resultSession = raceSession;
                raceDataFound = true;
                break;
              } else if (sprintSession) {
                foundMeeting = meeting;
                resultSession = sprintSession;
                raceDataFound = true;
                break;
              } else {
                // Check if this is a current meeting (within date range)
                const today = new Date();
                const startDate = new Date(meeting.date_start);
                const endDate = new Date(meeting.date_end);
                
                if (today >= startDate && today <= endDate) {
                  foundMeeting = meeting;
                  raceDataFound = false;
                  break;
                }
              }
            }
            
            if (foundMeeting) break;
            
            // If no current meeting, use the most recent one
            if (!foundMeeting && sortedMeetings.length > 0) {
              const recentMeeting = sortedMeetings[0];
              foundMeeting = recentMeeting;
              const sessions = await api.meetingSessions(recentMeeting.meeting_id);
              const raceSession = sessions.find((s: SessionData) => s.session_type === 'race');
              const sprintSession = sessions.find((s: SessionData) => s.session_type === 'sprint');
              resultSession = raceSession || sprintSession || null;
              raceDataFound = !!resultSession;
            }
          }
        }
        
        setLatestMeeting(foundMeeting);
        setHasRaceData(raceDataFound);

        // Fetch race/sprint results if we have a session
        if (resultSession) {
          const classification = await api.sessionClassification(resultSession.session_id);
          const sortedResults = classification
            .filter((c: ClassificationData) => c.finish_position !== null)
            .sort((a: ClassificationData, b: ClassificationData) => 
              (a.finish_position || 999) - (b.finish_position || 999)
            )
            .slice(0, 3); // Top 3 for the simplified view
          
          setTopFinishers(sortedResults);
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

  // Determine if the meeting is "current" (within date range AND no race data)
  const isMeetingCurrent = (meeting: MeetingData | null, hasRace: boolean): boolean => {
    if (!meeting) return false;
    const today = new Date();
    const startDate = new Date(meeting.date_start);
    const endDate = new Date(meeting.date_end);
    return today >= startDate && today <= endDate && !hasRace;
  };

  // Helper component for driver avatar with top-aligned image and outside stroke
  const DashboardDriverAvatar = ({ 
    headshotUrl, 
    driverName, 
    nameAcronym, 
    teamColor 
  }: { 
    headshotUrl: string | null | undefined; 
    driverName: string; 
    nameAcronym?: string;
    teamColor: string;
  }) => {
    const [imageError, setImageError] = useState(false);
    
    return (
      <div className="relative w-12 h-12 rounded-full" style={{ backgroundColor: teamColor }}>
        {/* Halftone overlay */}
        <div
          className="absolute inset-0 pointer-events-none opacity-30 rounded-full"
          style={{
            backgroundImage: 'url(/assets/textures/halftone.webp)',
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            mixBlendMode: 'multiply',
          }}
        />
        
        {/* Driver image - top-aligned */}
        {headshotUrl && !imageError ? (
          <img
            src={headshotUrl}
            alt={driverName}
            className="w-full h-full object-cover object-top rounded-full"
            onError={() => setImageError(true)}
            style={{
              objectPosition: 'center top',
            }}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-white/40 f1-display-bold text-lg">
              {nameAcronym || driverName.charAt(0)}
            </span>
          </div>
        )}
        
        {/* Outside stroke */}
        <div className="absolute -inset-0.5 rounded-full border border-white/20 pointer-events-none" />
      </div>
    );
  };

  // Get top 3 drivers for championship rows
  const getTop3Drivers = (): ChampionshipDriverData[] => {
    if (!driverStandings.length) return [];
    
    const latestRound = Math.max(...driverStandings.map(d => d.round_number));
    const latestStandings = driverStandings
      .filter(d => d.round_number === latestRound)
      .sort((a, b) => b.cumulative_points - a.cumulative_points)
      .slice(0, 3);
    
    return latestStandings.map(driver => ({
      driver_id: driver.driver_id || '',
      driver_name: driver.driver_name || '',
      first_name: driver.first_name,
      last_name: driver.last_name,
      name_acronym: driver.name_acronym,
      headshot_url: driver.headshot_url,
      headshot_override: driver.headshot_override,
      team_id: driver.team_id,
      color_hex: driver.color_hex,
      cumulative_points: driver.cumulative_points,
    }));
  };

  // Get top 3 constructors for championship rows
  const getTop3Constructors = (): ChampionshipTeamData[] => {
    if (!constructorStandings.length) return [];
    
    const latestRound = Math.max(...constructorStandings.map(d => d.round_number));
    const latestStandings = constructorStandings
      .filter(d => d.round_number === latestRound)
      .sort((a, b) => b.cumulative_points - a.cumulative_points)
      .slice(0, 3);
    
    return latestStandings.map(team => ({
      team_id: team.team_id || '',
      team_name: team.team_name || '',
      display_name: team.display_name,
      color_hex: team.color_hex,
      logo_url: team.logo_url,
      cumulative_points: team.cumulative_points,
    }));
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

  const top3Drivers = getTop3Drivers();
  const top3Constructors = getTop3Constructors();
  const currentYear = new Date().getFullYear();

  return (
    <PageLayout pageTitle="Dashboard" sidebar={<NavSidebar />}>
      <div className="flex flex-col h-240">
        {/* Championship Snapshots - 3 equal columns */}
        <div className="grid grid-cols-3 gap-6 flex-1 min-h-0">
          {/* Latest Meeting - Column 1 */}
          {latestMeeting && (
            <div className="flex flex-col h-full">
              <div
                onClick={() => navigate(`/grand-prix/${latestMeeting.meeting_id}`)}
                className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.01] active:scale-[0.99] bg-black flex flex-col"
              >
                {/* Header Section - Circuit image with gradient */}
                <div className="relative flex-shrink-0" style={{ aspectRatio: '16/9' }}>
                  {coverImageUrl ? (
                    <>
                      <img
                        src={coverImageUrl}
                        alt={latestMeeting.circuit_name}
                        className="w-full h-full object-cover"
                      />
                      <div
                        className="absolute inset-0"
                        style={{
                          background: 'linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0) 100%)',
                        }}
                      />
                    </>
                  ) : (
                    <div className="w-full h-full bg-black" />
                  )}

                  {/* Content */}
                  <div className="absolute inset-0 flex flex-col p-6">
                    {/* Badge */}
                    <div className="bg-f1-red text-white px-3 py-1 rounded text-sm f1-display-bold w-fit">
                      {isMeetingCurrent(latestMeeting, hasRaceData) ? 'CURRENT' : 'LATEST'}
                    </div>

                    {/* Spacer */}
                    <div className="flex-1" />

                    {/* Meeting Info - Bottom aligned */}
                    <div className="z-10">
                      {/* Round number - sans serif, aligned with meeting name */}
                      <div 
                        className="text-zinc-400 text-base font-sans font-semibold mb-1" 
                        style={{ 
                          textShadow: '0 2px 4px rgba(0, 0, 0, 0.8)',
                          marginLeft: latestMeeting.flag_url ? '48px' : '0'
                        }}
                      >
                        ROUND {latestMeeting.round_number}
                      </div>
                      
                      {/* Meeting name with flag */}
                      <div className="flex items-center gap-3 mb-2">
                        {latestMeeting.flag_url && (
                          <div className="w-10 h-10 rounded-full overflow-hidden shadow-lg flex-shrink-0">
                            <img
                              src={latestMeeting.flag_url}
                              alt={latestMeeting.country_name}
                              className="w-full h-full object-cover"
                            />
                          </div>
                        )}
                        <h2
                          className="text-white f1-display-bold text-3xl leading-tight"
                          style={{ textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)' }}
                        >
                          {latestMeeting.meeting_short_name}
                        </h2>
                      </div>
                      
                      {/* Dates - sans serif, aligned with meeting name */}
                      <div 
                        className="text-zinc-400 text-base font-sans font-semibold" 
                        style={{ 
                          textShadow: '0 2px 4px rgba(0, 0, 0, 0.8)',
                          marginLeft: latestMeeting.flag_url ? '48px' : '0'
                        }}
                      >
                        {formatDate(latestMeeting.date_start)} – {formatDate(latestMeeting.date_end)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Table Section - Separate black background */}
                {topFinishers.length > 0 && (
                  <div className="bg-black flex-shrink-0 flex flex-col py-2 gap-2">
                    {topFinishers.map((finisher, idx) => {
                      const positionChange = finisher.grid_position && finisher.finish_position
                        ? finisher.grid_position - finisher.finish_position
                        : null;
                      
                      // Ensure color_hex has # prefix
                      const teamColor = finisher.color_hex?.startsWith('#') 
                        ? finisher.color_hex 
                        : `#${finisher.color_hex || '666'}`;
                      
                      const headshotUrl = finisher.headshot_override || finisher.headshot_url;
                      
                      return (
                        <div 
                          key={finisher.driver_id} 
                          className="flex items-center py-3 px-6"
                        >
                          {/* Position - fixed width to align with flag above */}
                          <div className="w-10 flex-shrink-0 flex items-center justify-center">
                            <span className="text-white f1-display-bold text-xl">
                              {idx + 1}
                            </span>
                          </div>
                          
                          {/* Driver Avatar - top-aligned with outside stroke */}
                          <div className="flex-shrink-0 ml-3">
                            <DashboardDriverAvatar
                              headshotUrl={headshotUrl}
                              driverName={finisher.driver_name}
                              nameAcronym={finisher.name_acronym}
                              teamColor={teamColor}
                            />
                          </div>
                          
                          {/* Team Logo + Driver Name */}
                          <div className="flex items-center gap-2 ml-3 flex-1 min-w-0">
                            {finisher.team_logo_url && (
                              <img 
                                src={finisher.team_logo_url} 
                                alt={finisher.team_name}
                                className="w-5 h-5 object-contain flex-shrink-0"
                              />
                            )}
                            <span className="text-white f1-display-regular text-base truncate">
                              {finisher.driver_name.split(' ')[0]}{' '}
                              <span className="f1-display-bold uppercase">
                                {finisher.driver_name.split(' ').slice(1).join(' ')}
                              </span>
                            </span>
                          </div>
                          
                          {/* Position Change - centered in space */}
                          <div className="flex-1 flex items-center justify-center">
                            {positionChange !== null && positionChange !== 0 ? (
                              <div className="flex items-center gap-1">
                                <FontAwesomeIcon 
                                  icon={positionChange > 0 ? faChevronUp : faChevronDown} 
                                  className={`text-xs ${positionChange > 0 ? 'text-green-400' : 'text-red-400'}`}
                                />
                                <span className={`text-sm font-bold ${positionChange > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                  {Math.abs(positionChange)}
                                </span>
                              </div>
                            ) : null}
                          </div>
                          
                          {/* Points Earned - right-aligned */}
                          <div className="flex-shrink-0 w-20 text-right">
                            {finisher.points !== null && finisher.points > 0 && (
                              <span className="text-zinc-500 font-mono font-semibold text-sm">
                                +{finisher.points} pts
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Hover effect */}
                <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
              </div>
            </div>
          )}

          {/* Driver Championship - Column 2 */}
          <div className="flex flex-col h-full">
            <div
              onClick={() => navigate('/championship?tab=drivers')}
              className="relative bg-black rounded-corner cursor-pointer group transition-all hover:scale-[1.01] active:scale-[0.99] flex flex-col p-6 flex-shrink-0"
            >
              <h2 className="text-white f1-display-bold text-xl mb-4 uppercase">
                {currentYear} Driver Standings
              </h2>
              <div className="space-y-3">
                {top3Drivers.map((driver, idx) => (
                  <ChampionshipDriverRow
                    key={driver.driver_id}
                    position={idx + 1}
                    driver={driver}
                  />
                ))}
              </div>
              {/* Hover effect */}
              <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none rounded-corner" />
            </div>
          </div>

          {/* Constructor Championship - Column 3 */}
          <div className="flex flex-col h-full">
            <div
              onClick={() => navigate('/championship?tab=constructors')}
              className="relative bg-black rounded-corner cursor-pointer group transition-all hover:scale-[1.01] active:scale-[0.99] flex flex-col p-6 flex-shrink-0"
            >
              <h2 className="text-white f1-display-bold text-xl mb-4 uppercase">
                {currentYear} Team Standings
              </h2>
              <div className="space-y-3">
                {top3Constructors.map((team, idx) => (
                  <ChampionshipTeamRow
                    key={team.team_id}
                    position={idx + 1}
                    team={team}
                  />
                ))}
              </div>
              {/* Hover effect */}
              <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none rounded-corner" />
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};
