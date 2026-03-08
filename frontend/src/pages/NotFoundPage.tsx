import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
      <h1 className="font-heading text-6xl font-bold text-[var(--color-accent-gold-dim)] mb-4">
        404
      </h1>
      <h2 className="font-heading text-xl text-[var(--color-text-heading)] mb-2">
        The path ahead is shrouded in darkness...
      </h2>
      <p className="text-[var(--color-text-secondary)] mb-6">
        The page you're looking for doesn't exist or has been moved.
      </p>
      <Link to="/" className="poe-btn-primary">
        Return to the Archive
      </Link>
    </div>
  );
}
