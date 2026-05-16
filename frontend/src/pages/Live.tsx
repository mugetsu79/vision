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
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { omniEmptyStates, omniLabels } from "@/copy/omnisight";
import { useCameras, useUpdateCamera } from "@/hooks/use-cameras";
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
type BrowserDeliverySettings = components["schemas"]["BrowserDeliverySettings"];
type BrowserDeliveryProfile = NonNullable<BrowserDeliverySettings["profiles"]>[number];
type LiveRenditionOption = {
  id: string;
  label: string;
  description: string | null;
};

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
  const updateCamera = useUpdateCamera();
  const [browserOverlayEnabled, setBrowserOverlayEnabled] = useState(true);
  const renditionOptions = useMemo(
    () => getAvailableRenditionOptions(camera),
    [camera],
  );
  const currentProfile = camera.browser_delivery?.default_profile ?? "720p10";
  const [stagedProfile, setStagedProfile] = useState<string>(currentProfile);
  const sourceSize = getCameraSourceSize(camera);
  const overlayTracks = useMemo(
    () => selectDrawableSignalTracks(stableSignal.tracks, frame?.stream_mode),
    [frame?.stream_mode, stableSignal.tracks],
  );
  const visibleCopy =
    stableSignal.counts.liveTotal > 0
      ? `${stableSignal.counts.liveTotal} visible now`
      : "0 visible now";
  const heartbeatStatus = getHeartbeatStatus(frame);
  const deliveryProfileLabel = formatDeliveryProfile(camera);
  const selectedRendition = renditionOptions.find(
    (option) => option.id === stagedProfile,
  );
  const hasRenditionChange = stagedProfile !== currentProfile;
  const canApplyRendition =
    hasRenditionChange &&
    camera.browser_delivery !== undefined &&
    camera.browser_delivery !== null &&
    !updateCamera.isPending;

  useEffect(() => {
    setStagedProfile(currentProfile);
  }, [currentProfile]);

  useEffect(() => {
    onSignalRowsChange(camera.id, stableSignal.counts.rows);
  }, [camera.id, onSignalRowsChange, stableSignal.counts.rows]);

  useEffect(() => {
    return () => {
      onSignalRowsChange(camera.id, []);
    };
  }, [camera.id, onSignalRowsChange]);

  const applyRendition = useCallback(async () => {
    if (!camera.browser_delivery || stagedProfile === currentProfile) {
      return;
    }

    await updateCamera.mutateAsync({
      cameraId: camera.id,
      payload: {
        browser_delivery: {
          ...camera.browser_delivery,
          // The server profile catalog can be wider than the generated union.
          default_profile:
            stagedProfile as BrowserDeliverySettings["default_profile"],
        },
      },
    });
  }, [camera.browser_delivery, camera.id, currentProfile, stagedProfile, updateCamera]);

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
          deliveryMode={camera.browser_delivery?.delivery_mode ?? null}
          heartbeatTs={frame?.ts ?? null}
        />
        <TelemetryCanvas
          frame={frame}
          activeClasses={classFilter}
          tracks={overlayTracks}
          sourceSize={sourceSize}
          disabled={!browserOverlayEnabled}
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
        <div className="grid gap-3 rounded-[0.75rem] border border-white/8 bg-[#07101c]/80 p-3 sm:grid-cols-[minmax(0,1fr)_auto]">
          <label className="flex items-center gap-2 text-xs font-medium text-[#c7d8f2]">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[#6ebdff]"
              checked={browserOverlayEnabled}
              onChange={(event) => setBrowserOverlayEnabled(event.target.checked)}
            />
            Browser overlay
          </label>

          {renditionOptions.length > 0 ? (
            <div className="grid gap-2 sm:min-w-[240px]">
              <label
                className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]"
                htmlFor={`live-rendition-${camera.id}`}
              >
                Live rendition
              </label>
              <div className="flex flex-wrap items-center gap-2">
                <Select
                  id={`live-rendition-${camera.id}`}
                  aria-label={`${camera.name} live rendition`}
                  className="min-w-[170px] flex-1 rounded-[0.65rem] px-3 py-2"
                  value={stagedProfile}
                  onChange={(event) =>
                    setStagedProfile(event.target.value)
                  }
                >
                  {renditionOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </Select>
                <Button
                  className="px-3 py-2 text-xs"
                  disabled={!canApplyRendition}
                  onClick={() => void applyRendition()}
                >
                  Apply to scene
                </Button>
              </div>
              <p className="text-xs text-[#91a8c9]">
                {hasRenditionChange
                  ? `Apply to scene will reconfigure the worker to publish ${selectedRendition?.label ?? stagedProfile}.`
                  : "Current worker rendition. Changes are staged until applied to the scene."}
              </p>
              {updateCamera.isError ? (
                <p className="text-xs text-[#ff9fb5]">
                  Could not apply rendition. Try again from this scene.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
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

function getAvailableRenditionOptions(
  camera: CameraResponse,
): LiveRenditionOption[] {
  const profiles = camera.browser_delivery?.profiles ?? [];
  return profiles.flatMap((profile) => {
    const id = readProfileId(profile);
    if (typeof id !== "string" || id.length === 0) {
      return [];
    }
    if (
      id === "native" &&
      camera.browser_delivery?.native_status?.available === false
    ) {
      return [];
    }

    return [
      {
        id,
        label: readProfileLabel(profile) ?? formatProfileId(id, camera),
        description: readProfileDescription(profile),
      },
    ];
  });
}

function readProfileId(profile: BrowserDeliveryProfile): unknown {
  return profile["id"];
}

function readProfileLabel(profile: BrowserDeliveryProfile): string | null {
  const label = profile["label"];
  return typeof label === "string" && label.length > 0 ? label : null;
}

function readProfileDescription(profile: BrowserDeliveryProfile): string | null {
  const description = profile["description"];
  return typeof description === "string" && description.length > 0
    ? description
    : null;
}

function formatProfileId(
  profileId: string,
  camera: CameraResponse,
): string {
  if (profileId === "native" || profileId === "annotated") {
    return formatDeliveryProfile({
      ...camera,
      browser_delivery: {
        ...camera.browser_delivery,
        default_profile: profileId,
      },
    });
  }

  const match = /^(\d+p)(\d+)$/.exec(profileId);
  return match ? `${match[1]} / ${match[2]} fps` : profileId;
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
