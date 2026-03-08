import { describe, it, expect } from "vitest";
import {
  filenameToTitle,
  toSlug,
  fromSlug,
  fileTypeBadge,
  formatFileSize,
  formatDate,
} from "../utils";

describe("filenameToTitle", () => {
  it("strips extension and capitalizes words", () => {
    expect(filenameToTitle("Life.md")).toBe("Life");
  });

  it("replaces hyphens and underscores with spaces", () => {
    expect(filenameToTitle("quarterly_report.pdf")).toBe("Quarterly Report");
    expect(filenameToTitle("my-cool-doc.txt")).toBe("My Cool Doc");
  });

  it("handles filenames with multiple dots", () => {
    expect(filenameToTitle("v2.0.release-notes.md")).toBe("V2.0.Release Notes");
  });

  it("handles filenames without an extension", () => {
    expect(filenameToTitle("README")).toBe("README");
  });

  it("returns empty string for empty input", () => {
    expect(filenameToTitle("")).toBe("");
  });
});

describe("toSlug", () => {
  it("builds a slug from id and filename", () => {
    const slug = toSlug("abc-123", "My Document.md");
    expect(slug).toBe("abc-123--my-document");
  });

  it("strips special characters from the title portion", () => {
    const slug = toSlug("id1", "hello@world!.txt");
    expect(slug).toBe("id1--hello-world");
  });

  it("handles empty title gracefully", () => {
    const slug = toSlug("id1", ".md");
    expect(slug).toBe("id1--");
  });
});

describe("fromSlug", () => {
  it("extracts the id before the -- separator", () => {
    expect(fromSlug("abc-123--my-document")).toBe("abc-123");
  });

  it("returns the whole string when no separator is present", () => {
    expect(fromSlug("abc-123")).toBe("abc-123");
  });

  it("handles multiple -- by splitting on the first", () => {
    expect(fromSlug("id--title--extra")).toBe("id");
  });
});

describe("fileTypeBadge", () => {
  it("returns PDF badge for application/pdf", () => {
    const badge = fileTypeBadge("application/pdf");
    expect(badge.label).toBe("PDF");
    expect(badge.className).toBe("poe-badge-pdf");
  });

  it("returns MD badge for text/markdown", () => {
    const badge = fileTypeBadge("text/markdown");
    expect(badge.label).toBe("MD");
    expect(badge.className).toBe("poe-badge-md");
  });

  it("returns TXT badge for text/plain", () => {
    const badge = fileTypeBadge("text/plain");
    expect(badge.label).toBe("TXT");
    expect(badge.className).toBe("poe-badge-txt");
  });

  it("returns DOC badge for unknown content types", () => {
    const badge = fileTypeBadge("application/octet-stream");
    expect(badge.label).toBe("DOC");
    expect(badge.className).toBe("poe-badge-txt");
  });
});

describe("formatFileSize", () => {
  it("formats 0 bytes", () => {
    expect(formatFileSize(0)).toBe("0 B");
  });

  it("formats small byte values without decimals", () => {
    expect(formatFileSize(512)).toBe("512 B");
  });

  it("formats exactly 1 KB boundary", () => {
    expect(formatFileSize(1024)).toBe("1.0 KB");
  });

  it("formats kilobyte values with one decimal", () => {
    expect(formatFileSize(1536)).toBe("1.5 KB");
  });

  it("formats exactly 1 MB boundary", () => {
    expect(formatFileSize(1048576)).toBe("1.0 MB");
  });

  it("formats megabyte values", () => {
    expect(formatFileSize(5242880)).toBe("5.0 MB");
  });

  it("formats gigabyte values", () => {
    expect(formatFileSize(1073741824)).toBe("1.0 GB");
  });
});

describe("formatDate", () => {
  it("formats a valid ISO string into a readable date", () => {
    const result = formatDate("2026-03-08T12:00:00Z");
    expect(result).toMatch(/Mar/);
    expect(result).toMatch(/8/);
    expect(result).toMatch(/2026/);
  });

  it("handles different ISO strings", () => {
    const result = formatDate("2025-12-25T00:00:00Z");
    expect(result).toMatch(/Dec/);
    expect(result).toMatch(/25/);
    expect(result).toMatch(/2025/);
  });
});
