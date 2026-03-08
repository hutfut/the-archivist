import { useCallback, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useLayoutContext } from "../hooks/useLayoutContext";
import { useRecentlyViewed } from "../hooks/useRecentlyViewed";
import { fileTypeBadge, filenameToTitle, formatDate, formatFileSize, toSlug } from "../lib/utils";
import { ConfirmDialog } from "../components/ConfirmDialog";

type SortKey = "newest" | "alpha" | "chunks";

export function HomePage() {
  const { documents: docs, openUpload } = useLayoutContext();
  const { documents, loading, remove } = docs;
  const { items: recentlyViewed } = useRecentlyViewed();
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<SortKey>("newest");

  const filtered = useMemo(() => {
    let result = documents;
    if (filter.trim()) {
      const lower = filter.toLowerCase();
      result = result.filter(
        (d) =>
          d.filename.toLowerCase().includes(lower) ||
          filenameToTitle(d.filename).toLowerCase().includes(lower),
      );
    }
    const sorted = [...result];
    switch (sort) {
      case "alpha":
        sorted.sort((a, b) =>
          filenameToTitle(a.filename).localeCompare(filenameToTitle(b.filename)),
        );
        break;
      case "chunks":
        sorted.sort((a, b) => b.chunk_count - a.chunk_count);
        break;
      case "newest":
      default:
        sorted.sort(
          (a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
        );
    }
    return sorted;
  }, [documents, filter, sort]);

  if (loading) {
    return <LoadingSkeleton />;
  }

  if (documents.length === 0) {
    return <EmptyState onUpload={openUpload} />;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-heading font-semibold text-[var(--color-text-heading)] mb-2">
          Your Library
        </h1>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {documents.length} document{documents.length !== 1 ? "s" : ""} uploaded
        </p>
      </div>

      {recentlyViewed.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-heading font-semibold text-[var(--color-accent-gold-dim)] uppercase tracking-wider mb-3">
            Recently Viewed
          </h2>
          <div className="flex gap-2 overflow-x-auto pb-2">
            {recentlyViewed.slice(0, 5).map((item) => (
              <Link
                key={item.id}
                to={`/doc/${toSlug(item.id, item.filename)}`}
                className="poe-card px-3 py-2 shrink-0 max-w-[180px] hover:border-[var(--color-accent-gold-dim)] transition-colors"
              >
                <p className="text-xs font-medium text-[var(--color-text-heading)] truncate">{item.title}</p>
                <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{formatDate(item.viewedAt)}</p>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 mb-6">
        <input
          type="text"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter documents..."
          className="poe-input flex-1"
        />
        <div className="flex items-center gap-2">
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            className="poe-input text-xs py-2"
          >
            <option value="newest">Newest first</option>
            <option value="alpha">Alphabetical</option>
            <option value="chunks">Most sections</option>
          </select>
          <button type="button" onClick={openUpload} className="poe-btn-primary text-xs whitespace-nowrap">
            Upload
          </button>
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="text-center py-12 text-[var(--color-text-muted)]">
          <p className="text-sm">No documents match "{filter}"</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((doc) => (
            <DocumentCard key={doc.id} document={doc} onDelete={remove} />
          ))}
        </div>
      )}
    </div>
  );
}

interface DocumentCardProps {
  document: {
    id: string;
    filename: string;
    content_type: string;
    file_size: number;
    chunk_count: number;
    created_at: string;
  };
  onDelete: (id: string) => Promise<void>;
}

function DocumentCard({ document: doc, onDelete }: DocumentCardProps) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const badge = fileTypeBadge(doc.content_type);
  const title = filenameToTitle(doc.filename);
  const slug = toSlug(doc.id, doc.filename);

  const handleDelete = useCallback(async () => {
    await onDelete(doc.id);
    setConfirmDelete(false);
  }, [doc.id, onDelete]);

  return (
    <>
      <div className="poe-card p-4 flex flex-col gap-3 group">
        <div className="flex items-start justify-between gap-2">
          <Link to={`/doc/${slug}`} className="flex-1 min-w-0">
            <h3 className="font-heading text-sm font-semibold text-[var(--color-text-heading)] truncate group-hover:text-[var(--color-accent-gold)] transition-colors">
              {title}
            </h3>
          </Link>
          <span className={`poe-badge ${badge.className} shrink-0`}>{badge.label}</span>
        </div>

        <Link to={`/doc/${slug}`} className="flex-1">
          <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-[var(--color-text-secondary)]">
            <span>{doc.chunk_count} section{doc.chunk_count !== 1 ? "s" : ""}</span>
            <span>{formatFileSize(doc.file_size)}</span>
            <span>{formatDate(doc.created_at)}</span>
          </div>
        </Link>

        <div className="flex items-center justify-between pt-2 border-t border-[var(--color-border)]">
          <Link
            to={`/doc/${slug}`}
            className="text-xs text-[var(--color-accent-gold-dim)] hover:text-[var(--color-accent-gold)] transition-colors"
          >
            Read &rarr;
          </Link>
          <button
            type="button"
            onClick={() => setConfirmDelete(true)}
            className="text-xs text-[var(--color-text-muted)] hover:text-red-400 transition-colors cursor-pointer"
          >
            Delete
          </button>
        </div>
      </div>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete document"
        message={`Delete "${doc.filename}"? This will remove the document and all its processed data. This cannot be undone.`}
        confirmLabel="Delete"
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(false)}
      />
    </>
  );
}

function EmptyState({ onUpload }: { onUpload: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-6 text-center">
      <div className="max-w-md mx-auto">
        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-[var(--color-accent-gold)]/20 to-[var(--color-accent-crimson)]/10 border border-[var(--color-border-gold)] flex items-center justify-center">
          <svg className="w-10 h-10 text-[var(--color-accent-gold)]" fill="currentColor" viewBox="0 0 20 20" aria-hidden="true">
            <path d="M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z" />
          </svg>
        </div>

        <h1 className="font-heading text-2xl font-semibold text-[var(--color-accent-gold)] mb-3">
          Welcome to Exile's Archive
        </h1>
        <p className="text-[var(--color-text-secondary)] mb-8 leading-relaxed">
          Upload your documents to get started. Ask questions, search content,
          and explore connections between your files with AI-powered assistance.
        </p>

        <button type="button" onClick={onUpload} className="poe-btn-primary text-base px-8 py-3 mb-6">
          Upload Your First Document
        </button>

        <div className="flex items-center justify-center gap-4 text-xs text-[var(--color-text-muted)]">
          <span className="poe-badge poe-badge-pdf">PDF</span>
          <span className="poe-badge poe-badge-txt">TXT</span>
          <span className="poe-badge poe-badge-md">MD</span>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <div className="poe-skeleton h-8 w-48 mb-2" />
      <div className="poe-skeleton h-4 w-32 mb-8" />
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }, (_, i) => (
          <div key={i} className="poe-card p-4 space-y-3">
            <div className="poe-skeleton h-5 w-3/4" />
            <div className="poe-skeleton h-3 w-1/2" />
            <div className="poe-skeleton h-3 w-2/3" />
          </div>
        ))}
      </div>
    </div>
  );
}
