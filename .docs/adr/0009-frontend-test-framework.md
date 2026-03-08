# 9. Frontend Test Framework Choice

**Date**: 2026-03-08  
**Status**: Accepted

## Context

The frontend project had no testing infrastructure. We needed to choose a test runner and supporting libraries to enable unit testing of utilities, API modules, hooks, and components.

## Options considered

1. **Jest + React Testing Library** — The long-standing default for React projects. Mature ecosystem with extensive documentation. However, requires separate Babel/ts-jest configuration that duplicates the Vite build pipeline, leading to configuration drift and slower startup.

2. **Vitest + React Testing Library** — Test runner built on Vite's architecture. Shares the same config, transforms, and plugin pipeline as the dev/build toolchain. Native ESM support, TypeScript out of the box, Jest-compatible API for easy migration.

## Decision

Vitest with React Testing Library, `@testing-library/jest-dom` for DOM matchers, and `@testing-library/user-event` for interaction simulation.

Key reasons:
- **Zero config duplication**: Vitest reuses `vite.config.ts` (plugins, resolve aliases, transforms), eliminating the parallel Jest/Babel config that projects typically accumulate.
- **Faster execution**: Vitest uses Vite's on-demand transform pipeline and runs tests concurrently by default.
- **Jest-compatible API**: `describe`, `it`, `expect`, `vi.fn()`, `vi.mock()` — no learning curve for developers familiar with Jest.
- **jsdom environment**: Built-in support via the `environment: 'jsdom'` option, matching what Jest provides.

## Consequences

- All test files use Vitest's `vi` object for mocks/spies rather than Jest's `jest` object.
- `@testing-library/jest-dom/vitest` is imported in the setup file for DOM matcher integration.
- Test configuration lives in the `test` block of `vite.config.ts` rather than a separate config file.
- If the project ever migrates away from Vite, tests would need to migrate to Jest or another runner.
