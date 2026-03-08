import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { type SearchResult, searchDocuments } from "../api/search";
import { useLayoutContext } from "../hooks/useLayoutContext";
import { filenameToTitle, toSlug } from "../lib/utils";

type FetchState =
  | { status: "loading" }
  | { status: "success"; results: SearchResult[]; total: number }
  | { status: "error"; message: string };

export function SearchPage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const { openUpload } = useLayoutContext();

  if (!query.trim()) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <h2 className="font-heading text-xl text-[var(--color-text-heading)] mb-2">Search</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Enter a search query using the search bar above.
        </p>
      </div>
    );
  }

  return <SearchResults key={query} query={query} onUpload={openUpload} />;
}

function SearchResults({
  query,
  onUpload,
}: {
  query: string;
  onUpload: () => void;
}) {
  const [state, setState] = useState<FetchState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    searchDocuments(query)
      .then((data) => {
        if (cancelled) return;
        setState({ status: "success", results: data.results, total: data.total });
      })
      .catch((err) => {
        if (cancelled) return;
        setState({
          status: "error",
          message: err instanceof Error ? err.message : "Search failed",
        });
      });

    return () => { cancelled = true; };
  }, [query]);

  if (state.status === "loading") return <SearchSkeleton />;

  if (state.status === "error") {
    return (
      <div className="max-w-3xl mx-auto px-6 py-8 text-center">
        <p className="text-red-400">{state.message}</p>
      </div>
    );
  }

  const { results, total } = state;

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="mb-6">
        <h2 className="font-heading text-lg text-[var(--color-text-heading)]">
          {total > 0
            ? `${total} result${total !== 1 ? "s" : ""} for "${query}"`
            : `No results for "${query}"`}
        </h2>
      </div>

      {results.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[var(--color-text-secondary)] mb-4">
            No documents matched your search. Try different keywords or upload more documents.
          </p>
          <button type="button" onClick={onUpload} className="poe-btn-primary text-sm">
            Upload Documents
          </button>
        </div>
      ) : (
        <ul className="space-y-3">
          {results.map((result, i) => (
            <SearchResultCard key={`${result.document_id}-${i}`} result={result} />
          ))}
        </ul>
      )}
    </div>
  );
}

function SearchResultCard({ result }: { result: SearchResult }) {
  const title = result.title || filenameToTitle(result.filename);
  const slug = toSlug(result.document_id, result.filename);
  const anchor = result.section_heading
    ? `#${result.section_heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`
    : "";

  return (
    <li>
      <Link to={`/doc/${slug}${anchor}`} className="poe-card block p-4 hover:border-[var(--color-accent-gold-dim)]">
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3 className="text-sm font-heading font-semibold text-[var(--color-text-heading)]">
            {title}
          </h3>
          <span className="poe-badge text-[var(--color-accent-gold)] border-[var(--color-accent-gold-dim)] bg-[var(--color-accent-gold)]/5 shrink-0">
            {(result.score * 100).toFixed(0)}%
          </span>
        </div>
        {result.section_heading && (
          <p className="text-xs text-[var(--color-accent-gold-dim)] mb-1">{result.section_heading}</p>
        )}
        <p className="text-xs text-[var(--color-text-secondary)] line-clamp-2">{result.snippet}</p>
      </Link>
    </li>
  );
}

function SearchSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="poe-skeleton h-6 w-48 mb-6" />
      <div className="space-y-3">
        {Array.from({ length: 5 }, (_, i) => (
          <div key={i} className="poe-card p-4 space-y-2">
            <div className="poe-skeleton h-5 w-1/2" />
            <div className="poe-skeleton h-3 w-3/4" />
            <div className="poe-skeleton h-3 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}
