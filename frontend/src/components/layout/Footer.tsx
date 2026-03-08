export function Footer() {
  return (
    <footer className="shrink-0 px-6 py-3 border-t border-[var(--color-border)] bg-[var(--color-bg-secondary)]/50">
      <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)]">
        <span>Exile's Archive &mdash; AI-powered document exploration</span>
        <span>Built with React, FastAPI &amp; LangGraph</span>
      </div>
    </footer>
  );
}
