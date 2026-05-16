import { useCallback, useEffect, useState } from "react";

export const LIVE_TILE_LAYOUT_STORAGE_KEY = "vezor.live.tileLayout.v1";

export type LiveTileSize = "compact" | "standard" | "large";

type TileSizeMap = Record<string, LiveTileSize>;

const VALID_SIZES = new Set<LiveTileSize>(["compact", "standard", "large"]);

export function useLiveTileLayout() {
  const [sizes, setSizes] = useState<TileSizeMap>(() => readTileSizes());

  useEffect(() => {
    window.localStorage.setItem(
      LIVE_TILE_LAYOUT_STORAGE_KEY,
      JSON.stringify(sizes),
    );
  }, [sizes]);

  const tileSizeFor = useCallback(
    (cameraId: string): LiveTileSize => sizes[cameraId] ?? "standard",
    [sizes],
  );

  const setTileSize = useCallback((cameraId: string, size: LiveTileSize) => {
    setSizes((current) => ({ ...current, [cameraId]: size }));
  }, []);

  return { tileSizeFor, setTileSize };
}

function readTileSizes(): TileSizeMap {
  try {
    const parsed = JSON.parse(
      window.localStorage.getItem(LIVE_TILE_LAYOUT_STORAGE_KEY) ?? "{}",
    ) as unknown;
    if (!isRecord(parsed)) return {};

    return Object.fromEntries(
      Object.entries(parsed).filter((entry): entry is [string, LiveTileSize] => {
        const [, value] = entry;
        return isLiveTileSize(value);
      }),
    );
  } catch {
    return {};
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isLiveTileSize(value: unknown): value is LiveTileSize {
  return typeof value === "string" && VALID_SIZES.has(value as LiveTileSize);
}
