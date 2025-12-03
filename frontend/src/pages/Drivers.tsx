import { useState, useEffect } from 'react';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { DriverCard, type DriverCardData } from '../components/DriverCard';
import { api } from '../api/client';

export const Drivers = () => {
  const [season, setSeason] = useState(2025);
  const [drivers, setDrivers] = useState<DriverCardData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDrivers = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.driversRoster(season);
        setDrivers(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load drivers');
      } finally {
        setLoading(false);
      }
    };

    fetchDrivers();
  }, [season]);

  // Generate available seasons (2023-2025 for now)
  const availableSeasons = [2023, 2024, 2025];

  return (
    <PageLayout pageTitle="Drivers" sidebar={<NavSidebar />}>
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
            <p className="text-zinc-600">Loading drivers...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex items-center justify-center h-[400px]">
            <p className="text-f1-red">{error}</p>
          </div>
        )}

        {/* Drivers Grid */}
        {!loading && !error && (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {drivers.map((driver) => (
              <DriverCard
                key={driver.driver_id}
                driver={driver}
                onClick={() => {
                  // TODO: Navigate to driver detail page
                  console.log('Clicked driver:', driver.full_name);
                }}
              />
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && drivers.length === 0 && (
          <div className="flex items-center justify-center h-[400px]">
            <p className="text-zinc-600">No drivers found for {season} season</p>
          </div>
        )}
      </div>
    </PageLayout>
  );
};
