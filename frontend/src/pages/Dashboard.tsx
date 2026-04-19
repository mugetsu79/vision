import { useMemo, useState } from "react";

import { AgentInput, type LiveQueryScope } from "@/components/live/AgentInput";
import { DynamicStats } from "@/components/live/DynamicStats";
import { TelemetryCanvas } from "@/components/live/TelemetryCanvas";
import { VideoStream } from "@/components/live/VideoStream";
import { Badge } from "@/components/ui/badge";
import { useCameras } from "@/hooks/use-cameras";
import {
  countTracksByClass,
  filterTracks,
  formatHeartbeat,
  isHeartbeatFresh,
} from "@/lib/live";
import type { components } from "@/lib/api.generated";
import { useLiveTelemetry } from "@/hooks/use-live-telemetry";

type QueryResponse = components["schemas"]["QueryResponse"];

export function DashboardPage() {
  const { data: cameras = [], isLoading } = useCameras();
  const { connectionState, framesByCamera } = useLiveTelemetry(cameras.map((camera) => camera.id));
  const [activeQuery, setActiveQuery] = useState<{
    response: QueryResponse;
    scope: LiveQueryScope;
  } | null>(null);

  const classFiltersByCamera = useMemo(() => {
    const filters = new Map<string, string[] | null>();

    if (!activeQuery) {
      return filters;
    }

    if (activeQuery.scope.scope === "all") {
      for (const camera of cameras) {
        filters.set(camera.id, activeQuery.response.resolved_classes);
      }
      return filters;
    }

    filters.set(activeQuery.scope.cameraId, activeQuery.response.resolved_classes);
    return filters;
  }, [activeQuery, cameras]);

  const counts = useMemo(() => {
    const aggregated: Record<string, number> = {};

    for (const camera of cameras) {
      const frame = framesByCamera[camera.id];
      const classFilter = classFiltersByCamera.get(camera.id) ?? null;
      const visibleCounts = countTracksByClass(frame, classFilter);
      for (const [className, count] of Object.entries(visibleCounts)) {
        aggregated[className] = (aggregated[className] ?? 0) + count;
      }
    }

    return aggregated;
  }, [cameras, classFiltersByCamera, framesByCamera]);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(64,114,255,0.16),transparent_36%),linear-gradient(180deg,rgba(13,18,29,0.98),rgba(6,9,15,0.96))] shadow-[0_32px_96px_-56px_rgba(53,107,255,0.5)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
                Live command surface
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Operator-grade visibility without native-bandwidth waste.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                Argus keeps analytics on native ingest, then serves delivery-aware
                renditions, overlays, and live query filters through one control-room
                workspace.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {connectionBadgeLabel(connectionState)}
              </Badge>
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {cameras.length} cameras
              </Badge>
            </div>
          </div>
        </div>

        <div className="space-y-6 px-6 py-6">
          <AgentInput
            cameras={cameras.map((camera) => ({ id: camera.id, name: camera.name }))}
            onResolved={(response, scope) => {
              setActiveQuery({ response, scope });
            }}
          />

          {isLoading ? (
            <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
              Loading live cameras...
            </div>
          ) : cameras.length === 0 ? (
            <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
              No cameras are configured yet.
            </div>
          ) : (
            <div className="grid gap-5 md:grid-cols-2">
              {cameras.map((camera) => {
                const frame = framesByCamera[camera.id];
                const classFilter = classFiltersByCamera.get(camera.id) ?? null;
                const visibleTracks = filterTracks(frame, classFilter);
                const online = isHeartbeatFresh(frame);

                return (
                  <article
                    key={camera.id}
                    className="overflow-hidden rounded-[1.7rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,14,22,0.98),rgba(4,7,12,0.96))] shadow-[0_18px_48px_-36px_rgba(5,14,28,0.95)]"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/8 px-5 py-4">
                      <div>
                        <h3 className="text-xl font-semibold text-[#f3f7ff]">{camera.name}</h3>
                        <p className="mt-2 text-sm text-[#88a2c7]">
                          {camera.processing_mode} processing ·{" "}
                          {camera.browser_delivery?.default_profile ?? "720p10"}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Badge
                          className={
                            online
                              ? "border-[#1f654c] bg-[#082118] text-[#b6f7d2]"
                              : "border-[#5d2f3b] bg-[#221018] text-[#ffd2db]"
                          }
                        >
                          {online ? "online" : "offline"}
                        </Badge>
                        <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                          {camera.tracker_type}
                        </Badge>
                      </div>
                    </div>

                    <div className="relative aspect-video bg-[#02050b]">
                      <VideoStream
                        cameraId={camera.id}
                        cameraName={camera.name}
                        defaultProfile={camera.browser_delivery?.default_profile ?? "720p10"}
                      />
                      <TelemetryCanvas frame={frame} activeClasses={classFilter} />
                      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-wrap items-end justify-between gap-3 bg-[linear-gradient(180deg,transparent,rgba(2,4,8,0.92))] px-4 pb-3 pt-12">
                        <div>
                          <p className="text-xs font-medium uppercase tracking-[0.18em] text-[#8ea8cf]">
                            {formatHeartbeat(frame)}
                          </p>
                          <p className="mt-1 text-sm text-[#dce6f7]">
                            {visibleTracks.length} visible detections
                          </p>
                        </div>
                        {frame ? (
                          <p className="text-xs text-[#9db3d3]">{frame.stream_mode}</p>
                        ) : null}
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <aside className="space-y-6">
        <DynamicStats counts={counts} />

        <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(9,15,24,0.98),rgba(4,7,12,0.96))]">
          <div className="border-b border-white/8 px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">
              Active filter
            </p>
            <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">
              Current command resolution.
            </h3>
          </div>

          <div className="space-y-3 px-5 py-5">
            {activeQuery ? (
              <>
                <p className="text-sm text-[#dce6f7]">
                  {activeQuery.response.resolved_classes.join(", ")}
                </p>
                <p className="text-sm text-[#90a7c9]">
                  {activeQuery.response.model} · {activeQuery.response.latency_ms} ms
                </p>
              </>
            ) : (
              <p className="text-sm text-[#8ca2c5]">
                No natural-language filter is active. Operators are currently seeing the
                raw class set from each live scene.
              </p>
            )}
          </div>
        </section>
      </aside>
    </div>
  );
}

function connectionBadgeLabel(connectionState: string): string {
  if (connectionState === "open") {
    return "Telemetry live";
  }
  if (connectionState === "error") {
    return "Telemetry degraded";
  }
  if (connectionState === "closed") {
    return "Telemetry reconnecting";
  }
  return "Telemetry connecting";
}
