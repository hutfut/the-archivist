/**
 * Derive a human-readable title from a filename.
 * "Life.md" -> "Life", "quarterly_report.pdf" -> "Quarterly Report"
 */
export function filenameToTitle(filename: string): string {
  const withoutExt = filename.replace(/\.[^.]+$/, "");
  return withoutExt
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .trim();
}

/**
 * Build a URL-friendly slug from a document ID and filename.
 * Embeds the UUID so we can extract it for API calls.
 */
export function toSlug(id: string, filename: string): string {
  const title = filenameToTitle(filename)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${id}--${title}`;
}

/**
 * Extract the document ID from a slug.
 */
export function fromSlug(slug: string): string {
  const sep = slug.indexOf("--");
  return sep === -1 ? slug : slug.slice(0, sep);
}

/**
 * Get file type label from content_type.
 */
export function fileTypeBadge(contentType: string): { label: string; className: string } {
  switch (contentType) {
    case "application/pdf":
      return { label: "PDF", className: "poe-badge-pdf" };
    case "text/markdown":
      return { label: "MD", className: "poe-badge-md" };
    case "text/plain":
      return { label: "TXT", className: "poe-badge-txt" };
    default:
      return { label: "DOC", className: "poe-badge-txt" };
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** i;
  return `${i === 0 ? value : value.toFixed(1)} ${units[i]}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
