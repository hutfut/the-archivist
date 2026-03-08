import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useRecentlyViewed } from "../useRecentlyViewed";

const STORAGE_KEY = "exiles-archive-recently-viewed";

beforeEach(() => {
  localStorage.clear();
});

describe("useRecentlyViewed", () => {
  it("returns empty items when localStorage is empty", () => {
    const { result } = renderHook(() => useRecentlyViewed());
    expect(result.current.items).toEqual([]);
  });

  it("adds an item and reflects it in items", () => {
    const { result } = renderHook(() => useRecentlyViewed());

    act(() => {
      result.current.addItem({ id: "1", filename: "doc.md", title: "Doc" });
    });

    expect(result.current.items).toHaveLength(1);
    expect(result.current.items[0]).toMatchObject({
      id: "1",
      filename: "doc.md",
      title: "Doc",
    });
    expect(result.current.items[0].viewedAt).toBeDefined();
  });

  it("writes to localStorage", () => {
    const { result } = renderHook(() => useRecentlyViewed());

    act(() => {
      result.current.addItem({ id: "1", filename: "doc.md", title: "Doc" });
    });

    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY)!);
    expect(stored).toHaveLength(1);
    expect(stored[0].id).toBe("1");
  });

  it("moves existing item to top on re-add (deduplication)", () => {
    const { result } = renderHook(() => useRecentlyViewed());

    act(() => {
      result.current.addItem({ id: "1", filename: "a.md", title: "A" });
    });
    act(() => {
      result.current.addItem({ id: "2", filename: "b.md", title: "B" });
    });
    act(() => {
      result.current.addItem({ id: "1", filename: "a.md", title: "A" });
    });

    expect(result.current.items).toHaveLength(2);
    expect(result.current.items[0].id).toBe("1");
    expect(result.current.items[1].id).toBe("2");
  });

  it("caps at 10 items", () => {
    const { result } = renderHook(() => useRecentlyViewed());

    act(() => {
      for (let i = 0; i < 12; i++) {
        result.current.addItem({
          id: String(i),
          filename: `${i}.md`,
          title: `Doc ${i}`,
        });
      }
    });

    expect(result.current.items).toHaveLength(10);
    expect(result.current.items[0].id).toBe("11");
  });

  it("handles corrupted JSON in localStorage gracefully", () => {
    localStorage.setItem(STORAGE_KEY, "not valid json{{{");
    const { result } = renderHook(() => useRecentlyViewed());
    expect(result.current.items).toEqual([]);
  });
});
