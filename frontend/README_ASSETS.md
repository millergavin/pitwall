# Assets Organization

Assets are located in `frontend/public/assets/` and are accessible via:

- `/assets/fonts/` - Formula 1 display fonts (for decorative/display type)
- `/assets/logo/` - Pitwall logo variants
- `/assets/track_svgs/` - Circuit track SVG files
- `/assets/*.png` - Other image assets

## Usage in Frontend

Assets can be referenced in React components using:

```tsx
// Images
<img src="/assets/logo/pitwall_logo-white.svg" alt="Pitwall" />

// Fonts (when defining @font-face rules)
@font-face {
  font-family: 'Formula1 Display';
  src: url('/assets/fonts/Formula1-Display-Regular.woff2') format('woff2');
}
```

## Database References

Note: These assets are also referenced in the database with file paths. The paths in the database should match the public asset paths (e.g., `/assets/logo/pitwall_logo-white.svg`).

