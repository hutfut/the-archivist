import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

interface HeaderProps {
  onUploadClick: () => void;
}

export function Header({ onUploadClick }: HeaderProps) {
  const [searchValue, setSearchValue] = useState("");
  const searchRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleSearch = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const q = searchValue.trim();
      if (q) {
        navigate(`/search?q=${encodeURIComponent(q)}`);
      }
    },
    [searchValue, navigate],
  );

  useEffect(() => {
    function handleKeyDown(e: globalThis.KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <header className="shrink-0 flex items-center gap-4 px-6 py-3 border-b border-[var(--color-border)] bg-[var(--color-bg-secondary)]/80 backdrop-blur-sm z-30">
      <Link to="/" className="flex items-center gap-3 shrink-0 group">
        <div className="w-8 h-8 rounded-md bg-gradient-to-br from-[var(--color-accent-gold)] to-[var(--color-accent-gold-dim)] flex items-center justify-center">
          <svg className="w-5 h-5 text-[var(--color-bg-primary)]" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
          </svg>
        </div>
        <span className="font-heading text-lg font-semibold text-[var(--color-accent-gold)] tracking-wide group-hover:text-[var(--color-accent-gold-bright)] transition-colors hidden sm:inline">
          The Archive
        </span>
      </Link>

      <form onSubmit={handleSearch} className="flex-1 max-w-xl mx-4">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-muted)]" />
          <input
            ref={searchRef}
            type="text"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
              if (e.key === "Escape") {
                searchRef.current?.blur();
              }
            }}
            placeholder="Search documents... (Ctrl+K)"
            className="poe-input w-full pl-9 pr-3 py-2"
          />
        </div>
      </form>

      <nav className="flex items-center gap-2 shrink-0">
        <button
          type="button"
          onClick={onUploadClick}
          className="poe-btn-primary text-xs"
        >
          <span className="hidden sm:inline">Upload</span>
          <UploadIcon className="w-4 h-4 sm:hidden" />
        </button>

        <Link to="/" className="poe-btn-secondary text-xs px-3 py-2">
          Library
        </Link>
      </nav>
    </header>
  );
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 16V4m0 0L8 8m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" />
    </svg>
  );
}
