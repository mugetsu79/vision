import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, test } from "vitest";

import {
  LIVE_TILE_LAYOUT_STORAGE_KEY,
  useLiveTileLayout,
} from "@/hooks/use-live-tile-layout";

describe("useLiveTileLayout", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  test("defaults tiles to standard", () => {
    const { result } = renderHook(() => useLiveTileLayout());

    expect(result.current.tileSizeFor("camera-1")).toBe("standard");
  });

  test("persists per-camera tile sizes", () => {
    const { result, rerender } = renderHook(() => useLiveTileLayout());

    act(() => {
      result.current.setTileSize("camera-1", "large");
    });
    rerender();

    expect(result.current.tileSizeFor("camera-1")).toBe("large");
    expect(
      JSON.parse(localStorage.getItem(LIVE_TILE_LAYOUT_STORAGE_KEY)!),
    ).toEqual({
      "camera-1": "large",
    });
  });
});
