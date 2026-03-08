import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Components } from "react-markdown";
import {
  type DocumentContent,
  type RelatedDocument,
  fetchDocumentContent,
  fetchRelatedDocuments,
} from "../api/content";
import { useLayoutContext } from "../hooks/useLayoutContext";
import { useRecentlyViewed } from "../hooks/useRecentlyViewed";
import { filenameToTitle, fromSlug, toSlug, formatFileSize, formatDate, fileTypeBadge } from "../lib/utils";
import { extractHeadings, extractText, type Heading } from "../lib/markdown";

export function DocumentPage() {
  const { slug } = useParams<{ slug: string }>();
  const documentId = slug ? fromSlug(slug) : "";

  if (!documentId) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <h2 className="font-heading text-xl text-[var(--color-accent-gold)] mb-2">Invalid Document</h2>
        <Link to="/" className="poe-btn-secondary text-sm">Back to Library</Link>
      </div>
    );
  }

  return <DocumentView key={documentId} documentId={documentId} />;
}

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; doc: DocumentContent; related: RelatedDocument[] };

function DocumentView({ documentId }: { documentId: string }) {
  const { openChat } = useLayoutContext();
  const { addItem } = useRecentlyViewed();
  const [state, setState] = useState<PageState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetchDocumentContent(documentId),
      fetchRelatedDocuments(documentId).catch((): { documents: RelatedDocument[] } => ({ documents: [] })),
    ]).then(([content, rel]) => {
      if (cancelled) return;
      setState({ status: "ready", doc: content, related: rel.documents });
      addItem({
        id: content.id,
        filename: content.filename,
        title: content.title || filenameToTitle(content.filename),
      });
    }).catch((err) => {
      if (cancelled) return;
      setState({
        status: "error",
        message: err instanceof Error ? err.message : "Failed to load document",
      });
    });

    return () => { cancelled = true; };
  }, [documentId, addItem]);

  if (state.status === "loading") return <DocumentSkeleton />;

  if (state.status === "error") {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <h2 className="font-heading text-xl text-[var(--color-accent-gold)] mb-2">
          Document Not Found
        </h2>
        <p className="text-[var(--color-text-secondary)] mb-4">{state.message}</p>
        <Link to="/" className="poe-btn-secondary text-sm">Back to Library</Link>
      </div>
    );
  }

  const { doc, related } = state;
  const title = doc.title || filenameToTitle(doc.filename);
  const isMarkdown = doc.content_type === "text/markdown";
  const headings = isMarkdown ? extractHeadings(doc.content) : [];
  const badge = fileTypeBadge(doc.content_type);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      <nav className="flex items-center gap-2 text-xs text-[var(--color-text-muted)] mb-4">
        <Link to="/" className="hover:text-[var(--color-accent-gold)] transition-colors">Home</Link>
        <span>/</span>
        <span className="text-[var(--color-text-secondary)] truncate">{title}</span>
      </nav>

      <div className="flex gap-6">
        {headings.length > 2 && (
          <aside className="hidden lg:block w-56 shrink-0">
            <TableOfContents headings={headings} />
          </aside>
        )}

        <article className="flex-1 min-w-0">
          <div className="poe-card p-6 sm:p-8">
            <div className="mb-6 pb-4 border-b border-[var(--color-border)]">
              <div className="flex items-start justify-between gap-3 mb-2">
                <h1 className="font-heading text-2xl font-semibold text-[var(--color-text-heading)]">
                  {title}
                </h1>
                <span className={`poe-badge ${badge.className} shrink-0 mt-1`}>{badge.label}</span>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--color-text-muted)]">
                <span>{doc.filename}</span>
                <span>{formatFileSize(doc.file_size)}</span>
                <span>{doc.chunk_count} sections</span>
                <span>{formatDate(doc.created_at)}</span>
              </div>
            </div>

            {isMarkdown ? (
              <MarkdownRenderer content={doc.content} />
            ) : (
              <pre className="text-sm text-[var(--color-text-primary)] whitespace-pre-wrap font-body leading-relaxed overflow-x-auto">
                {doc.content}
              </pre>
            )}
          </div>

          <div className="mt-4 flex justify-center">
            <button
              type="button"
              onClick={() => openChat(`Tell me about ${title}`)}
              className="poe-btn-secondary text-sm flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zM3.75 20.25V4.125C3.75 3.504 4.254 3 4.875 3h14.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125H7.875L3.75 20.25z" />
              </svg>
              Ask about this document
            </button>
          </div>
        </article>

        {related.length > 0 && (
          <aside className="hidden xl:block w-56 shrink-0">
            <RelatedPanel documents={related} />
          </aside>
        )}
      </div>
    </div>
  );
}

function TableOfContents({ headings }: { headings: Heading[] }) {
  const [activeId, setActiveId] = useState<string>("");
  const observerRef = useRef<IntersectionObserver | null>(null);

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id);
          }
        }
      },
      { rootMargin: "-80px 0px -60% 0px", threshold: 0.1 },
    );

    for (const h of headings) {
      const el = document.getElementById(h.id);
      if (el) observerRef.current.observe(el);
    }

    return () => observerRef.current?.disconnect();
  }, [headings]);

  return (
    <nav className="sticky top-6">
      <h4 className="font-heading text-xs font-semibold text-[var(--color-accent-gold-dim)] uppercase tracking-wider mb-3">
        Contents
      </h4>
      <ul className="space-y-1 text-xs">
        {headings.map((h) => (
          <li key={h.id} style={{ paddingLeft: `${(h.level - 2) * 12}px` }}>
            <a
              href={`#${h.id}`}
              className={`block py-1 transition-colors ${
                activeId === h.id
                  ? "text-[var(--color-accent-gold)] font-medium"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
              }`}
            >
              {h.text}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function MarkdownRenderer({ content }: { content: string }) {
  const components: Components = useMemo(
    () => ({
      h2: ({ children, ...props }) => {
        const text = extractText(children);
        const id = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        return <h2 id={id} className="font-heading text-xl font-semibold text-[var(--color-text-heading)] mt-8 mb-3 scroll-mt-20" {...props}>{children}</h2>;
      },
      h3: ({ children, ...props }) => {
        const text = extractText(children);
        const id = text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
        return <h3 id={id} className="font-heading text-lg font-semibold text-[var(--color-text-heading)] mt-6 mb-2 scroll-mt-20" {...props}>{children}</h3>;
      },
      p: ({ children, ...props }) => (
        <p className="text-sm text-[var(--color-text-primary)] leading-relaxed mb-4" {...props}>{children}</p>
      ),
      a: ({ children, href, ...props }) => {
        if (href?.startsWith("/wiki/")) {
          return <span className="text-[var(--color-accent-gold-dim)] cursor-default" {...props}>{children}</span>;
        }
        return <a href={href} className="text-[var(--color-accent-blue)] hover:underline" target="_blank" rel="noopener noreferrer" {...props}>{children}</a>;
      },
      table: ({ children, ...props }) => (
        <div className="overflow-x-auto mb-4">
          <table className="w-full text-sm border-collapse border border-[var(--color-border)]" {...props}>{children}</table>
        </div>
      ),
      th: ({ children, ...props }) => (
        <th className="px-3 py-2 text-left text-xs font-heading font-semibold text-[var(--color-accent-gold)] bg-[var(--color-bg-tertiary)] border border-[var(--color-border)]" {...props}>{children}</th>
      ),
      td: ({ children, ...props }) => (
        <td className="px-3 py-2 text-sm border border-[var(--color-border)] text-[var(--color-text-primary)]" {...props}>{children}</td>
      ),
      blockquote: ({ children, ...props }) => (
        <blockquote className="border-l-2 border-[var(--color-accent-gold-dim)] pl-4 my-4 text-[var(--color-text-secondary)] italic" {...props}>{children}</blockquote>
      ),
      code: ({ children, className, ...props }) => {
        const isBlock = className?.includes("language-");
        if (isBlock) {
          return (
            <pre className="bg-[var(--color-bg-primary)] border border-[var(--color-border)] rounded-md p-4 overflow-x-auto mb-4">
              <code className="text-xs text-[var(--color-text-primary)]" {...props}>{children}</code>
            </pre>
          );
        }
        return <code className="text-xs bg-[var(--color-bg-tertiary)] px-1.5 py-0.5 rounded text-[var(--color-accent-gold)]" {...props}>{children}</code>;
      },
      ul: ({ children, ...props }) => (
        <ul className="list-disc list-inside text-sm text-[var(--color-text-primary)] mb-4 space-y-1" {...props}>{children}</ul>
      ),
      ol: ({ children, ...props }) => (
        <ol className="list-decimal list-inside text-sm text-[var(--color-text-primary)] mb-4 space-y-1" {...props}>{children}</ol>
      ),
      hr: () => <hr className="poe-divider my-6" />,
    }),
    [],
  );

  return (
    <div className="max-w-none">
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </Markdown>
    </div>
  );
}

function RelatedPanel({ documents }: { documents: RelatedDocument[] }) {
  return (
    <div className="sticky top-6">
      <h4 className="font-heading text-xs font-semibold text-[var(--color-accent-gold-dim)] uppercase tracking-wider mb-3">
        Related Documents
      </h4>
      <ul className="space-y-2">
        {documents.map((doc) => (
          <li key={doc.id}>
            <Link
              to={`/doc/${toSlug(doc.id, doc.filename)}`}
              className="poe-card block p-3 hover:border-[var(--color-accent-gold-dim)] transition-colors"
            >
              <p className="text-xs font-medium text-[var(--color-text-heading)] truncate">
                {doc.title || filenameToTitle(doc.filename)}
              </p>
              <p className="text-xs text-[var(--color-text-muted)] mt-1">
                {(doc.score * 100).toFixed(0)}% related
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function DocumentSkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-6 py-6">
      <div className="poe-skeleton h-4 w-32 mb-4" />
      <div className="poe-card p-8 space-y-4">
        <div className="poe-skeleton h-8 w-2/3" />
        <div className="poe-skeleton h-4 w-1/3" />
        <hr className="poe-divider my-6" />
        <div className="space-y-3">
          {[95, 80, 88, 72, 92, 68, 85, 76].map((w, i) => (
            <div key={i} className="poe-skeleton h-4" style={{ width: `${w}%` }} />
          ))}
        </div>
      </div>
    </div>
  );
}
