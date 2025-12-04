# Frontend Development Guide

> **⚠️ Tailwind utility classes not working?** See [TAILWIND_TROUBLESHOOTING.md](./TAILWIND_TROUBLESHOOTING.md)

## Tailwind CSS v4 - Important Patterns

We're using **Tailwind CSS v4** with the `@tailwindcss/postcss` plugin. This version has different syntax than v3 that you need to follow.

### ✅ Correct Patterns

#### 1. Import Syntax
```css
/* ✅ Correct - Tailwind v4 */
@import "tailwindcss";

/* ❌ Wrong - This is v3 syntax */
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### 2. Custom Utility Classes
```css
/* ✅ Correct - Tailwind v4 uses @utility */
@utility bg-overlay-50 {
  background-color: rgb(255 255 255 / 0.05);
}

/* ❌ Wrong - @layer utilities is v3 syntax */
@layer utilities {
  .bg-overlay-50 {
    background-color: rgb(255 255 255 / 0.05);
  }
}
```

#### 3. Custom Colors in Config
Define custom colors in `tailwind.config.js` under `theme.extend.colors`:

```javascript
colors: {
  'overlay': {
    50: 'rgb(255 255 255 / 0.05)',
    100: 'rgb(255 255 255 / 0.10)',
    // ... etc
  },
}
```

**However**: Tailwind v4 may not always generate utility classes from config colors. For reliability, define utilities explicitly using `@utility` in CSS (see pattern #2).

#### 4. Using Custom Utilities in Components
```tsx
// ✅ Correct - Use the class name directly
<div className="bg-overlay-100 text-white">

// ❌ Avoid - Arbitrary values should only be used as a last resort
<div className="bg-[rgb(255_255_255/0.1)]">
```

### Global CSS Resets - Be Careful!

**Avoid global resets that use `color: inherit` or `background: inherit`** - they will override Tailwind utility classes due to CSS specificity.

```css
/* ❌ This breaks Tailwind color utilities */
a {
  color: inherit;
}

/* ✅ This is fine - only removes underlines */
a {
  text-decoration: none;
}
```

### Design System Structure

Our design system is configured in three places:

1. **`tailwind.config.js`**: Color palettes, font families, font sizes, border radius
2. **`src/index.css`**: Custom `@utility` declarations, `@font-face`, semantic type styles
3. **`src/components/`**: Reusable components that consume the design tokens

### Color Palette

#### Background Colors
- `bg-0`: `#0F0F0F` (base page background)
- `bg-1`: `#000000` (container/object backgrounds)

#### Brand Colors
- `f1-red`: `#E10600`
- `f1-bright-red`: `#FF1E00`

#### White Overlay Colors (for surfaces/hover states)
- `bg-overlay-50` through `bg-overlay-950` (5% to 95% white opacity)
- Number indicates opacity percentage (50 = 5%, 100 = 10%, etc.)

#### Zinc Grays
- Standard Tailwind zinc scale: `zinc-50` through `zinc-950`
- `zinc-600` (`#52525b`) is our default muted text color

### Typography

#### Base Font Size
- Base REM: **14px** (not the default 16px)
- This gives a dense, technical feel

#### Font Families
- **Default**: SF (system sans) - `font-sans`
- **Monospace**: SF Mono (system mono) - `font-mono`
- **Display**: Formula 1 Display - `font-f1-display`

#### Semantic Type Styles
- `.button-sm`, `.button-md`, `.button-lg` - Button text styles
- `.page-title` - Formula 1 Display Bold, 1rem, uppercase
- `.f1-display-regular`, `.f1-display-bold`, `.f1-display-black`, `.f1-display-italic`, `.f1-display-wide`

### Component Patterns

#### Buttons
Use the `Button` and `IconButton` components:
- 3 sizes: `sm` (24px), `md` (32px), `lg` (40px)
- 5 variants: `primary`, `secondary`, `text`, `outline`, `destructive`

#### Navigation
Use the `NavMenuItem` component for sidebar navigation:
- Automatically detects active route
- Proper hover and active states
- Consistent padding and styling

### Global Styles

- **Corner radius**: 6px (use `rounded-corner` class or `--corner-radius` variable)
- **Transitions**: Use `transition-colors duration-150` for smooth state changes
- **Button resets**: All default button styles are removed globally
- **Link underlines**: Removed by default (use `no-underline` if needed for specificity)

## Development Tips

1. **Always define design tokens globally** in `tailwind.config.js` or `index.css`
2. **Never use inline styles** for things that should be design tokens
3. **Use semantic class names** (`bg-overlay-100`) instead of arbitrary values when possible
4. **Test in multiple browsers** - Some browsers cache CSS aggressively (hard refresh with Cmd+Shift+R)
5. **Restart dev server** after changing `tailwind.config.js` or global CSS

## Troubleshooting

### "My custom Tailwind classes aren't applying"
1. Check if you're using Tailwind v4 syntax (`@utility` not `@layer`)
2. Restart the dev server (`pkill -f vite && npm run dev`)
3. Clear Vite cache: `rm -rf node_modules/.vite`
4. Hard refresh browser: Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows/Linux)

### "Colors defined in config aren't generating classes"
Tailwind v4 can be quirky with custom color generation. Use `@utility` declarations in `index.css` for reliability.

### "Global CSS is overriding my component styles"
Avoid `color: inherit` and `background: inherit` in global resets. They override utility classes.

