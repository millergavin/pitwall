# Tailwind CSS Troubleshooting Guide

## Issue: Tailwind Utility Classes Not Applying (Especially Background Colors)

### Symptoms

You'll know you have this issue when:

- Tailwind utilities like `bg-white`, `bg-zinc-700`, etc. don't apply
- The browser DevTools shows `background-color: transparent` instead of the expected color
- Custom colors defined in `@theme` work fine (e.g., `bg-f1-red`), but default Tailwind palette colors don't
- The compiled CSS file shows the utility classes exist (e.g., `.bg-white { background-color: var(--color-white); }`)
- Changing the class name in the browser DevTools manually **does** apply the color (proving the CSS exists)

### Root Cause

**Global CSS resets outside of Tailwind's layer system are interfering with utility classes.**

In Tailwind v4, the framework uses a sophisticated layer system:

```css
@layer properties;
@layer theme, base, components, utilities;
```

When you write CSS **outside** these layers (like raw CSS in `index.css` after the `@import "tailwindcss"`), it can have higher specificity or appear later in the cascade than Tailwind's utilities, causing conflicts.

### The Specific Problem We Had

In `frontend/src/index.css`, there was a global button reset:

```css
/* ❌ BAD: This was outside Tailwind's layer system */
button {
  margin: 0;
  padding: 0;
  border: none;
  background-color: transparent;  /* ← THIS LINE CAUSED THE ISSUE */
  font: inherit;
  color: inherit;
  cursor: pointer;
  /* ... */
}
```

This `background-color: transparent` was:
1. Applied to ALL button elements globally
2. Written outside of Tailwind's `@layer` system
3. In some cases, taking precedence over Tailwind utility classes

Even though Tailwind utilities theoretically have higher specificity, the interaction between layers and source order can cause unexpected behavior.

### How to Diagnose

1. **Check the browser DevTools:**
   - Inspect the element that's not getting the right color
   - Look at the computed styles
   - If you see a value that doesn't match your utility class, check where it's coming from

2. **Look at the compiled CSS:**
   - Open DevTools → Sources → find the `index.css` style tag
   - Search for the utility class (e.g., `.bg-white`)
   - Verify the class exists and has the right value
   - If it exists but isn't applying, you have a specificity/cascade issue

3. **Check for global resets in `index.css`:**
   - Look for any CSS rules written **after** `@import "tailwindcss"`
   - Especially look for element selectors (`button`, `input`, `div`, etc.) that set the same properties as utilities you're trying to use
   - Check if these rules are inside a `@layer` or not

4. **Test with `!important` (diagnostic only):**
   - Try adding a custom class with `!important` in your component's CSS
   - If that works, you definitely have a specificity issue
   - **Don't use this as a solution**, just as a diagnostic tool

### The Solution

**Remove redundant CSS resets that Tailwind already handles.**

Tailwind v4's base layer includes comprehensive resets for all elements, including buttons. You don't need custom resets.

#### Before (❌ Bad):

```css
@import "tailwindcss";

@theme {
  /* your theme config */
}

/* Custom button reset - CONFLICTS WITH TAILWIND */
button {
  margin: 0;
  padding: 0;
  border: none;
  background-color: transparent;
  font: inherit;
  color: inherit;
  cursor: pointer;
  -webkit-appearance: none;
  appearance: none;
}
```

#### After (✅ Good):

```css
@import "tailwindcss";

@theme {
  /* your theme config */
}

/* Button reset is handled by Tailwind's base layer */
```

Or, if you absolutely need custom resets, put them in the base layer:

```css
@import "tailwindcss";

@layer base {
  button {
    /* Only add properties Tailwind doesn't reset */
    /* Avoid setting background-color, color, etc. here */
  }
}
```

### Best Practices to Avoid This

1. **Trust Tailwind's base layer**: Don't add redundant element resets
2. **Use `@layer`**: If you must write custom CSS, put it in the appropriate layer:
   - `@layer base` - for element resets and global styles
   - `@layer components` - for component classes
   - `@layer utilities` - for utility classes
3. **Define custom properties in `@theme`**: Don't override Tailwind's default palette in other ways
4. **Use utility classes, not inline styles**: Inline styles have even higher specificity and can cause similar issues
5. **Check compiled output**: When something doesn't work, inspect the compiled CSS to verify the utility exists

### Testing After a Fix

After removing conflicting CSS, **you MUST restart your dev server**:

```bash
# Stop the server (Ctrl+C or kill the process)
# Then restart:
npm run dev
```

Vite caches CSS output, so changes to `index.css` may not apply until a full restart.

### Common Culprits

Watch out for these patterns in `index.css`:

```css
/* ❌ These can all cause issues if outside @layer */
button { background-color: transparent; }
input { border: none; }
* { margin: 0; padding: 0; }
a { color: inherit; }
div { background: transparent; }
```

If you see these, either remove them (Tailwind handles it) or move them into `@layer base`.

### Related Issues

- Custom colors in `tailwind.config.js` not working → [Ensure you don't have a `tailwind.config.js` in v4, use `@theme` in CSS instead]
- Hover states not working → [Same cause, check for pseudo-selector conflicts]
- Responsive utilities not applying → [Check for media query conflicts outside layers]

### More Resources

- [Tailwind v4 Beta Docs](https://tailwindcss.com/docs/v4-beta)
- [Tailwind v4 Migration Guide](https://tailwindcss.com/docs/v4-beta#migrating-to-v4)
- [CSS Cascade Layers (MDN)](https://developer.mozilla.org/en-US/docs/Web/CSS/@layer)

---

**Last Updated**: December 2025  
**Tailwind Version**: 4.1.17

