import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { Button } from '../components/Button';
import { faArrowLeft } from '@fortawesome/free-solid-svg-icons';
import { api } from '../api/client';

interface CircuitData {
  circuit_id: string;
  circuit_name: string | null;
  circuit_short_name: string;
  location: string;
  country_code: string;
  country_name: string;
  flag_url: string;
  lat: number;
  lon: number;
  lap_length_km: number | null;
  race_laps: number | null;
  race_distance_km: number | null;
  sprint_laps: number | null;
  sprint_distance_km: number | null;
  last_year_used: number | null;
  total_turns: number | null;
  circuit_svg: string | null;
  fastest_lap_time_ms: number | null;
  fastest_lap_driver_id: string | null;
  fastest_lap_driver_name: string | null;
  fastest_lap_driver_name_acronym: string | null;
  fastest_lap_year: number | null;
}

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

export const CircuitDetails = () => {
  const { circuitId } = useParams<{ circuitId: string }>();
  const navigate = useNavigate();
  const [circuit, setCircuit] = useState<CircuitData | null>(null);
  const [latestMeeting, setLatestMeeting] = useState<MeetingData | null>(null);
  const [coverImageUrl, setCoverImageUrl] = useState<string | null>(null);
  const [allCircuitImages, setAllCircuitImages] = useState<string[]>([]);
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [meetingCoverUrl, setMeetingCoverUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!circuitId) return;
      
      setLoading(true);
      setError(null);
      
      try {
        // Fetch all circuits and find the one we want
        const circuits = await api.circuits();
        const circuitData = circuits.find((c: CircuitData) => c.circuit_id === circuitId);
        
        if (!circuitData) {
          setError('Circuit not found');
          return;
        }
        
        setCircuit(circuitData);

        // Fetch cover image for the circuit
        try {
          const images = await api.images({
            circuitId: circuitData.circuit_id,
          });
          if (images && images.length > 0) {
            const imageUrls = images.map((img: any) => `/assets/circuit_image/${img.file_path}`);
            setAllCircuitImages(imageUrls);
            setCoverImageUrl(imageUrls[0]);
            setMeetingCoverUrl(imageUrls[0]);
          }
        } catch {
          // Ignore image errors
        }

        // Fetch latest meeting for this circuit
        try {
          // Fetch meetings from the most recent seasons
          const currentYear = new Date().getFullYear();
          const years = [currentYear, currentYear - 1, currentYear - 2];
          
          let foundMeeting: MeetingData | null = null;
          
          for (const year of years) {
            const meetings = await api.meetings(year);
            const circuitMeetings = meetings.filter((m: MeetingData) => m.circuit_id === circuitId);
            if (circuitMeetings.length > 0) {
              // Get the most recent one
              foundMeeting = circuitMeetings[circuitMeetings.length - 1];
              break;
            }
          }
          
          setLatestMeeting(foundMeeting);
        } catch {
          // Ignore meeting fetch errors
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load circuit details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [circuitId]);

  // Cycle through images every 5 seconds
  useEffect(() => {
    if (allCircuitImages.length <= 1) return;

    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % allCircuitImages.length);
    }, 5000);

    return () => clearInterval(interval);
  }, [allCircuitImages.length]);

  // Update cover image when index changes
  useEffect(() => {
    if (allCircuitImages.length > 0) {
      setCoverImageUrl(allCircuitImages[currentImageIndex]);
    }
  }, [currentImageIndex, allCircuitImages]);

  const formatLapTime = (ms: number): string => {
    const totalSeconds = ms / 1000;
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toFixed(3).padStart(6, '0')}`;
  };

  const kmToMiles = (km: number): number => km * 0.621371;

  const getCircuitDisplayName = (circuit: CircuitData): string => {
    if (circuit.circuit_name) {
      return circuit.circuit_name;
    }
    if (circuit.circuit_short_name.toLowerCase().includes('circuit')) {
      return circuit.circuit_short_name;
    }
    return `${circuit.circuit_short_name} Circuit`;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  if (loading) {
    return (
      <PageLayout pageTitle="Circuit Details" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      </PageLayout>
    );
  }

  if (error || !circuit) {
    return (
      <PageLayout pageTitle="Circuit Details" sidebar={<NavSidebar />}>
        <div className="flex items-center justify-center h-full">
          <p className="text-f1-red text-lg">{error || 'Circuit not found'}</p>
        </div>
      </PageLayout>
    );
  }

  return (
    <PageLayout 
      pageTitle={getCircuitDisplayName(circuit)}
      sidebar={<NavSidebar />}
    >
      <div className="flex flex-col gap-6 overflow-auto">
        {/* Back button */}
        <div>
          <Button 
            variant="text" 
            size="sm"
            icon={faArrowLeft}
            onClick={() => navigate('/circuits')}
          >
            Back to Circuits
          </Button>
        </div>

        {/* Hero Section */}
        <div 
          className="relative rounded-corner overflow-hidden"
          style={{ height: '50vh', minHeight: '500px' }}
        >
          {/* Cover image with fade transition */}
          {coverImageUrl ? (
            <img
              key={currentImageIndex}
              src={coverImageUrl}
              alt={circuit.circuit_short_name}
              className="w-full h-full object-cover transition-opacity duration-1000"
              style={{ 
                animation: 'fadeIn 2s ease-in-out',
              }}
            />
          ) : (
            <div className="w-full h-full bg-black" />
          )}
          
          {/* Dark gradient overlay */}
          <div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.6) 40%, rgba(0,0,0,0.3) 70%, rgba(0,0,0,0.0) 100%)',
            }}
          />

          {/* Content */}
          <div className="absolute inset-0 flex flex-col justify-end p-8">
            <div className="flex items-end gap-4 mb-4">
              {circuit.flag_url && (
                <div className="w-12 h-12 rounded-full overflow-hidden shadow-lg flex-shrink-0">
                  <img
                    src={circuit.flag_url}
                    alt={circuit.country_name}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
            </div>
            <h1
              className="text-white f1-display-bold text-6xl leading-tight uppercase mb-2"
              style={{
                textShadow: '0 2px 12px rgba(0, 0, 0, 0.9)',
              }}
            >
              {getCircuitDisplayName(circuit)}
            </h1>
            <h2
              className="text-zinc-300 f1-display-regular text-2xl leading-tight"
              style={{
                textShadow: '0 2px 8px rgba(0, 0, 0, 0.9)',
              }}
            >
              {circuit.location}, {circuit.country_name}
            </h2>
          </div>
        </div>

        {/* Content Grid: Track SVG on left, Stats on right */}
        <div className="grid grid-cols-2 gap-6 pb-6">
          {/* Left: Track Layout SVG */}
          <div className="bg-black rounded-corner p-8 flex items-center justify-center">
            {circuit.circuit_svg ? (
              <img 
                src={circuit.circuit_svg}
                alt={`${circuit.circuit_short_name} track layout`}
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-zinc-600 f1-display-regular">No track layout available</div>
            )}
          </div>

          {/* Right: Latest Meeting + Stats */}
          <div className="flex flex-col gap-6">
            {/* Latest Meeting */}
            {latestMeeting && (
              <div>

                <div
                  onClick={() => navigate(`/grand-prix/${latestMeeting.meeting_id}`)}
                  className="relative overflow-hidden rounded-corner cursor-pointer group transition-transform hover:scale-[1.01] active:scale-[0.99]"
                  style={{
                    aspectRatio: '16 / 6',
                    backgroundColor: '#000',
                  }}
                >
                  {/* Circuit cover image */}
                  {meetingCoverUrl ? (
                    <div className="absolute inset-0">
                      <img
                        src={meetingCoverUrl}
                        alt={circuit.circuit_name || circuit.circuit_short_name}
                        className="w-full h-full object-cover"
                      />
                      {/* Dark gradient overlay */}
                      <div
                        className="absolute inset-0"
                        style={{
                          background: 'linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.6) 40%, rgba(0,0,0,0.3) 70%, rgba(0,0,0,0.1) 100%)',
                        }}
                      />
                    </div>
                  ) : (
                    <div className="absolute inset-0 bg-black" />
                  )}

                  {/* Content */}
                  <div className="relative h-full flex flex-col justify-between p-5">
                    {/* Top section - Latest Grand Prix chip and flag */}
                    <div className="flex justify-between items-start">
                      <div className="bg-f1-red text-white px-2.5 py-1 rounded text-xs f1-display-bold">
                        LATEST GRAND PRIX
                      </div>
                      {latestMeeting.flag_url && (
                        <div className="w-8 h-8 rounded-full overflow-hidden shadow-lg flex-shrink-0">
                          <img
                            src={latestMeeting.flag_url}
                            alt={latestMeeting.country_name}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      )}
                    </div>

                    {/* Bottom section - Meeting info */}
                    <div className="z-10">
                      {/* Date range */}
                      <div className="text-zinc-300 text-xs f1-display-regular mb-1.5">
                        {formatDate(latestMeeting.date_start)} - {formatDate(latestMeeting.date_end)}
                      </div>
                      
                      {/* Meeting name with season */}
                      <h2
                        className="text-white f1-display-bold text-xl leading-tight uppercase"
                        style={{
                          textShadow: '0 2px 8px rgba(0, 0, 0, 0.8)',
                        }}
                      >
                        {latestMeeting.season} {latestMeeting.meeting_short_name}
                      </h2>
                    </div>
                  </div>

                  {/* Hover effect overlay */}
                  <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-5 transition-opacity pointer-events-none" />
                </div>
              </div>
            )}

            {/* Circuit Stats Grid - More compact */}
            <div className="grid grid-cols-2 gap-4">
              {/* Circuit Length */}
              {circuit.lap_length_km && (
                <div className="bg-black rounded-corner p-4">
                  <div className="text-zinc-400 text-xs f1-display-regular mb-1.5 uppercase tracking-wide">
                    Circuit Length
                  </div>
                  <div className="text-white f1-display-bold text-2xl mb-0.5">
                    {circuit.lap_length_km.toFixed(3)} <span className="text-lg text-zinc-400">km</span>
                  </div>
                  <div className="text-zinc-500 f1-display-regular text-base">
                    {kmToMiles(circuit.lap_length_km).toFixed(3)} <span className="text-xs">mi</span>
                  </div>
                </div>
              )}

              {/* Race Laps */}
              {circuit.race_laps && (
                <div className="bg-black rounded-corner p-4">
                  <div className="text-zinc-400 text-xs f1-display-regular mb-1.5 uppercase tracking-wide">
                    Race Laps
                  </div>
                  <div className="text-white f1-display-bold text-2xl">
                    {circuit.race_laps}
                  </div>
                  {circuit.race_distance_km && (
                    <div className="text-zinc-500 f1-display-regular text-base mt-0.5">
                      {circuit.race_distance_km.toFixed(1)} km
                    </div>
                  )}
                </div>
              )}

              {/* Total Turns */}
              {circuit.total_turns && (
                <div className="bg-black rounded-corner p-4">
                  <div className="text-zinc-400 text-xs f1-display-regular mb-1.5 uppercase tracking-wide">
                    Total Turns
                  </div>
                  <div className="text-white f1-display-bold text-2xl">
                    {circuit.total_turns}
                  </div>
                </div>
              )}

              {/* Last Year Used */}
              {circuit.last_year_used && (
                <div className="bg-black rounded-corner p-4">
                  <div className="text-zinc-400 text-xs f1-display-regular mb-1.5 uppercase tracking-wide">
                    Last Used
                  </div>
                  <div className="text-white f1-display-bold text-2xl">
                    {circuit.last_year_used}
                  </div>
                </div>
              )}
            </div>

            {/* Lap Record - Full width */}
            {circuit.fastest_lap_time_ms && (
              <div className="bg-black rounded-corner p-5">
                <div className="text-zinc-400 text-xs f1-display-regular mb-2 uppercase tracking-wide">
                  Lap Record
                </div>
                <div className="flex items-end gap-4">
                  <div className="text-white f1-display-bold text-5xl leading-none">
                    {formatLapTime(circuit.fastest_lap_time_ms)}
                  </div>
                  {circuit.fastest_lap_driver_name && circuit.fastest_lap_year && (
                    <div className="pb-1">
                      <div className="text-white f1-display-bold text-xl">
                        {circuit.fastest_lap_driver_name}
                      </div>
                      <div className="text-zinc-400 f1-display-regular text-base">
                        {circuit.fastest_lap_year}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

