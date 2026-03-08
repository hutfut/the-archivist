import { useCallback, useSyncExternalStore } from "react";

interface RecentlyViewedItem {
  id: string;
  filename: string;
  title: string;
  viewedAt: string;
}

const STORAGE_KEY = "exiles-archive-recently-viewed";
const MAX_ITEMS = 10;

let listeners: Array<() => void> = [];

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

function getSnapshot(): RecentlyViewedItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function subscribe(listener: () => void): () => void {
  listeners = [...listeners, listener];
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

export function useRecentlyViewed() {
  const items = useSyncExternalStore(subscribe, getSnapshot, () => []);

  const addItem = useCallback(
    (item: Omit<RecentlyViewedItem, "viewedAt">) => {
      const current = getSnapshot();
      const filtered = current.filter((i) => i.id !== item.id);
      const updated: RecentlyViewedItem[] = [
        { ...item, viewedAt: new Date().toISOString() },
        ...filtered,
      ].slice(0, MAX_ITEMS);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
      emitChange();
    },
    [],
  );

  return { items, addItem };
}
