import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { PageLayout } from '../components/PageLayout';
import { NavSidebar } from '../components/NavSidebar';
import { CircuitSidebar, type CircuitData } from '../components/CircuitSidebar';
import { api } from '../api/client';
import { useStore } from '../store/useStore';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

export const Circuits = () => {
  const navigate = useNavigate();
  const [circuits, setCircuits] = useState<CircuitData[]>([]);
  const [selectedCircuit, setSelectedCircuit] = useState<CircuitData | null>(null);
  const [coverImageUrl, setCoverImageUrl] = useState<string | null>(null);
  const [coverImagesMap, setCoverImagesMap] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const { sidebarOpen, sidebarWidth } = useStore();

  // Fetch circuits data and cover images
  useEffect(() => {
    const fetchCircuits = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.circuits();
        // Filter out circuits without valid coordinates
        const validCircuits = data.filter(
          (c: CircuitData) =>
            c.lat != null &&
            c.lon != null &&
            Number.isFinite(Number(c.lat)) &&
            Number.isFinite(Number(c.lon))
        );
        setCircuits(validCircuits);
        
        // Fetch all images and build cover map
        try {
          const allImages = await api.images({});
          const coverMap: Record<string, string> = {};
          
          // Group images by circuit_id, prioritize is_cover = true
          for (const img of allImages) {
            if (img.circuit_id && img.file_path) {
              // Only set if not already set, or if this is a cover image
              if (!coverMap[img.circuit_id] || img.is_cover) {
                coverMap[img.circuit_id] = `/assets/circuit_image/${img.file_path}`;
              }
            }
          }
          
          setCoverImagesMap(coverMap);
        } catch {
          // Ignore image fetch errors
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load circuits');
      } finally {
        setLoading(false);
      }
    };

    fetchCircuits();
  }, []);

  // Set cover image when circuit is selected (use pre-fetched map)
  useEffect(() => {
    if (!selectedCircuit) {
      setCoverImageUrl(null);
      return;
    }

    // Use the pre-fetched cover image from the map
    const cachedCover = coverImagesMap[selectedCircuit.circuit_id];
    if (cachedCover) {
      setCoverImageUrl(cachedCover);
    } else {
      setCoverImageUrl(null);
    }
  }, [selectedCircuit, coverImagesMap]);

  // Handle circuit selection from map
  const handleMapCircuitClick = useCallback((circuitId: string) => {
    const circuit = circuits.find(c => c.circuit_id === circuitId);
    if (circuit) {
      setSelectedCircuit(circuit);
    }
  }, [circuits]);

  // Calculate distance between two lat/lon points (Haversine formula)
  const calculateDistance = (lon1: number, lat1: number, lon2: number, lat2: number): number => {
    const R = 6371; // Earth's radius in km
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c; // Distance in km
  };

  // Fly to circuit on map with distance-based duration
  const flyToCircuit = useCallback((circuit: CircuitData) => {
    if (mapRef.current && circuit.lat && circuit.lon) {
      const currentCenter = mapRef.current.getCenter();
      const targetLon = Number(circuit.lon);
      const targetLat = Number(circuit.lat);
      
      // Calculate distance in km
      const distance = calculateDistance(
        currentCenter.lng,
        currentCenter.lat,
        targetLon,
        targetLat
      );
      
      // Calculate duration based on speed (km per second)
      // Speed: ~500 km/s for smooth animation
      // Clamp between 800ms (min) and 3000ms (max)
      const speed = 500; // km per second
      const calculatedDuration = (distance / speed) * 1000; // Convert to milliseconds
      const duration = Math.max(800, Math.min(3000, calculatedDuration));
      
      mapRef.current.flyTo({
        center: [targetLon, targetLat],
        zoom: 8,
        duration: Math.round(duration),
      });
    }
  }, []);

  // Initialize Mapbox map
  useEffect(() => {
    if (!mapContainerRef.current || !circuits.length || mapRef.current) return;

    const mapboxToken = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN;
    if (!mapboxToken) {
      setError(
        'Mapbox access token not found. Please set VITE_MAPBOX_ACCESS_TOKEN in .env file.'
      );
      return;
    }

    mapboxgl.accessToken = mapboxToken;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [25, 45],
      zoom: 4.1,
      projection: 'globe',
    });

    mapRef.current = map;

    if (typeof window !== 'undefined') {
      window.map = map;
    }

    map.addControl(new mapboxgl.NavigationControl(), 'top-right');

    map.on('style.load', () => {
      try {
        const projectionName = map.getProjection && map.getProjection().name;
        if (projectionName === 'globe') {
          map.setFog({
            range: [-5, 20],
            color: '#000000',
            'horizon-blend': 1,
            'high-color': '#000000',
            'space-color': '#000000',
            'star-intensity': 0.0,
          });
        } else {
          if (map.getLayer('background')) {
            map.setPaintProperty('background', 'background-color', '#000000');
          } else if (!map.getLayer('custom-bg')) {
            map.addLayer({
              id: 'custom-bg',
              type: 'background',
              paint: { 'background-color': '#000000' },
            });
          }
        }
      } catch {
        // Ignore errors
      }

      const features = circuits.map((c) => ({
        type: 'Feature' as const,
        properties: {
          circuit_id: c.circuit_id,
          name: c.circuit_name || c.circuit_short_name,
          short_name: c.circuit_short_name,
          country: c.country_name || c.country_code,
          country_code: c.country_code,
          flag_url: c.flag_url,
        },
        geometry: {
          type: 'Point' as const,
          coordinates: [Number(c.lon), Number(c.lat)],
        },
      }));

      const geojson = { type: 'FeatureCollection' as const, features };

      const existing = map.getSource('circuits');
      if (existing) {
        (existing as mapboxgl.GeoJSONSource).setData(geojson);
      } else {
        map.addSource('circuits', { type: 'geojson', data: geojson });
      }

      const styleLayers = map.getStyle().layers || [];
      const labelLayerId =
        (styleLayers.find(
          (l) => l.type === 'symbol' && 'layout' in l && 'text-field' in (l.layout || {})
        ) || {}).id;

      // Soft glow layer
      map.addLayer({
        id: 'circuits-glow',
        type: 'circle',
        source: 'circuits',
        minzoom: 0,
        maxzoom: 24,
        paint: {
          'circle-radius': 20,
          'circle-color': '#FF1E00',
          'circle-opacity': 0.3,
          'circle-blur': 1.2,
          'circle-emissive-strength': 0.3,
        },
      });

      // Core dot layer
      map.addLayer({
        id: 'circuits-core',
        type: 'circle',
        source: 'circuits',
        minzoom: 0,
        maxzoom: 24,
        paint: {
          'circle-radius': 6,
          'circle-color': '#FF1E00',
          'circle-opacity': 1,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 0,
          'circle-stroke-opacity': 0.3,
          'circle-emissive-strength': 1,
        },
      });

      // Add dynamic labels
      map.addLayer(
        {
          id: 'circuit-labels',
          type: 'symbol',
          source: 'circuits',
          minzoom: 3,
          maxzoom: 24,
          layout: {
            'text-field': ['get', 'name'],
            'text-font': ['Formula1', 'Arial Unicode MS Bold'],
            'text-size': 14,
            'text-transform': 'uppercase',
            'text-letter-spacing': 0.08,
            'text-variable-anchor': ['top', 'bottom', 'left', 'right'],
            'text-radial-offset': 1,
            'text-allow-overlap': false,
            'text-max-width': 14,
          },
          paint: {
            'text-color': '#ffffff',
            'text-halo-color': '#000000',
            'text-halo-width': 1.8,
            'text-halo-blur': 0.8,
            'text-opacity': 1,
          },
        },
        labelLayerId
      );

      map.setPaintProperty('circuits-core', 'circle-color', '#FF1E00');
      map.setPaintProperty('circuits-core', 'circle-stroke-color', '#ffffff');
      map.setPaintProperty('circuits-core', 'circle-emissive-strength', 1);
      map.setPaintProperty('circuits-glow', 'circle-color', '#e10600');
      map.setPaintProperty('circuits-glow', 'circle-opacity', 0.8);
      map.setPaintProperty('circuits-glow', 'circle-emissive-strength', 0.8);

      // Click to select circuit (no popup)
      map.on('click', 'circuits-core', (e) => {
        const f = e.features && e.features[0];
        if (!f || !f.properties) return;
        handleMapCircuitClick(f.properties.circuit_id);
      });

      map.on('mouseenter', 'circuits-core', () => {
        if (map.getCanvas()) {
          map.getCanvas().style.cursor = 'pointer';
        }
      });
      map.on('mouseleave', 'circuits-core', () => {
        if (map.getCanvas()) {
          map.getCanvas().style.cursor = '';
        }
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [circuits, handleMapCircuitClick]);

  // Resize map when sidebar opens/closes
  useEffect(() => {
    if (!mapRef.current) return;

    const handleResize = () => {
      setTimeout(() => {
        mapRef.current?.resize();
      }, 300);
    };

    handleResize();

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [sidebarOpen, sidebarWidth, selectedCircuit]);

  // Handle navigation to circuit details page
  const handleNavigateToCircuitDetails = useCallback((circuitId: string) => {
    navigate(`/circuits/${circuitId}`);
  }, [navigate]);

  return (
    <PageLayout pageTitle="Circuits" sidebar={<NavSidebar />}>
      <div className="flex h-full gap-4">
        {/* Circuit Sidebar */}
        <div className="w-[440px] flex-shrink-0 bg-1 rounded-corner overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-f1-red"></div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-full p-4">
              <p className="text-f1-red text-sm">{error}</p>
            </div>
          ) : (
            <CircuitSidebar
              circuits={circuits}
              selectedCircuit={selectedCircuit}
              coverImageUrl={coverImageUrl}
              coverImagesMap={coverImagesMap}
              onSelectCircuit={setSelectedCircuit}
              onFlyToCircuit={flyToCircuit}
              onNavigateToDetails={handleNavigateToCircuitDetails}
            />
          )}
        </div>

        {/* Map - always render for ref */}
        <div className="flex-1 min-w-0 h-full">
          <div 
            ref={mapContainerRef} 
            className="w-full h-full rounded-corner overflow-hidden"
            style={{ 
              opacity: loading || error ? 0 : 1,
              pointerEvents: loading || error ? 'none' : 'auto',
              transition: 'opacity 0.3s'
            }}
          />
        </div>
      </div>
    </PageLayout>
  );
};
