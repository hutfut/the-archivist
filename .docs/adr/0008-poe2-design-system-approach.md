# ADR-0008: PoE2 Design System Approach

**Date:** 2026-03-08
**Status:** Accepted

## Context

The frontend needs a heavy PoE2-inspired visual theme: dark backgrounds, gold accents, ornate borders, and an immersive aesthetic. The theme is a visual skin over a generic document management app -- it must not assume PoE2 content.

## Options Considered

1. **Tailwind `@theme` custom properties + utility classes** -- Define design tokens as CSS custom properties via Tailwind v4's `@theme` directive. Components use standard Tailwind utilities that reference these tokens.
2. **CSS-in-JS (styled-components / Emotion)** -- Runtime styling with theme context. Adds bundle size and runtime overhead for no benefit over Tailwind.
3. **CSS Modules with a theme file** -- Scoped styles per component. Works but loses Tailwind's utility-first productivity.

## Decision

Use **Tailwind v4 `@theme` tokens** for the design system:

- **Colors:** Dark primary (`#0c0c14`), secondary (`#141420`), gold accent (`#c8aa6e`), crimson (`#8b2500`), muted text tones
- **Fonts:** Cinzel (Google Fonts) for headings, Fira Sans for body text
- **Decorative elements:** CSS-only -- gradients, box shadows with amber tint, 1px gold borders, `::before`/`::after` pseudo-element flourishes. No copyrighted game assets.
- **Background texture:** Subtle repeating noise pattern via CSS radial-gradient

## Consequences

- **Positive:** Zero runtime cost -- all theming is CSS custom properties resolved at build time
- **Positive:** Consistent design language across all components via shared tokens
- **Positive:** No copyright concerns -- purely CSS-based aesthetic
- **Negative:** Google Fonts add ~50KB of font files (acceptable, loaded async)
- **Risk:** Heavy theming could make the UI feel slow if overused; keep decorative elements subtle
