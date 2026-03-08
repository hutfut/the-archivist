import type { ReactNode } from "react";

export interface Heading {
  level: number;
  text: string;
  id: string;
}

/**
 * Parse markdown text and extract h2/h3 headings with generated anchor IDs.
 */
export function extractHeadings(markdown: string): Heading[] {
  const headings: Heading[] = [];
  for (const line of markdown.split("\n")) {
    const match = line.match(/^(#{2,3})\s+(.+)/);
    if (match) {
      const text = match[2].replace(/[*_`[\]]/g, "").trim();
      const id = text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      headings.push({ level: match[1].length, text, id });
    }
  }
  return headings;
}

/**
 * Recursively extract plain text from React children (ReactNode tree).
 */
export function extractText(children: ReactNode): string {
  if (typeof children === "string") return children;
  if (typeof children === "number") return String(children);
  if (Array.isArray(children)) return children.map(extractText).join("");
  if (children && typeof children === "object" && "props" in children) {
    const el = children as { props: { children?: ReactNode } };
    return extractText(el.props.children);
  }
  return "";
}
