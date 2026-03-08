import { describe, it, expect } from "vitest";
import { extractHeadings, extractText } from "../markdown";

describe("extractHeadings", () => {
  it("extracts h2 headings", () => {
    const md = "## Overview\nSome text\n## Details";
    const headings = extractHeadings(md);
    expect(headings).toEqual([
      { level: 2, text: "Overview", id: "overview" },
      { level: 2, text: "Details", id: "details" },
    ]);
  });

  it("extracts h3 headings", () => {
    const md = "### Sub Section";
    const headings = extractHeadings(md);
    expect(headings).toEqual([
      { level: 3, text: "Sub Section", id: "sub-section" },
    ]);
  });

  it("extracts both h2 and h3 in order", () => {
    const md = "## Parent\n### Child\n## Sibling";
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(3);
    expect(headings[0]).toMatchObject({ level: 2, text: "Parent" });
    expect(headings[1]).toMatchObject({ level: 3, text: "Child" });
    expect(headings[2]).toMatchObject({ level: 2, text: "Sibling" });
  });

  it("ignores h1 headings", () => {
    const md = "# Title\n## Section";
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(1);
    expect(headings[0].text).toBe("Section");
  });

  it("ignores h4+ headings", () => {
    const md = "#### Deep\n##### Deeper\n## Valid";
    const headings = extractHeadings(md);
    expect(headings).toHaveLength(1);
    expect(headings[0].text).toBe("Valid");
  });

  it("strips markdown formatting from heading text", () => {
    const md = "## **Bold** and *italic* and `code` and [link]";
    const headings = extractHeadings(md);
    expect(headings[0].text).toBe("Bold and italic and code and link");
  });

  it("generates correct kebab-case IDs", () => {
    const md = "## Hello World!";
    const headings = extractHeadings(md);
    expect(headings[0].id).toBe("hello-world");
  });

  it("strips leading and trailing dashes from IDs", () => {
    const md = "## !Special! Characters!";
    const headings = extractHeadings(md);
    expect(headings[0].id).not.toMatch(/^-/);
    expect(headings[0].id).not.toMatch(/-$/);
  });

  it("returns empty array for markdown with no headings", () => {
    expect(extractHeadings("Just a paragraph.")).toEqual([]);
  });

  it("returns empty array for empty string", () => {
    expect(extractHeadings("")).toEqual([]);
  });
});

describe("extractText", () => {
  it("returns string children as-is", () => {
    expect(extractText("hello")).toBe("hello");
  });

  it("converts number children to string", () => {
    expect(extractText(42)).toBe("42");
  });

  it("joins array children", () => {
    expect(extractText(["hello", " ", "world"])).toBe("hello world");
  });

  it("extracts text from nested React-like elements", () => {
    const element = { props: { children: "inner text" } };
    expect(extractText(element as React.ReactNode)).toBe("inner text");
  });

  it("recursively extracts from deeply nested elements", () => {
    const element = {
      props: {
        children: { props: { children: "deep" } },
      },
    };
    expect(extractText(element as React.ReactNode)).toBe("deep");
  });

  it("returns empty string for null", () => {
    expect(extractText(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(extractText(undefined)).toBe("");
  });

  it("returns empty string for boolean", () => {
    expect(extractText(true as unknown as React.ReactNode)).toBe("");
  });
});
