import { useCallback, useEffect, useMemo, useState } from "react";

import { InspectorPanel } from "@/components/layout/InspectorPanel";
import {
  StatusToneBadge,
  WorkspaceBand,
} from "@/components/layout/workspace-surfaces";
import { AgentInput, type LiveQueryScope } from "@/components/live/AgentInput";
import { DynamicStats } from "@/components/live/DynamicStats";
import { TelemetryCanvas } from "@/components/live/TelemetryCanvas";
import { TelemetryTerrain } from "@/components/live/TelemetryTerrain";
import { VideoStream } from "@/components/live/VideoStream";
import { SceneStatusStrip } from "@/components/operations/SceneStatusStrip";
import { Badge } from "@/components/ui/badge";
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
import { useCameras } from "@/hooks/use-cameras";
import { useLiveTelemetry } from "@/hooks/use-live-telemetry";
import { useFleetOverview } from "@/hooks/use-operations";
import { useStableSignalFrame } from "@/hooks/use-stable-signal-frame";
import type { components } from "@/lib/api.generated";
import { formatHeartbeat, getHeartbeatStatus } from "@/lib/live";
import {
  selectDrawableSignalTracks,
  type SignalCountRow,
} from "@/lib/live-signal-stability";
import {
  deriveSceneReadinessRows,
  type SceneHealthRow,
} from "@/lib/operational-health";

type QueryResponse = components["schemas"]["QueryResponse"];
type CameraResponse = components["schemas"]["CameraResponse"];
type TelemetryFrame = components["schemas"]["TelemetryFrame"];

export function LivePage() {
  return <WorkspacePage />;
}

function WorkspacePage() {
  const { data: cameras = [], isLoading } = useCameras();
  const fleet = useFleetOverview();
  const { connectionState, framesByCamera } = useLiveTelemetry(
    cameras.map((camera) => camera.id),
  );
  const [activeQuery, setActiveQuery] = useState<{
    response: QueryResponse;
    scope: LiveQueryScope;
  } | null>(null);
  const [signalRowsByCamera, setSignalRowsByCamera] = useState(
    () => new Map<string, SignalCountRow[]>(),
  );

  const handleSignalRowsChange = useCallback(
    (cameraId: string, rows: SignalCountRow[]) => {
      setSignalRowsByCamera((current) => {
        const next = new Map(current);
        next.set(cameraId, rows);
        return next;
      });
    },
    [],
  );

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

    filters.set(
      activeQuery.scope.cameraId,
      activeQuery.response.resolved_classes,
    );
    return filters;
  }, [activeQuery, cameras]);

  const signalRows = useMemo<SignalCountRow[]>(() => {
    const rowsByClass = new Map<string, SignalCountRow>();

    for (const rows of signalRowsByCamera.values()) {
      for (const row of rows) {
        if (row.totalCount <= 0) {
          continue;
        }

        const aggregate: SignalCountRow =
          rowsByClass.get(row.className) ??
          {
            className: row.className,
            color: row.color,
            liveCount: 0,
            heldCount: 0,
            totalCount: 0,
            state: "held",
          };

        aggregate.liveCount += row.liveCount;
        aggregate.heldCount += row.heldCount;
        aggregate.totalCount += row.totalCount;
        aggregate.state = aggregate.liveCount > 0 ? "live" : "held";
        rowsByClass.set(row.className, aggregate);
      }
    }

    return Array.from(rowsByClass.values()).sort(
      (left, right) =>
        right.liveCount - left.liveCount ||
        right.totalCount - left.totalCount ||
        left.className.localeCompare(right.className),
    );
  }, [signalRowsByCamera]);

  const sceneHealthRows = useMemo(
    () =>
      deriveSceneReadinessRows({
        cameras,
        fleet: fleet.data,
        framesByCamera,
      }),
    [cameras, fleet.data, framesByCamera],
  );
  const sceneHealthByCamera = useMemo(
    () => new Map(sceneHealthRows.map((row) => [row.cameraId, row])),
    [sceneHealthRows],
  );

  return (
    <div
      data-testid="live-intelligence-workspace"
      className="grid gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1fr)_340px]"
    >
      <section className="min-w-0 space-y-5">
        <WorkspaceBand
          eyebrow="Live"
          title={omniLabels.liveTitle}
          description="Watch scenes, signals, and operator intent converge in one live spatial intelligence layer."
          actions={
            <>
              <StatusToneBadge tone={connectionTone(connectionState)}>
                {connectionBadgeLabel(connectionState)}
              </StatusToneBadge>
              <StatusToneBadge tone="accent">
                {cameras.length} connected scenes
              </StatusToneBadge>
            </>
          }
        />

        <AgentInput
          cameras={cameras.map((camera) => ({
            id: camera.id,
            name: camera.name,
          }))}
          onResolved={(response, scope) => {
            setActiveQuery({ response, scope });
          }}
        />

        {isLoading ? (
          <div className="rounded-[1rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
            Loading connected scenes...
          </div>
        ) : cameras.length === 0 ? (
          <div className="rounded-[1rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-sm text-[#9bb0d0]">
            {omniEmptyStates.noScenes}
          </div>
        ) : (
          <section
            className="space-y-3"
            aria-labelledby="active-scenes-heading"
          >
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#8ea8cf]">
                  Scene portal grid
                </p>
                <h2
                  id="active-scenes-heading"
                  className="mt-1 text-xl font-semibold text-[#f3f7ff]"
                >
                  Active scenes
                </h2>
              </div>
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {activeQuery ? "Resolved view" : "Unfiltered view"}
              </Badge>
            </div>

            <div
              data-testid="scene-portal-grid"
              className="grid gap-4 md:grid-cols-2"
            >
              {cameras.map((camera) => {
                const frame = framesByCamera[camera.id];
                const classFilter = classFiltersByCamera.get(camera.id) ?? null;
                const sceneHealth = sceneHealthByCamera.get(camera.id);

                return (
                  <ScenePortalCard
                    key={camera.id}
                    camera={camera}
                    frame={frame}
                    classFilter={classFilter}
                    sceneHealth={sceneHealth}
                    onSignalRowsChange={handleSignalRowsChange}
                  />
                );
              })}
            </div>
          </section>
        )}
      </section>

      <aside data-testid="spatial-instrument-rail" className="space-y-4">
        <DynamicStats signalRows={signalRows} />

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
              <p className="mt-2 text-sm text-[#90a7c9]">
                {activeQuery.response.model}
              </p>
              <p className="mt-1 text-sm text-[#7f95b6]">
                {activeQuery.response.latency_ms} ms
              </p>
            </>
          ) : (
            <p className="text-sm text-[#8ca2c5]">
              No intent is active. Operators are seeing the current signal set
              from each live scene.
            </p>
          )}
        </InspectorPanel>
      </aside>
    </div>
  );
}

function ScenePortalCard({
  camera,
  frame,
  classFilter,
  sceneHealth,
  onSignalRowsChange,
}: {
  camera: CameraResponse;
  frame: TelemetryFrame | undefined;
  classFilter: string[] | null;
  sceneHealth: SceneHealthRow | undefined;
  onSignalRowsChange: (cameraId: string, rows: SignalCountRow[]) => void;
}) {
  const stableSignal = useStableSignalFrame(frame, classFilter);
  const sourceSize = getCameraSourceSize(camera);
  const overlayTracks = useMemo(
    () => selectDrawableSignalTracks(stableSignal.tracks, frame?.stream_mode),
    [frame?.stream_mode, stableSignal.tracks],
  );
  const visibleCopy =
    stableSignal.counts.total > 0
      ? `${stableSignal.counts.total} visible now`
      : "0 visible now";
  const heartbeatStatus = getHeartbeatStatus(frame);
  const deliveryProfileLabel = formatDeliveryProfile(camera);

  useEffect(() => {
    onSignalRowsChange(camera.id, stableSignal.counts.rows);
  }, [camera.id, onSignalRowsChange, stableSignal.counts.rows]);

  useEffect(() => {
    return () => {
      onSignalRowsChange(camera.id, []);
    };
  }, [camera.id, onSignalRowsChange]);

  return (
    <article
      data-testid="scene-portal"
      data-scene-portal-tile
      tabIndex={0}
      className="group relative overflow-hidden rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] shadow-[var(--vz-elev-1)] outline-none transition duration-200 hover:-translate-y-0.5 hover:shadow-[var(--vz-elev-glow-cerulean)] focus-within:shadow-[var(--vz-elev-glow-cerulean)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/8 px-5 py-4">
        <div>
          <h3 className="text-xl font-semibold text-[#f3f7ff]">
            {camera.name}
          </h3>
          <p className="mt-2 text-sm text-[#88a2c7]">
            {camera.processing_mode} processing · {deliveryProfileLabel}
          </p>
          {camera.browser_delivery?.native_status?.available === false ? (
            <p className="mt-2 text-xs text-[#ffd28a]">
              Direct stream unavailable:{" "}
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
        {sceneHealth ? (
          <div className="basis-full pt-1">
            <SceneStatusStrip row={sceneHealth} />
          </div>
        ) : null}
      </div>

      <div
        data-scene-portal-media
        className="relative aspect-video bg-[color:var(--vz-media-black)]"
      >
        <span data-bracket aria-hidden="true" />
        <VideoStream
          cameraId={camera.id}
          cameraName={camera.name}
          defaultProfile={camera.browser_delivery?.default_profile ?? "720p10"}
          heartbeatTs={frame?.ts ?? null}
        />
        <TelemetryCanvas
          frame={frame}
          activeClasses={classFilter}
          tracks={overlayTracks}
          sourceSize={sourceSize}
        />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-wrap items-end justify-between gap-3 bg-[linear-gradient(180deg,transparent,rgba(2,4,8,0.92))] px-4 pb-3 pt-12">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-[#8ea8cf]">
              {formatHeartbeat(frame)}
            </p>
            <p className="mt-1 text-sm text-[#dce6f7]">{visibleCopy}</p>
          </div>
          {frame ? (
            <p className="text-xs text-[#9db3d3]">{formatStreamMode(frame)}</p>
          ) : null}
        </div>
      </div>

      <div className="space-y-3 border-t border-white/8 px-5 py-4">
        <TelemetryTerrain
          cameraId={camera.id}
          cameraName={camera.name}
          activeClasses={camera.active_classes ?? []}
          signalRows={stableSignal.counts.rows}
        />
      </div>
    </article>
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

function connectionTone(
  connectionState: string,
): "healthy" | "attention" | "danger" | "accent" {
  if (connectionState === "open") {
    return "healthy";
  }
  if (connectionState === "error") {
    return "danger";
  }
  if (connectionState === "closed") {
    return "attention";
  }
  return "accent";
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

function formatDeliveryProfile(camera: CameraResponse): string {
  const defaultProfile = camera.browser_delivery?.default_profile ?? "720p10";
  const profiles = camera.browser_delivery?.profiles ?? [];
  const profile = profiles.find((candidate) => candidate.id === defaultProfile);
  if (typeof profile?.label === "string" && profile.label.length > 0) {
    return profile.label;
  }

  const isEdge = camera.processing_mode === "edge" || camera.edge_node_id !== null;
  if (defaultProfile === "native") {
    return isEdge ? "Native edge passthrough" : "Native camera";
  }
  if (defaultProfile === "annotated") {
    return isEdge ? "Annotated edge stream" : "Annotated";
  }
  return isEdge
    ? `${defaultProfile} edge bandwidth saver`
    : `${defaultProfile} viewer preview`;
}

function formatStreamMode(frame: TelemetryFrame): string {
  return frame.stream_mode;
}

function getCameraSourceSize(camera: CameraResponse): { width: number; height: number } | null {
  const source = camera.source_capability;
  if (!source || source.width <= 0 || source.height <= 0) {
    return null;
  }

  return { width: source.width, height: source.height };
}

function formatNativeAvailabilityReason(
  reason: string | null | undefined,
): string {
  return reason ? reason.replaceAll("_", " ") : "not available";
}
