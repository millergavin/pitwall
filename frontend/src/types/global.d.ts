import mapboxgl from 'mapbox-gl';

declare global {
  interface Window {
    map?: mapboxgl.Map;
  }
}

export {};

