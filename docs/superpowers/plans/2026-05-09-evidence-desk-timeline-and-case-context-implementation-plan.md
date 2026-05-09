# Evidence Desk Timeline And Case Context Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frontend-only Evidence Timeline, Case Context Strip, and polished evidence queue so Evidence Desk reads as a case review surface.

**Architecture:** Create a pure `evidence-signals` utility that derives tones, completeness, summary totals, and timeline buckets from the current incident result set. Render that model through focused Evidence components, then integrate them into `IncidentsPage` without changing backend APIs or review mutation behavior.

**Tech Stack:** React 19, Vite 6, TypeScript 5.7, Tailwind v4, Vitest, React Testing Library, existing workspace surface primitives.

**Spec source:** `/Users/yann.moren/vision/docs/superpowers/specs/2026-05-09-evidence-desk-timeline-and-case-context-design.md`

---

## Execution Protocol

The user prefers one implementation task at a time. Execute one task, run its verification, commit it, report the result, then wait for the next `go`.

Do not stage unrelated untracked scratch files. Current known unrelated untracked files include `.claude/`, `.codex/`, `.superpowers/brainstorm/*`, screenshot files, `camera-capture.md`, `codex-review-findings.md`, `docs/brand/2d_logo.png`, `docs/brand/3d_logo.png`, and `docs/strategy/`.

## Pre-flight

```bash
cd /Users/yann.moren/vision
git status --short
git rev-parse --abbrev-ref HEAD
corepack pnpm --dir frontend test
corepack pnpm --dir frontend lint
corepack pnpm --dir frontend build
```

Expected:

- branch is `codex/omnisight-ui-spec-implementation` unless the user starts a new branch first
- frontend tests, lint, and build pass or show only already-known warnings
- no unrelated scratch files are staged

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `frontend/src/lib/evidence-signals.ts` | create | pure evidence tones, completeness, timeline buckets, summary totals |
| `frontend/src/lib/evidence-signals.test.ts` | create | utility tests |
| `frontend/src/components/evidence/EvidenceTimeline.tsx` | create | timeline density strip and bucket selection |
| `frontend/src/components/evidence/EvidenceTimeline.test.tsx` | create | timeline rendering and interaction tests |
| `frontend/src/components/evidence/CaseContextStrip.tsx` | create | selected case trigger/evidence/review/retention context |
| `frontend/src/components/evidence/CaseContextStrip.test.tsx` | create | context strip tests |
| `frontend/src/components/evidence/EvidenceQueue.tsx` | create | extracted and polished review queue |
| `frontend/src/components/evidence/EvidenceQueue.test.tsx` | create | queue row tone, completeness, and selection tests |
| `frontend/src/pages/Incidents.tsx` | modify | integrate summary, timeline, queue, and case context |
| `frontend/src/pages/Incidents.test.tsx` | modify | integration coverage for timeline and context |
| `frontend/CHANGELOG.md` | modify | document Evidence Desk polish |

---

## Task 1: Evidence Signal Model

**Files:**
- Create: `frontend/src/lib/evidence-signals.ts`
- Create: `frontend/src/lib/evidence-signals.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/evidence-signals.test.ts`:

```ts
import { describe, expect, test } from "vitest";

import {
  buildEvidenceSummary,
  evidenceCompleteness,
  evidenceToneForType,
  formatEvidenceBucketLabel,
  newestIncidentInBucket,
} from "@/lib/evidence-signals";
import type { Incident } from "@/hooks/use-incidents";

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false, severity: "high" },
    snapshot_url: null,
    clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    storage_bytes: 2_097_152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}

describe("evidence signals", () => {
  test("derives evidence completeness labels", () => {
    expect(evidenceCompleteness(incident()).label).toBe("Clip only");
    expect(
      evidenceCompleteness(
        incident({ snapshot_url: "https://minio.local/snap.jpg" }),
      ).label,
    ).toBe("Snapshot and clip");
    expect(
      evidenceCompleteness(
        incident({ clip_url: null, snapshot_url: "https://minio.local/snap.jpg" }),
      ).label,
    ).toBe("Snapshot only");
    expect(
      evidenceCompleteness(incident({ clip_url: null, snapshot_url: null })).label,
    ).toBe("Metadata only");
  });

  test("maps incident types to deterministic product tones", () => {
    expect(evidenceToneForType("ppe-missing").family).toBe("safety");
    expect(evidenceToneForType("forklift-zone-entry").family).toBe("vehicle");
    expect(evidenceToneForType("perimeter-violation").family).toBe("alert");
    expect(evidenceToneForType("occupancy").family).toBe("human");
    expect(evidenceToneForType("custom-model-signal").family).toBe("other");
    expect(evidenceToneForType("custom-model-signal")).toEqual(
      evidenceToneForType("custom-model-signal"),
    );
  });

  test("builds summary totals, type rows, and selected bucket", () => {
    const selected = incident({
      id: "selected",
      ts: "2026-04-18T10:20:00Z",
      type: "ppe-missing",
      review_status: "pending",
    });
    const reviewed = incident({
      id: "reviewed",
      ts: "2026-04-18T10:50:00Z",
      type: "forklift-zone-entry",
      review_status: "reviewed",
      reviewed_at: "2026-04-18T11:00:00Z",
      reviewed_by_subject: "analyst-1",
      storage_bytes: 1_048_576,
    });

    const summary = buildEvidenceSummary([selected, reviewed], "selected", 4);

    expect(summary.total).toBe(2);
    expect(summary.pending).toBe(1);
    expect(summary.reviewed).toBe(1);
    expect(summary.storageBytes).toBe(3_145_728);
    expect(summary.typeRows.map((row) => [row.type, row.count])).toEqual([
      ["forklift-zone-entry", 1],
      ["ppe-missing", 1],
    ]);
    expect(summary.buckets.some((bucket) => bucket.selected)).toBe(true);
  });

  test("handles empty and single-timestamp timeline inputs", () => {
    expect(buildEvidenceSummary([], null, 4).buckets).toEqual([]);

    const summary = buildEvidenceSummary(
      [
        incident({ id: "a", ts: "2026-04-18T10:15:00Z" }),
        incident({ id: "b", ts: "2026-04-18T10:15:00Z", review_status: "reviewed" }),
      ],
      "a",
      4,
    );

    expect(summary.buckets).toHaveLength(1);
    expect(summary.buckets[0]).toMatchObject({
      total: 2,
      pending: 1,
      reviewed: 1,
      selected: true,
    });
  });

  test("selects the newest incident from a bucket", () => {
    const summary = buildEvidenceSummary(
      [
        incident({ id: "old", ts: "2026-04-18T10:00:00Z" }),
        incident({ id: "new", ts: "2026-04-18T10:30:00Z" }),
      ],
      null,
      1,
    );

    expect(newestIncidentInBucket(summary.buckets[0])?.id).toBe("new");
    expect(formatEvidenceBucketLabel(summary.buckets[0])).toContain("2 records");
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/evidence-signals.test.ts
```

Expected: FAIL because `@/lib/evidence-signals` does not exist.

- [ ] **Step 3: Implement the utility**

Create `frontend/src/lib/evidence-signals.ts`:

```ts
import type { Incident } from "@/hooks/use-incidents";

export type EvidenceToneFamily = "human" | "vehicle" | "safety" | "alert" | "other";

export type EvidenceTone = {
  family: EvidenceToneFamily;
  stroke: string;
  fill: string;
  text: string;
};

export type EvidenceCompleteness = {
  key: "snapshot-clip" | "clip-only" | "snapshot-only" | "metadata-only";
  label: string;
  detail: string;
  tone: "healthy" | "attention" | "muted";
};

export type EvidenceTypeRow = {
  type: string;
  count: number;
  pending: number;
  reviewed: number;
  tone: EvidenceTone;
};

export type EvidenceTimelineBucket = {
  id: string;
  index: number;
  startMs: number;
  endMs: number;
  label: string;
  total: number;
  pending: number;
  reviewed: number;
  selected: boolean;
  dominantType: string | null;
  tone: EvidenceTone;
  incidents: Incident[];
};

export type EvidenceSummary = {
  total: number;
  pending: number;
  reviewed: number;
  storageBytes: number;
  typeRows: EvidenceTypeRow[];
  buckets: EvidenceTimelineBucket[];
};

const HUMAN = ["person", "people", "occupancy", "queue", "worker"];
const VEHICLE = ["vehicle", "car", "truck", "forklift", "parking", "bus", "bike"];
const SAFETY = ["ppe", "helmet", "vest", "hard_hat", "hard-hat", "safety"];
const ALERT = ["zone", "access", "perimeter", "violation", "intrusion", "entry"];

const OTHER_TONES: EvidenceTone[] = [
  { family: "other", stroke: "#76e0ff", fill: "rgba(118,224,255,0.16)", text: "#c9f6ff" },
  { family: "other", stroke: "#c7b8ff", fill: "rgba(199,184,255,0.16)", text: "#eee8ff" },
];

const FAMILY_TONES: Record<Exclude<EvidenceToneFamily, "other">, EvidenceTone> = {
  human: { family: "human", stroke: "#61e6a6", fill: "rgba(97,230,166,0.16)", text: "#c9ffe1" },
  vehicle: { family: "vehicle", stroke: "#62a6ff", fill: "rgba(98,166,255,0.16)", text: "#dbeaff" },
  safety: { family: "safety", stroke: "#f7c56b", fill: "rgba(247,197,107,0.16)", text: "#ffe8b8" },
  alert: { family: "alert", stroke: "#ff6f9d", fill: "rgba(255,111,157,0.16)", text: "#ffd4e1" },
};

export function evidenceToneForType(type: string): EvidenceTone {
  const normalized = type.toLowerCase();
  if (HUMAN.some((token) => normalized.includes(token))) return FAMILY_TONES.human;
  if (VEHICLE.some((token) => normalized.includes(token))) return FAMILY_TONES.vehicle;
  if (SAFETY.some((token) => normalized.includes(token))) return FAMILY_TONES.safety;
  if (ALERT.some((token) => normalized.includes(token))) return FAMILY_TONES.alert;
  return OTHER_TONES[hashString(normalized) % OTHER_TONES.length];
}

export function evidenceCompleteness(incident: Incident): EvidenceCompleteness {
  const hasSnapshot = Boolean(incident.snapshot_url);
  const hasClip = Boolean(incident.clip_url);

  if (hasSnapshot && hasClip) {
    return {
      key: "snapshot-clip",
      label: "Snapshot and clip",
      detail: "Still image and clip secured",
      tone: "healthy",
    };
  }
  if (hasClip) {
    return {
      key: "clip-only",
      label: "Clip only",
      detail: "Clip secured without still snapshot",
      tone: "attention",
    };
  }
  if (hasSnapshot) {
    return {
      key: "snapshot-only",
      label: "Snapshot only",
      detail: "Still image secured without clip",
      tone: "attention",
    };
  }
  return {
    key: "metadata-only",
    label: "Metadata only",
    detail: "Event metadata secured without media",
    tone: "muted",
  };
}

export function buildEvidenceSummary(
  incidents: Incident[],
  selectedIncidentId: string | null,
  bucketCount = 12,
): EvidenceSummary {
  const sorted = [...incidents].sort((left, right) => dateMs(left.ts) - dateMs(right.ts));
  const typeRows = buildTypeRows(sorted);
  const storageBytes = sorted.reduce((total, incident) => total + incident.storage_bytes, 0);
  const pending = sorted.filter((incident) => incident.review_status === "pending").length;
  const reviewed = sorted.length - pending;

  return {
    total: sorted.length,
    pending,
    reviewed,
    storageBytes,
    typeRows,
    buckets: buildBuckets(sorted, selectedIncidentId, bucketCount),
  };
}

export function newestIncidentInBucket(bucket: EvidenceTimelineBucket): Incident | null {
  return [...bucket.incidents].sort((left, right) => dateMs(right.ts) - dateMs(left.ts))[0] ?? null;
}

export function formatEvidenceBucketLabel(bucket: EvidenceTimelineBucket): string {
  const noun = bucket.total === 1 ? "record" : "records";
  return `${bucket.label}, ${bucket.total} ${noun}, ${bucket.pending} pending`;
}

function buildTypeRows(incidents: Incident[]): EvidenceTypeRow[] {
  const rows = new Map<string, EvidenceTypeRow>();
  for (const incident of incidents) {
    const current = rows.get(incident.type);
    rows.set(incident.type, {
      type: incident.type,
      count: (current?.count ?? 0) + 1,
      pending: (current?.pending ?? 0) + (incident.review_status === "pending" ? 1 : 0),
      reviewed: (current?.reviewed ?? 0) + (incident.review_status === "reviewed" ? 1 : 0),
      tone: evidenceToneForType(incident.type),
    });
  }

  return Array.from(rows.values()).sort(
    (left, right) => right.count - left.count || left.type.localeCompare(right.type),
  );
}

function buildBuckets(
  incidents: Incident[],
  selectedIncidentId: string | null,
  bucketCount: number,
): EvidenceTimelineBucket[] {
  if (incidents.length === 0) return [];

  const minMs = Math.min(...incidents.map((incident) => dateMs(incident.ts)));
  const maxMs = Math.max(...incidents.map((incident) => dateMs(incident.ts)));
  if (minMs === maxMs) {
    return [bucketFromIncidents(0, minMs, maxMs, incidents, selectedIncidentId)];
  }

  const safeCount = Math.max(1, Math.min(bucketCount, incidents.length, 12));
  const widthMs = Math.max(1, Math.ceil((maxMs - minMs + 1) / safeCount));
  const buckets = Array.from({ length: safeCount }, (_, index) => {
    const startMs = minMs + index * widthMs;
    const endMs = index === safeCount - 1 ? maxMs : startMs + widthMs - 1;
    return bucketFromIncidents(index, startMs, endMs, [], selectedIncidentId);
  });

  for (const incident of incidents) {
    const index = Math.min(
      safeCount - 1,
      Math.max(0, Math.floor((dateMs(incident.ts) - minMs) / widthMs)),
    );
    buckets[index].incidents.push(incident);
  }

  return buckets
    .filter((bucket) => bucket.incidents.length > 0)
    .map((bucket) =>
      bucketFromIncidents(
        bucket.index,
        bucket.startMs,
        bucket.endMs,
        bucket.incidents,
        selectedIncidentId,
      ),
    );
}

function bucketFromIncidents(
  index: number,
  startMs: number,
  endMs: number,
  incidents: Incident[],
  selectedIncidentId: string | null,
): EvidenceTimelineBucket {
  const pending = incidents.filter((incident) => incident.review_status === "pending").length;
  const reviewed = incidents.length - pending;
  const dominantType = dominantIncidentType(incidents);
  return {
    id: `${startMs}-${endMs}-${index}`,
    index,
    startMs,
    endMs,
    label: formatBucketTime(startMs),
    total: incidents.length,
    pending,
    reviewed,
    selected: selectedIncidentId
      ? incidents.some((incident) => incident.id === selectedIncidentId)
      : false,
    dominantType,
    tone: evidenceToneForType(dominantType ?? "evidence"),
    incidents,
  };
}

function dominantIncidentType(incidents: Incident[]) {
  const counts = new Map<string, number>();
  for (const incident of incidents) {
    counts.set(incident.type, (counts.get(incident.type) ?? 0) + 1);
  }
  return Array.from(counts.entries()).sort(
    (left, right) => right[1] - left[1] || left[0].localeCompare(right[0]),
  )[0]?.[0] ?? null;
}

function formatBucketTime(ms: number) {
  return new Date(ms).toLocaleString("en-GB", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function dateMs(value: string) {
  return new Date(value).getTime();
}

function hashString(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}
```

- [ ] **Step 4: Run utility tests**

```bash
corepack pnpm --dir frontend exec vitest run src/lib/evidence-signals.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit Task 1**

```bash
git add frontend/src/lib/evidence-signals.ts frontend/src/lib/evidence-signals.test.ts
git commit -m "feat(evidence): add evidence signal model"
```

---

## Task 2: Evidence Timeline Component

**Files:**
- Create: `frontend/src/components/evidence/EvidenceTimeline.tsx`
- Create: `frontend/src/components/evidence/EvidenceTimeline.test.tsx`

- [ ] **Step 1: Write the failing component tests**

Create `frontend/src/components/evidence/EvidenceTimeline.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { EvidenceTimeline } from "@/components/evidence/EvidenceTimeline";
import { buildEvidenceSummary } from "@/lib/evidence-signals";
import type { Incident } from "@/hooks/use-incidents";

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false },
    snapshot_url: null,
    clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    storage_bytes: 2_097_152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}

describe("EvidenceTimeline", () => {
  test("renders timeline buckets and summary counts", () => {
    const summary = buildEvidenceSummary(
      [
        incident({ id: "a", ts: "2026-04-18T10:00:00Z" }),
        incident({ id: "b", ts: "2026-04-18T11:00:00Z", review_status: "reviewed" }),
      ],
      "a",
      4,
    );

    render(<EvidenceTimeline summary={summary} onSelectIncident={vi.fn()} />);

    expect(screen.getByRole("region", { name: /evidence timeline/i })).toBeInTheDocument();
    expect(screen.getByText("2 records")).toBeInTheDocument();
    expect(screen.getByText("1 pending")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /select evidence bucket/i })).toHaveLength(2);
  });

  test("selects newest incident when a bucket is clicked", async () => {
    const user = userEvent.setup();
    const onSelectIncident = vi.fn();
    const summary = buildEvidenceSummary(
      [
        incident({ id: "old", ts: "2026-04-18T10:00:00Z" }),
        incident({ id: "new", ts: "2026-04-18T10:30:00Z" }),
      ],
      null,
      1,
    );

    render(<EvidenceTimeline summary={summary} onSelectIncident={onSelectIncident} />);

    await user.click(screen.getByRole("button", { name: /select evidence bucket/i }));

    expect(onSelectIncident).toHaveBeenCalledWith("new");
  });

  test("renders a stable empty state", () => {
    render(
      <EvidenceTimeline
        summary={buildEvidenceSummary([], null)}
        onSelectIncident={vi.fn()}
      />,
    );

    expect(screen.getByText(/no evidence in the current result set/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/evidence/EvidenceTimeline.test.tsx
```

Expected: FAIL because `EvidenceTimeline` does not exist.

- [ ] **Step 3: Implement `EvidenceTimeline`**

Create `frontend/src/components/evidence/EvidenceTimeline.tsx`:

```tsx
import type { EvidenceSummary } from "@/lib/evidence-signals";
import {
  formatEvidenceBucketLabel,
  newestIncidentInBucket,
} from "@/lib/evidence-signals";

type EvidenceTimelineProps = {
  summary: EvidenceSummary;
  onSelectIncident: (incidentId: string) => void;
};

export function EvidenceTimeline({
  summary,
  onSelectIncident,
}: EvidenceTimelineProps) {
  const maxTotal = Math.max(1, ...summary.buckets.map((bucket) => bucket.total));

  return (
    <section
      aria-label="Evidence timeline"
      data-testid="evidence-timeline"
      className="rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[linear-gradient(180deg,rgba(14,19,28,0.94),rgba(8,12,18,0.96))] px-4 py-4 shadow-[var(--vz-elev-1)]"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--vz-text-muted)]">
            Evidence timeline
          </p>
          <p className="mt-1 text-sm text-[var(--vz-text-secondary)]">
            {summary.total} {summary.total === 1 ? "record" : "records"}{" "}
            / {summary.pending} pending / {summary.reviewed} reviewed
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-[11px] font-semibold uppercase tracking-[0.14em]">
          {summary.typeRows.slice(0, 3).map((row) => (
            <span
              key={row.type}
              className="rounded-full border px-2.5 py-1"
              style={{
                borderColor: row.tone.stroke,
                backgroundColor: row.tone.fill,
                color: row.tone.text,
              }}
            >
              {row.type} {row.count}
            </span>
          ))}
        </div>
      </div>

      {summary.buckets.length === 0 ? (
        <div className="mt-4 flex h-24 items-center rounded-[var(--vz-r-md)] border border-dashed border-[color:var(--vz-hair-strong)] px-4 text-sm text-[var(--vz-text-muted)]">
          No evidence in the current result set.
        </div>
      ) : (
        <div className="mt-4 grid h-28 grid-flow-col items-end gap-2 overflow-x-auto pb-1">
          {summary.buckets.map((bucket) => {
            const newest = newestIncidentInBucket(bucket);
            const height = 28 + Math.round((bucket.total / maxTotal) * 56);
            const pendingHeight =
              bucket.total > 0 ? Math.round((bucket.pending / bucket.total) * height) : 0;
            const reviewedHeight = Math.max(0, height - pendingHeight);

            return (
              <button
                key={bucket.id}
                type="button"
                aria-label={`Select evidence bucket ${formatEvidenceBucketLabel(bucket)}`}
                onClick={() => {
                  if (newest) onSelectIncident(newest.id);
                }}
                className={`group flex min-w-[4.5rem] flex-col items-center justify-end gap-2 rounded-[var(--vz-r-md)] border px-2 py-2 text-left transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--vz-hair-focus)] ${
                  bucket.selected
                    ? "border-[color:var(--vz-hair-focus)] bg-white/[0.055] shadow-[var(--vz-elev-glow-cerulean)]"
                    : "border-transparent bg-white/[0.025] hover:border-[color:var(--vz-hair-strong)] hover:bg-white/[0.04]"
                }`}
              >
                <span className="flex w-full items-end justify-center">
                  <span
                    className="flex w-full max-w-10 flex-col justify-end overflow-hidden rounded-t-[0.65rem] rounded-b-sm border border-white/10 bg-black/20"
                    style={{ height }}
                    aria-hidden="true"
                  >
                    <span
                      className="block w-full"
                      style={{
                        height: reviewedHeight,
                        backgroundColor: "rgba(132,151,179,0.42)",
                      }}
                    />
                    <span
                      className="block w-full"
                      style={{
                        height: pendingHeight,
                        background: `linear-gradient(180deg, ${bucket.tone.stroke}, ${bucket.tone.fill})`,
                      }}
                    />
                  </span>
                </span>
                <span className="max-w-[4rem] truncate text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--vz-text-muted)]">
                  {bucket.label}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 4: Run timeline tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/evidence/EvidenceTimeline.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit Task 2**

```bash
git add frontend/src/components/evidence/EvidenceTimeline.tsx frontend/src/components/evidence/EvidenceTimeline.test.tsx
git commit -m "feat(evidence): add evidence timeline"
```

---

## Task 3: Case Context Strip

**Files:**
- Create: `frontend/src/components/evidence/CaseContextStrip.tsx`
- Create: `frontend/src/components/evidence/CaseContextStrip.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/components/evidence/CaseContextStrip.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";

import { CaseContextStrip } from "@/components/evidence/CaseContextStrip";
import type { Incident } from "@/hooks/use-incidents";

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false },
    snapshot_url: null,
    clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    storage_bytes: 2_097_152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}

describe("CaseContextStrip", () => {
  test("renders trigger evidence review and retention cells", () => {
    render(<CaseContextStrip incident={incident()} storageLabel="2.0 MB secured" />);

    expect(screen.getByText("Case context")).toBeInTheDocument();
    expect(screen.getByText("Trigger")).toBeInTheDocument();
    expect(screen.getByText("ppe-missing")).toBeInTheDocument();
    expect(screen.getByText("Evidence")).toBeInTheDocument();
    expect(screen.getByText("Clip only")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Pending review")).toBeInTheDocument();
    expect(screen.getByText("Retention")).toBeInTheDocument();
    expect(screen.getByText("2.0 MB secured")).toBeInTheDocument();
  });

  test("shows reviewed actor and time when present", () => {
    render(
      <CaseContextStrip
        incident={incident({
          review_status: "reviewed",
          reviewed_at: "2026-04-18T11:00:00Z",
          reviewed_by_subject: "analyst-1",
        })}
        storageLabel="2.0 MB secured"
      />,
    );

    expect(screen.getByText("Reviewed")).toBeInTheDocument();
    expect(screen.getByText(/analyst-1/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/evidence/CaseContextStrip.test.tsx
```

Expected: FAIL because `CaseContextStrip` does not exist.

- [ ] **Step 3: Implement `CaseContextStrip`**

Create `frontend/src/components/evidence/CaseContextStrip.tsx`:

```tsx
import type { Incident } from "@/hooks/use-incidents";
import { evidenceCompleteness, evidenceToneForType } from "@/lib/evidence-signals";

type CaseContextStripProps = {
  incident: Incident;
  storageLabel: string;
};

export function CaseContextStrip({ incident, storageLabel }: CaseContextStripProps) {
  const tone = evidenceToneForType(incident.type);
  const completeness = evidenceCompleteness(incident);
  const reviewLabel =
    incident.review_status === "pending" ? "Pending review" : "Reviewed";
  const reviewDetail =
    incident.review_status === "reviewed"
      ? [incident.reviewed_by_subject ?? "Unknown reviewer", incident.reviewed_at]
          .filter(Boolean)
          .join(" / ")
      : "Awaiting operator decision";

  return (
    <div
      aria-label="Case context"
      className="border-b border-white/8 bg-[linear-gradient(180deg,rgba(255,255,255,0.035),rgba(255,255,255,0.015))] px-5 py-4"
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--vz-text-muted)]">
        Case context
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <ContextCell
          label="Trigger"
          value={incident.type}
          detail="Scene event"
          accent={tone.stroke}
        />
        <ContextCell
          label="Evidence"
          value={completeness.label}
          detail={completeness.detail}
          accent={tone.stroke}
        />
        <ContextCell
          label="Review"
          value={reviewLabel}
          detail={reviewDetail}
          accent={
            incident.review_status === "pending"
              ? "var(--vz-state-attention)"
              : "var(--vz-state-healthy)"
          }
        />
        <ContextCell
          label="Retention"
          value={storageLabel}
          detail="Secured evidence"
          accent="var(--vz-lens-cerulean)"
        />
      </div>
    </div>
  );
}

function ContextCell({
  label,
  value,
  detail,
  accent,
}: {
  label: string;
  value: string;
  detail: string;
  accent: string;
}) {
  return (
    <div className="min-w-0 rounded-[var(--vz-r-md)] border border-white/8 bg-black/20 px-3 py-3">
      <div className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="h-2 w-2 rounded-full"
          style={{ backgroundColor: accent }}
        />
        <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[var(--vz-text-muted)]">
          {label}
        </span>
      </div>
      <p className="mt-2 truncate text-sm font-semibold text-[var(--vz-text-primary)]">
        {value}
      </p>
      <p className="mt-1 truncate text-xs text-[var(--vz-text-muted)]">
        {detail}
      </p>
    </div>
  );
}
```

- [ ] **Step 4: Run context tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/evidence/CaseContextStrip.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit Task 3**

```bash
git add frontend/src/components/evidence/CaseContextStrip.tsx frontend/src/components/evidence/CaseContextStrip.test.tsx
git commit -m "feat(evidence): add case context strip"
```

---

## Task 4: Evidence Queue Extraction And Polish

**Files:**
- Create: `frontend/src/components/evidence/EvidenceQueue.tsx`
- Create: `frontend/src/components/evidence/EvidenceQueue.test.tsx`
- Task 5 integrates this component into `frontend/src/pages/Incidents.tsx`

- [ ] **Step 1: Write the failing queue tests**

Create `frontend/src/components/evidence/EvidenceQueue.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { EvidenceQueue } from "@/components/evidence/EvidenceQueue";
import type { Incident } from "@/hooks/use-incidents";

function incident(overrides: Partial<Incident> = {}): Incident {
  return {
    id: "99999999-9999-9999-9999-999999999999",
    camera_id: "11111111-1111-1111-1111-111111111111",
    camera_name: "Forklift Gate",
    ts: "2026-04-18T10:15:00Z",
    type: "ppe-missing",
    payload: { hard_hat: false },
    snapshot_url: null,
    clip_url: "https://minio.local/signed/incidents/forklift-gate.mjpeg",
    storage_bytes: 2_097_152,
    review_status: "pending",
    reviewed_at: null,
    reviewed_by_subject: null,
    ...overrides,
  };
}

describe("EvidenceQueue", () => {
  test("renders polished evidence rows with completeness and status", () => {
    render(
      <EvidenceQueue
        incidents={[incident()]}
        selectedIncidentId="99999999-9999-9999-9999-999999999999"
        cameraNamesById={new Map()}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("complementary", { name: /review queue/i })).toBeInTheDocument();
    expect(screen.getByText("Forklift Gate")).toBeInTheDocument();
    expect(screen.getByText("ppe-missing")).toBeInTheDocument();
    expect(screen.getByText("Clip only")).toBeInTheDocument();
    expect(screen.getByText("pending")).toBeInTheDocument();
  });

  test("selects a row when clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <EvidenceQueue
        incidents={[incident({ id: "a" }), incident({ id: "b", camera_name: "Loading Dock" })]}
        selectedIncidentId="a"
        cameraNamesById={new Map()}
        onSelect={onSelect}
      />,
    );

    await user.click(screen.getByRole("button", { name: /loading dock/i }));

    expect(onSelect).toHaveBeenCalledWith("b");
  });
});
```

- [ ] **Step 2: Run the failing tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/evidence/EvidenceQueue.test.tsx
```

Expected: FAIL because `EvidenceQueue` does not exist.

- [ ] **Step 3: Implement `EvidenceQueue`**

Create `frontend/src/components/evidence/EvidenceQueue.tsx`:

```tsx
import { InstrumentRail } from "@/components/layout/workspace-surfaces";
import { omniLabels } from "@/copy/omnisight";
import type { Incident } from "@/hooks/use-incidents";
import { evidenceCompleteness, evidenceToneForType } from "@/lib/evidence-signals";

type EvidenceQueueProps = {
  incidents: Incident[];
  selectedIncidentId: string;
  cameraNamesById: Map<string, string>;
  onSelect: (incidentId: string) => void;
};

export function EvidenceQueue({
  incidents,
  selectedIncidentId,
  cameraNamesById,
  onSelect,
}: EvidenceQueueProps) {
  return (
    <InstrumentRail
      aria-label="Review Queue"
      data-testid="review-queue"
      className="min-w-0 overflow-hidden"
    >
      <div className="border-b border-white/8 px-4 py-3">
        <h3 className="text-lg font-semibold text-[#eef4ff]">
          {omniLabels.reviewQueueTitle}
        </h3>
      </div>

      <div className="divide-y divide-white/8">
        {incidents.map((incident) => {
          const selected = incident.id === selectedIncidentId;
          const cameraName = cameraNameFor(incident, cameraNamesById);
          const tone = evidenceToneForType(incident.type);
          const completeness = evidenceCompleteness(incident);

          return (
            <button
              key={incident.id}
              type="button"
              aria-pressed={selected}
              onClick={() => onSelect(incident.id)}
              className={`relative block w-full px-4 py-3 text-left transition ${
                selected
                  ? "bg-[linear-gradient(135deg,rgba(110,189,255,0.16),rgba(126,83,255,0.14))] text-white shadow-[inset_3px_0_0_rgba(118,224,255,0.72)]"
                  : "text-[#c5d3ea] hover:bg-white/[0.04]"
              }`}
            >
              <span
                aria-hidden="true"
                className="absolute left-0 top-3 bottom-3 w-1 rounded-r-full"
                style={{ backgroundColor: tone.stroke }}
              />
              <span className="block truncate pl-2 text-sm font-semibold">
                {cameraName}
              </span>
              <span className="mt-1 flex flex-wrap items-center gap-2 pl-2 text-xs text-[#8ea8cf]">
                <span style={{ color: tone.text }}>{incident.type}</span>
                <span>{formatIncidentTime(incident.ts)}</span>
              </span>
              <span className="mt-3 flex flex-wrap gap-2 pl-2">
                <span
                  className="rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em]"
                  style={{
                    borderColor: tone.stroke,
                    backgroundColor: tone.fill,
                    color: tone.text,
                  }}
                >
                  {completeness.label}
                </span>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#b7c8e4]">
                  {incident.review_status}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </InstrumentRail>
  );
}

function cameraNameFor(incident: Incident, cameraNamesById: Map<string, string>) {
  return incident.camera_name ?? cameraNamesById.get(incident.camera_id) ?? incident.camera_id;
}

function formatIncidentTime(timestamp: string) {
  return new Date(timestamp).toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
```

- [ ] **Step 4: Run queue tests**

```bash
corepack pnpm --dir frontend exec vitest run src/components/evidence/EvidenceQueue.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

```bash
git add frontend/src/components/evidence/EvidenceQueue.tsx frontend/src/components/evidence/EvidenceQueue.test.tsx
git commit -m "feat(evidence): polish review queue"
```

---

## Task 5: Evidence Desk Integration

**Files:**
- Modify: `frontend/src/pages/Incidents.tsx`
- Modify: `frontend/src/pages/Incidents.test.tsx`
- Modify: `frontend/CHANGELOG.md`

- [ ] **Step 1: Extend integration tests**

Modify `frontend/src/pages/Incidents.test.tsx`.

In the first test, change the incident response to include two incidents:

```ts
if (url.pathname === "/api/v1/incidents") {
  return Promise.resolve(
    jsonResponse([
      incidentPayload(),
      incidentPayload({
        id: "88888888-8888-8888-8888-888888888888",
        camera_name: "Loading Dock",
        ts: "2026-04-18T10:45:00Z",
        type: "forklift-zone-entry",
        review_status: "reviewed",
        reviewed_at: "2026-04-18T11:00:00Z",
        reviewed_by_subject: "analyst-1",
        snapshot_url: "https://minio.local/signed/incidents/loading-dock.jpg",
      }),
    ]),
  );
}
```

Add assertions after the existing desk assertions:

```ts
expect(screen.getByTestId("evidence-timeline")).toBeInTheDocument();
expect(screen.getByText("Evidence timeline")).toBeInTheDocument();
expect(screen.getByText("Case context")).toBeInTheDocument();
expect(screen.getByText("Clip only")).toBeInTheDocument();
```

Add a new test:

```ts
test("selecting an evidence timeline bucket changes selected evidence", async () => {
  const user = userEvent.setup();

  vi.spyOn(global, "fetch").mockImplementation((input, init) => {
    const request =
      input instanceof Request ? input : new Request(String(input), init);
    const url = new URL(request.url);

    if (url.pathname === "/api/v1/cameras") {
      return Promise.resolve(jsonResponse([cameraPayload()]));
    }

    if (url.pathname === "/api/v1/incidents") {
      return Promise.resolve(
        jsonResponse([
          incidentPayload({
            id: "old",
            camera_name: "Forklift Gate",
            ts: "2026-04-18T10:00:00Z",
          }),
          incidentPayload({
            id: "new",
            camera_name: "Loading Dock",
            ts: "2026-04-18T11:00:00Z",
            type: "forklift-zone-entry",
          }),
        ]),
      );
    }

    return Promise.resolve(new Response("Not found", { status: 404 }));
  });

  renderIncidentsPage();

  await screen.findByTestId("evidence-timeline");
  await user.click(screen.getAllByRole("button", { name: /select evidence bucket/i }).at(-1)!);

  const hero = await screen.findByRole("region", { name: /selected evidence/i });
  expect(within(hero).getByText(/loading dock/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: Run failing integration tests**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx
```

Expected: FAIL because `IncidentsPage` does not render timeline or case context yet.

- [ ] **Step 3: Integrate new components**

Modify imports in `frontend/src/pages/Incidents.tsx`:

```tsx
import { CaseContextStrip } from "@/components/evidence/CaseContextStrip";
import { EvidenceQueue } from "@/components/evidence/EvidenceQueue";
import { EvidenceTimeline } from "@/components/evidence/EvidenceTimeline";
import { buildEvidenceSummary } from "@/lib/evidence-signals";
```

Remove the old local `IncidentQueue` function after replacing its usage.

In `IncidentsPage`, add summary derivation:

```tsx
const evidenceSummary = useMemo(
  () => buildEvidenceSummary(incidents, selectedIncident?.id ?? null),
  [incidents, selectedIncident?.id],
);
```

Render the timeline after the filter bar and before loading/error/empty state:

```tsx
{!isLoading && !error ? (
  <EvidenceTimeline
    summary={evidenceSummary}
    onSelectIncident={setSelectedIncidentId}
  />
) : null}
```

Replace the old queue call:

```tsx
<EvidenceQueue
  incidents={incidents}
  selectedIncidentId={selectedIncident.id}
  cameraNamesById={cameraNamesById}
  onSelect={setSelectedIncidentId}
/>
```

Inside `IncidentEvidenceHero`, render the context strip after the header and before the media block:

```tsx
<CaseContextStrip
  incident={incident}
  storageLabel={storageLabel(incident.storage_bytes)}
/>
```

Update the media hero header copy so it does not duplicate all context strip information. Keep camera name and review badge.

- [ ] **Step 4: Polish facts rail payload disclosure**

In `IncidentFactsPanel`, replace the raw payload block with:

```tsx
<div className="border-t border-white/8 px-4 py-3">
  <details open={Object.keys(incident.payload).length <= 4}>
    <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
      Raw payload
    </summary>
    <dl className="mt-3 grid gap-3">
      {Object.entries(incident.payload).map(([key, value]) => (
        <FactRow key={key} label={key} value={String(value)} compact />
      ))}
    </dl>
  </details>
</div>
```

- [ ] **Step 5: Update changelog**

Add under `## Phase 5A - Operational Readiness UI`:

```md
- Added Evidence Desk polish plan: timeline density strip, case context, type-colored review queue, and cleaner raw payload disclosure.
```

- [ ] **Step 6: Run integration tests**

```bash
corepack pnpm --dir frontend exec vitest run src/pages/Incidents.test.tsx src/components/evidence/EvidenceTimeline.test.tsx src/components/evidence/CaseContextStrip.test.tsx src/components/evidence/EvidenceQueue.test.tsx src/lib/evidence-signals.test.ts
```

Expected: PASS.

- [ ] **Step 7: Commit Task 5**

```bash
git add frontend/src/pages/Incidents.tsx frontend/src/pages/Incidents.test.tsx frontend/CHANGELOG.md
git commit -m "feat(evidence): integrate timeline case context"
```

---

## Task 6: Final Verification And Visual QA

**Files:**
- No planned code changes.

- [ ] **Step 1: Run frontend unit tests**

```bash
corepack pnpm --dir frontend test
```

Expected: PASS.

- [ ] **Step 2: Run lint**

```bash
corepack pnpm --dir frontend lint
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

```bash
corepack pnpm --dir frontend build
```

Expected: PASS.

- [ ] **Step 4: Run browser visual QA**

Start or reuse the frontend dev server. Then verify `/incidents` at:

- 375px width
- 768px width
- 1440px width

Checklist:

- timeline remains above the desk grid
- bucket labels do not overlap
- selected timeline bucket, selected queue row, and hero context point to the same incident
- case context text fits in all cells
- raw payload disclosure is keyboard accessible
- no WebGL usage
- no nested card visual clutter

- [ ] **Step 5: Commit verification notes if code changed during QA**

If QA required code fixes:

```bash
git add frontend/src
git commit -m "fix(evidence): tighten evidence desk visual QA"
```

If no code fixes were needed, do not create an empty commit.

## Self-Review Checklist

- Spec coverage:
  - Evidence signal model: Task 1
  - Evidence timeline: Task 2 and Task 5
  - Case context strip: Task 3 and Task 5
  - Queue polish: Task 4 and Task 5
  - Facts rail payload disclosure: Task 5
  - Verification and visual QA: Task 6

- Scope:
  - Frontend-only.
  - No backend aggregation endpoint.
  - No generic BI chart surface.

- Type consistency:
  - `EvidenceSummary`, `EvidenceTimelineBucket`, and component props are defined in Task 1 and reused by the component tasks.
  - Timeline selection uses `onSelectIncident(incidentId)` consistently.
