# Frontend -- The Archive UI

Document library, chat interface with The Caretaker, and semantic search -- built with React, Vite, and Tailwind CSS v4.

---

## Prerequisites

- Node 22+

---

## Local Development

```bash
npm install
npm run dev
```

The dev server starts at [http://localhost:5173](http://localhost:5173) and proxies `/api` requests to `http://localhost:8000` (the backend). Make sure the backend is running.

---

## Available Scripts

| Script | Command | Description |
|--------|---------|-------------|
| `dev` | `vite` | Start dev server with HMR |
| `build` | `tsc -b && vite build` | Type-check and produce production build |
| `lint` | `eslint .` | Run ESLint across the project |
| `test` | `vitest run` | Run tests once |
| `test:watch` | `vitest` | Run tests in watch mode |
| `preview` | `vite preview` | Serve the production build locally |

---

## Running Tests

```bash
npm run test
```

Tests use [Vitest](https://vitest.dev/) with [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) and jsdom. Test files live alongside their source code in `__tests__/` directories.

---

## Design System

The UI uses a **Path of Exile 2-inspired** dark fantasy theme, implemented via Tailwind CSS v4 `@theme` tokens in [`src/index.css`](src/index.css).

- **Fonts**: Cinzel (headings), Fira Sans (body)
- **Palette**: Dark backgrounds (`#0c0c14`, `#141420`), gold accents (`#c8aa6e`), crimson highlights (`#8b2500`)
- **Component classes**: `.poe-card`, `.poe-btn-primary`, `.poe-btn-secondary`, `.poe-input`, `.poe-badge`
- **Rarity colors**: Normal (grey), Magic (blue), Rare (yellow), Unique (orange) -- used for visual hierarchy

All theming is CSS-only with no runtime overhead.
