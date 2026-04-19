import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { useCameras } from "@/hooks/use-cameras";
import { type Incident, useIncidents } from "@/hooks/use-incidents";

export function IncidentsPage() {
  const { data: cameras = [] } = useCameras();
  const cameraNamesById = useMemo(
    () => new Map(cameras.map((camera) => [camera.id, camera.name])),
    [cameras],
  );
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const { data: incidents = [], isLoading, error } = useIncidents({
    cameraId: selectedCameraId,
    incidentType: selectedType,
    limit: 50,
  });

  const incidentTypes = useMemo(
    () => Array.from(new Set(incidents.map((incident) => incident.type))).sort(),
    [incidents],
  );

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(62,115,255,0.14),transparent_34%),linear-gradient(180deg,rgba(13,18,29,0.98),rgba(5,8,14,0.96))] shadow-[0_36px_100px_-62px_rgba(53,107,255,0.42)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
                Incidents
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Recent incident evidence with signed previews ready for review.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                Operators can pivot from the live wall into a filtered incident queue
                without losing camera context or waiting for heavy forensic reshaping.
              </p>
            </div>

            <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
              {incidents.length} incidents
            </Badge>
          </div>
        </div>

        <div className="grid gap-5 border-b border-white/8 px-6 py-5 md:grid-cols-2">
          <label className="space-y-2 text-sm text-[#d9e5f7]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
              Camera filter
            </span>
            <Select
              aria-label="Camera filter"
              value={selectedCameraId ?? ""}
              onChange={(event) =>
                setSelectedCameraId(event.target.value.length > 0 ? event.target.value : null)
              }
            >
              <option value="">All cameras</option>
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name}
                </option>
              ))}
            </Select>
          </label>

          <label className="space-y-2 text-sm text-[#d9e5f7]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
              Incident type
            </span>
            <Select
              aria-label="Incident type"
              value={selectedType ?? ""}
              onChange={(event) =>
                setSelectedType(event.target.value.length > 0 ? event.target.value : null)
              }
            >
              <option value="">All types</option>
              {incidentTypes.map((incidentType) => (
                <option key={incidentType} value={incidentType}>
                  {incidentType}
                </option>
              ))}
            </Select>
          </label>
        </div>

        <div className="space-y-4 px-6 py-6">
          {isLoading ? (
            <div className="text-sm text-[#93a7c5]">Loading incidents…</div>
          ) : error ? (
            <div className="text-sm text-[#f0b7c1]">
              {error instanceof Error ? error.message : "Failed to load incidents."}
            </div>
          ) : incidents.length === 0 ? (
            <div className="text-sm text-[#93a7c5]">
              No incidents matched the current camera and type filters.
            </div>
          ) : (
            incidents.map((incident) => (
              <IncidentCard
                key={incident.id}
                incident={incident}
                cameraName={incident.camera_name ?? cameraNamesById.get(incident.camera_id) ?? null}
              />
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function IncidentCard({
  incident,
  cameraName,
}: {
  incident: Incident;
  cameraName: string | null;
}) {
  const clipStorageLabel =
    incident.storage_bytes > 0
      ? `${(incident.storage_bytes / (1024 * 1024)).toFixed(1)} MB secured`
      : null;

  return (
    <article className="grid gap-5 rounded-[1.8rem] border border-white/10 bg-[linear-gradient(180deg,rgba(8,13,22,0.98),rgba(4,7,12,0.96))] p-4 md:grid-cols-[280px_minmax(0,1fr)]">
      <div className="overflow-hidden rounded-[1.3rem] border border-white/8 bg-[#04070c]">
        {incident.snapshot_url ? (
          <img
            src={incident.snapshot_url}
            alt={`Incident preview for ${cameraName ?? "camera"}`}
            className="aspect-video h-full w-full object-cover"
          />
        ) : (
          <div className="flex aspect-video items-center justify-center text-sm text-[#6f84a6]">
            No snapshot available
          </div>
        )}
      </div>

      <div className="flex min-w-0 flex-col gap-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="border-[#29436f] bg-[#08111d]/80 text-[#d7e4ff]">
                {incident.type}
              </Badge>
              <span className="text-sm text-[#8ea8cf]">
                {cameraName ?? incident.camera_id}
              </span>
            </div>
            <h3 className="mt-3 text-xl font-semibold text-[#eef4ff]">
              {cameraName ?? "Unassigned camera"}
            </h3>
            <p className="mt-2 text-sm text-[#8ea8cf]">
              {new Date(incident.ts).toLocaleString("en-GB", {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </p>
          </div>

          <div className="flex flex-col items-start gap-2">
            {incident.clip_url ? (
              <a
                href={incident.clip_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center rounded-full border border-[#33528a] bg-[#08111d]/85 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-[#dce8ff] transition hover:border-[#5c7dd0] hover:text-white"
              >
                Open clip
              </a>
            ) : (
              <Badge className="border-[#2d3748] bg-[#0b1018] text-[#9cb0cf]">
                Clip unavailable
              </Badge>
            )}

            {clipStorageLabel ? (
              <span className="text-xs text-[#7e95ba]">{clipStorageLabel}</span>
            ) : null}
          </div>
        </div>

        <dl className="grid gap-3 sm:grid-cols-2">
          {Object.entries(incident.payload).map(([key, value]) => (
            <div
              key={key}
              className="rounded-[1.1rem] border border-white/8 bg-white/[0.03] px-4 py-3"
            >
              <dt className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6f84a6]">
                {key}
              </dt>
              <dd className="mt-2 text-sm text-[#d8e2f2]">{String(value)}</dd>
            </div>
          ))}
        </dl>
      </div>
    </article>
  );
}
