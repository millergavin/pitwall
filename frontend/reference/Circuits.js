import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { MapPin } from 'lucide-react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const Circuits = () => {
  const [circuits, setCircuits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCircuits = async () => {
      try {
        const response = await axios.get('/api/circuits');
        setCircuits(response.data.circuits);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch circuits');
        setLoading(false);
      }
    };

    fetchCircuits();
  }, []);

  const isReady = !loading && !error;

  // Mapbox setup (run once circuits are loaded)
  useEffect(() => {
    if (!circuits.length) return;
    mapboxgl.accessToken = 'pk.eyJ1IjoibWlsbGVyZ2F2aW4iLCJhIjoiY21mM2Yyenp5MmZyODJtb29najB3bnEybiJ9.WrZJX5yRJadPMWSv643Nsg';
    const map = new mapboxgl.Map({
      container: 'circuits-map',
      style: 'mapbox://styles/millergavin/cmf3f3rud00wb01sg4lrw4gvn',
      center: [25, 45],
      zoom: 4.1,
      projection: 'globe'
    });
    // Expose for debugging in DevTools
    window.map = map;

    map.addControl(new mapboxgl.NavigationControl(), 'top-right');

    // Use style.load so layers are re-added if the style changes
    map.on('style.load', () => {
      // Black space behind globe only; keep globe colors intact
      try {
        const projectionName = map.getProjection && map.getProjection().name;
        if (projectionName === 'globe') {
          map.setFog({
            "range": [-5, 20],
            "color": "#000000",
            "horizon-blend": 1,
            "high-color": "#000000",
            'space-color': '#000000',
            'space-opacity': 1.0,
            'star-intensity': 0.0
          });
        } else {
          // Mercator: ensure background is black
          if (map.getLayer('background')) {
            map.setPaintProperty('background', 'background-color', '#000000');
          } else if (!map.getLayer('custom-bg')) {
            map.addLayer({
              id: 'custom-bg',
              type: 'background',
              paint: { 'background-color': '#000000' }
            });
          }
        }
      } catch {}


      
      const features = circuits
        .filter((c) => Number.isFinite(Number(c.longitude)) && Number.isFinite(Number(c.latitude)))
        .map((c) => ({
          type: 'Feature',
          properties: {
            circuit_id: c.circuit_id,
            name: c.circuit_name || c.circuit_id,
            country: c.country_code || ''
          },
          geometry: {
            type: 'Point',
            coordinates: [Number(c.longitude), Number(c.latitude)]
          }
        }));

      const geojson = { type: 'FeatureCollection', features };

      const existing = map.getSource('circuits');
      if (existing) {
        existing.setData(geojson);
      } else {
        map.addSource('circuits', { type: 'geojson', data: geojson });
      }

      // Determine a label layer to insert below so points are above base map
      const styleLayers = map.getStyle().layers || [];
      const labelLayerId = (styleLayers.find((l) => l.type === 'symbol' && l.layout && l.layout['text-field']) || {}).id;

      // Soft glow layer
      map.addLayer({
        id: 'circuits-glow',
        type: 'circle',
        source: 'circuits',
        minzoom: 0,
        maxzoom: 24,
        paint: {
          'circle-radius': 16,
          'circle-color': '#e10600',
          'circle-opacity': 1,
          'circle-blur': 1,
          'circle-emissive-strength': 1
        }
      });

      // Core dot layer
      map.addLayer({
        id: 'circuits-core',
        type: 'circle',
        source: 'circuits',
        minzoom: 0,
        maxzoom: 24,
        paint: {
          'circle-radius': 4,
          'circle-color': '#e10600',
          'circle-opacity': 1,
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 0,
          'circle-stroke-opacity': 0.3,
          'circle-emissive-strength': 1
        }
      });

      // Add dynamic labels from GeoJSON properties (no Studio upload needed)
      map.addLayer({
        id: 'circuit-labels',
        type: 'symbol',
        source: 'circuits',
        minzoom: 3,
        maxzoom: 24,
        layout: {
          'text-field': ['get', 'name'],
          'text-size': 11,
          'text-variable-anchor': ['top', 'bottom', 'left', 'right'],
          'text-radial-offset': 0.5,
          'text-allow-overlap': false
        },
        paint: {
          'text-color': '#ffffff',
          'text-halo-color': '#000000',
          'text-halo-width': 1
        }
      }, labelLayerId);

      // Re-assert paint properties post-style to avoid style theme overrides
      map.setPaintProperty('circuits-core', 'circle-color', '#FF1E00');
      map.setPaintProperty('circuits-core', 'circle-stroke-color', '#ffffff');
      map.setPaintProperty('circuits-core', 'circle-emissive-strength', 1);
      map.setPaintProperty('circuits-glow', 'circle-color', '#e10600');
      map.setPaintProperty('circuits-glow', 'circle-opacity', 0.8);
      map.setPaintProperty('circuits-glow', 'circle-emissive-strength', 0.8);

      // Ensure we zoom to where the circuits actually are
      // if (features.length > 0) {
      //   const bounds = new mapboxgl.LngLatBounds();
      //   features.forEach((f) => bounds.extend(f.geometry.coordinates));
      //   map.fitBounds(bounds, { padding: 40, maxZoom: 4, duration: 0 });
      // }

      // Popups on click
      map.on('click', 'circuits-core', (e) => {
        const f = e.features && e.features[0];
        if (!f) return;
        new mapboxgl.Popup({ offset: 8, className: 'dark' })
          .setLngLat(e.lngLat)
          .setHTML(`<div style="font-weight:600">${f.properties.name}</div><div style="opacity:.75">${f.properties.country}</div>`)
          .addTo(map);
      });

      map.on('mouseenter', 'circuits-core', () => map.getCanvas().style.cursor = 'pointer');
      map.on('mouseleave', 'circuits-core', () => map.getCanvas().style.cursor = '');
    });

    return () => map.remove();
  }, [circuits]);

  return (
    <div className="w-full h-full">
      {!isReady ? (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-f1-red"></div>
        </div>
      ) : (
        <div id="circuits-map" className="w-full h-full" />
      )}
    </div>
  );
};

export default Circuits;

