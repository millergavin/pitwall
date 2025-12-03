/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'bg-0': '#0F0F0F',
        'bg-1': '#000000',
        'f1-red': '#E10600',
        'f1-bright-red': '#FF1E00',
        // Zinc colors for borders and backgrounds
        'zinc': {
          50: '#fafafa',
          100: '#f4f4f5',
          200: '#e4e4e7',
          300: '#d4d4d8',
          400: '#a1a1aa',
          500: '#71717a',
          600: '#52525b',
          700: '#3f3f46',
          800: '#27272a',
          900: '#18181b',
          950: '#09090b',
        },
        // White overlay colors - using standard Tailwind scale
        'overlay': {
          50: 'rgb(255 255 255 / 0.05)',   // 5% opacity
          100: 'rgb(255 255 255 / 0.10)',  // 10% opacity
          200: 'rgb(255 255 255 / 0.20)',  // 20% opacity
          300: 'rgb(255 255 255 / 0.30)',  // 30% opacity
          400: 'rgb(255 255 255 / 0.40)',  // 40% opacity
          500: 'rgb(255 255 255 / 0.50)',  // 50% opacity
          600: 'rgb(255 255 255 / 0.60)',  // 60% opacity
          700: 'rgb(255 255 255 / 0.70)',  // 70% opacity
          800: 'rgb(255 255 255 / 0.80)',  // 80% opacity
          900: 'rgb(255 255 255 / 0.90)',  // 90% opacity
          950: 'rgb(255 255 255 / 0.95)',  // 95% opacity
        },
      },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"SF Pro Display"',
          '"SF Pro Text"',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
        mono: [
          '"SF Mono"',
          'Monaco',
          'Inconsolata',
          '"Roboto Mono"',
          '"Source Code Pro"',
          'Menlo',
          'Consolas',
          '"DejaVu Sans Mono"',
          'monospace',
        ],
        'f1-display': [
          '"Formula1 Display"',
          'sans-serif',
        ],
        'f1-display-regular': [
          '"Formula1 Display Regular"',
          'sans-serif',
        ],
        'f1-display-bold': [
          '"Formula1 Display Bold"',
          'sans-serif',
        ],
      },
      fontSize: {
        // Base font size is 14px, so these are relative to that
        'xs': ['0.75rem', { lineHeight: '1rem' }],      // 10.5px
        'sm': ['0.875rem', { lineHeight: '1.25rem' }],  // 12.25px
        'base': ['1rem', { lineHeight: '1.5rem' }],     // 14px
        'lg': ['1.125rem', { lineHeight: '1.75rem' }], // 15.75px
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],  // 17.5px
        '2xl': ['1.5rem', { lineHeight: '2rem' }],     // 21px
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }], // 26.25px
        '4xl': ['2.25rem', { lineHeight: '2.5rem' }],  // 31.5px
      },
      borderRadius: {
        'corner': 'var(--corner-radius, 6px)',
      },
    },
  },
  plugins: [],
}

