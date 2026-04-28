import { useMemo, useState } from "react";

import { InspectorPanel } from "@/components/layout/InspectorPanel";
import { PageHeader } from "@/components/layout/PageHeader";
import { PageUtilityBar } from "@/components/layout/PageUtilityBar";
import { AgentInput, type LiveQueryScope } from "@/components/live/AgentInput";
import { DynamicStats } from "@/components/live/DynamicStats";
import { LiveSparkline } from "@/components/live/LiveSparkline";
import { TelemetryCanvas } from "@/components/live/TelemetryCanvas";
import { VideoStream } from "@/components/live/VideoStream";
import { Badge } from "@/components/ui/badge";
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
import { useCameras } from "@/hooks/use-cameras";
import {
  formatHeartbeat,
  getHeartbeatStatus,
} from "@/lib/live";
import type { components } from "@/lib/api.generated";
import { useLiveTelemetry } from "@/hooks/use-live-telemetry";

type QueryResponse = components["schemas"]["QueryResponse"];

export function LivePage() {
  return <WorkspacePage />;
}

function WorkspacePage() {
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
      for (const [className, count] of Object.entries(frame?.counts ?? {})) {
        if (classFilter && !classFilter.includes(className)) {
          continue;
        }
        aggregated[className] = (aggregated[className] ?? 0) + count;
      }
    }

    return aggregated;
  }, [cameras, classFiltersByCamera, framesByCamera]);

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
      <section className="min-w-0 space-y-5">
        <PageHeader
          eyebrow="Live"
          title={omniLabels.liveTitle}
          description="Watch scenes, signals, and operator intent converge in one live spatial intelligence layer."
          actions={
            <>
              <Badge className={connectionBadgeClass(connectionState)}>
                {connectionBadgeLabel(connectionState)}
              </Badge>
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {cameras.length} connected scenes
              </Badge>
            </>
          }
        />

        <PageUtilityBar
          label="Workspace utility"
          title="Ask Vezor without leaving the live wall"
          description={
            isLoading
              ? "Loading connected scenes."
              : "Resolved intent narrows the operator view while telemetry remains truthful."
          }
          actions={<Badge className={connectionBadgeClass(connectionState)}>{connectionBadgeLabel(connectionState)}</Badge>}
        >
          <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
            {activeQuery ? "Filtered view active" : "Raw scene"}
          </Badge>
          <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
            {cameras.length} connected scenes
          </Badge>
        </PageUtilityBar>

        <AgentInput
          cameras={cameras.map((camera) => ({ id: camera.id, name: camera.name }))}
          onResolved={(response, scope) => {
            setActiveQuery({ response, scope });
          }}
        />

        {isLoading ? (
          <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
            Loading connected scenes...
          </div>
        ) : cameras.length === 0 ? (
          <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
            {omniEmptyStates.noScenes}
          </div>
        ) : (
          <div className="grid gap-5 md:grid-cols-2">
            {cameras.map((camera) => {
              const frame = framesByCamera[camera.id];
              const classFilter = classFiltersByCamera.get(camera.id) ?? null;
              const heartbeatStatus = getHeartbeatStatus(frame);
              const visibleNow = Object.entries(frame?.counts ?? {}).reduce((total, [className, count]) => {
                if (classFilter && !classFilter.includes(className)) {
                  return total;
                }
                return total + count;
              }, 0);

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
                      {camera.browser_delivery?.native_status?.available === false ? (
                        <p className="mt-2 text-xs text-[#ffd28a]">
                          Native unavailable:{" "}
                          {formatNativeAvailabilityReason(
                            camera.browser_delivery.native_status.reason,
                          )}
                        </p>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Badge className={heartbeatBadgeClass(heartbeatStatus)}>
                        {heartbeatBadgeLabel(heartbeatStatus)}
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
                      heartbeatTs={frame?.ts ?? null}
                    />
                    <TelemetryCanvas frame={frame} activeClasses={classFilter} />
                    <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-wrap items-end justify-between gap-3 bg-[linear-gradient(180deg,transparent,rgba(2,4,8,0.92))] px-4 pb-3 pt-12">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-[0.18em] text-[#8ea8cf]">
                          {formatHeartbeat(frame)}
                        </p>
                        <p className="mt-1 text-sm text-[#dce6f7]">
                          {visibleNow} visible now
                        </p>
                      </div>
                      {frame ? <p className="text-xs text-[#9db3d3]">{frame.stream_mode}</p> : null}
                    </div>
                  </div>

                  <div className="space-y-3 border-t border-white/8 px-5 py-4">
                    <LiveSparkline
                      cameraId={camera.id}
                      activeClasses={camera.active_classes ?? []}
                    />
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <aside className="space-y-5">
        <DynamicStats counts={counts} />

        <InspectorPanel
          title={omniLabels.resolvedIntentTitle}
          description="Selection-aware interpretation for the current live view."
          actions={
            activeQuery ? (
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {activeQuery.response.latency_ms} ms
              </Badge>
            ) : null
          }
        >
          {activeQuery ? (
            <>
              <p className="text-sm text-[#dce6f7]">
                {activeQuery.response.resolved_classes.join(", ")}
              </p>
              <p className="mt-2 text-sm text-[#90a7c9]">{activeQuery.response.model}</p>
              <p className="mt-1 text-sm text-[#7f95b6]">
                {activeQuery.response.latency_ms} ms
              </p>
            </>
          ) : (
            <p className="text-sm text-[#8ca2c5]">
              No intent is active. Operators are seeing the current signal set from each live scene.
            </p>
          )}
        </InspectorPanel>
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

function connectionBadgeClass(connectionState: string): string {
  if (connectionState === "open") {
    return "border-[#1f654c] bg-[#082118] text-[#b6f7d2]";
  }
  if (connectionState === "error") {
    return "border-[#5d2f3b] bg-[#221018] text-[#ffd2db]";
  }
  if (connectionState === "closed") {
    return "border-[#6a4b1c] bg-[#24180d] text-[#ffd9a9]";
  }
  return "border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]";
}

function heartbeatBadgeLabel(status: "unknown" | "fresh" | "stale"): string {
  if (status === "fresh") {
    return "telemetry live";
  }
  if (status === "stale") {
    return "telemetry stale";
  }
  return "awaiting telemetry";
}

function heartbeatBadgeClass(status: "unknown" | "fresh" | "stale"): string {
  if (status === "fresh") {
    return "border-[#1f654c] bg-[#082118] text-[#b6f7d2]";
  }
  if (status === "stale") {
    return "border-[#6a4b1c] bg-[#24180d] text-[#ffd9a9]";
  }
  return "border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]";
}

function formatNativeAvailabilityReason(reason: string | null | undefined): string {
  return reason ? reason.replaceAll("_", " ") : "not available";
}
