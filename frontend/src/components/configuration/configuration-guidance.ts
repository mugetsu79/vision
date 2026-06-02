import type {
  FieldGuidance,
  SectionGuidance,
} from "@/components/guidance/guidance-types";
import type { OperatorConfigKind } from "@/hooks/use-configuration";

export const PROFILE_COMMON_FIELD_GUIDANCE: Record<string, FieldGuidance> = {
  kind: {
    label: "Configuration kind",
    hint: "Selects which runtime subsystem this profile controls.",
    details: [
      "Each kind has its own fields, validation rules, and binding consequences.",
      "Changing kind resets the editor to fields for that subsystem.",
    ],
  },
  name: {
    label: "Profile name",
    hint: "Operator-facing label shown in profile lists, bindings, and diagnostics.",
    details: ["Use a name that states the site, runtime, or policy intent."],
  },
  slug: {
    label: "Slug",
    hint: "Stable identifier for automation and API references.",
    details: ["Use lowercase words separated by hyphens so references stay readable."],
  },
};

export const PROFILE_KIND_GUIDANCE: Record<OperatorConfigKind, SectionGuidance> = {
  evidence_storage: {
    eyebrow: "Evidence",
    title: "Choose where incident evidence is written",
    summary:
      "Evidence storage profiles decide whether event clips and snapshots write locally, centrally, to object storage, or through a local-first path.",
    commonMistakes: [
      "Selecting cloud storage without bucket credentials.",
      "Choosing a storage scope that conflicts with the privacy residency policy.",
      "Expecting this profile to enable continuous recording; camera recording policy controls event clips.",
    ],
  },
  stream_delivery: {
    eyebrow: "Live transport",
    title: "Choose how browsers reach live streams",
    summary:
      "Transport profiles control the stream route. Camera live rendition controls clean, annotated, or reduced video quality.",
    commonMistakes: [
      "Using localhost in a public base URL when operators connect from another machine.",
      "Selecting WebRTC when UDP 8189 is blocked.",
      "Expecting transport profile to change resolution or FPS.",
    ],
  },
  runtime_selection: {
    eyebrow: "Inference runtime",
    title: "Rank model runtimes and fallback behavior",
    summary:
      "Runtime selection profiles tell workers which backend and artifact family to prefer before starting inference.",
    commonMistakes: [
      "Disabling fallback before a valid TensorRT artifact exists.",
      "Choosing TensorRT-first on hardware with no compatible engine.",
      "Expecting runtime selection to change detector classes.",
    ],
  },
  privacy_policy: {
    eyebrow: "Privacy and retention",
    title: "Set residency, retention, and sensitive text posture",
    summary:
      "Privacy policies protect evidence lifecycle and decide where sensitive outputs may live.",
    commonMistakes: [
      "Using cloud residency for an edge-only privacy-sensitive site.",
      "Setting retention shorter than the review workflow needs.",
      "Using bytes-only quotas without checking the human-readable capacity.",
    ],
  },
  llm_provider: {
    eyebrow: "Policy assistance",
    title: "Configure policy draft assistance",
    summary:
      "LLM provider profiles power policy drafting. They do not affect detector inference or scene telemetry.",
    commonMistakes: [
      "Omitting base URL for local or custom providers.",
      "Expecting this setting to change model detection behavior.",
      "Saving a provider-backed profile without the required credential.",
    ],
  },
  operations_mode: {
    eyebrow: "Lifecycle",
    title: "Decide who owns worker lifecycle",
    summary:
      "Operations mode profiles control whether workers are manual, supervisor-managed, polling, push-driven, and restartable.",
    commonMistakes: [
      "Selecting edge supervisor for a camera without an edge node.",
      "Selecting push while the supporting dispatch service is unavailable.",
      "Using always restart during manual debugging.",
    ],
  },
};

export const PROFILE_FIELD_GUIDANCE: Record<
  OperatorConfigKind,
  Record<string, FieldGuidance>
> = {
  evidence_storage: {
    provider: {
      label: "Provider",
      hint: "Storage technology used for incident evidence.",
      details: [
        "MinIO is the default appliance object store.",
        "S3-compatible is for external object stores.",
        "Local filesystem is useful for simple edge-local evidence paths.",
        "Local first writes locally before central or cloud movement.",
      ],
      safeDefault: "MinIO for the portable master appliance.",
      runtimeEffect: "Incident capture uses this provider when writing clips and snapshots.",
    },
    storage_scope: {
      label: "Storage scope",
      hint: "Where evidence should live first: edge, central, or cloud.",
      details: ["Match this to privacy residency and network reliability."],
      safeDefault: "Central for a single MacBook master test build.",
    },
    local_root: {
      label: "Local root",
      hint: "Host or container path used by local filesystem evidence storage.",
      details: ["Use a durable mounted path that the evidence writer can access."],
      safeDefault: "/var/lib/vezor/evidence for appliance-style installs.",
    },
    endpoint: {
      label: "Endpoint",
      hint: "Object-store host and port for MinIO or S3-compatible storage.",
      details: ["Use a network-reachable endpoint from the backend container or worker."],
    },
    region: {
      label: "Region",
      hint: "Object-store region used by S3-compatible providers.",
      details: ["Leave empty for local MinIO unless your provider requires it."],
    },
    bucket: {
      label: "Bucket",
      hint: "Object-store bucket where evidence objects are written.",
      details: ["Use a dedicated bucket or prefix for OmniSight evidence."],
    },
    secure: {
      label: "Secure TLS",
      hint: "Controls whether object store calls use HTTPS/TLS.",
      details: ["Enable this for remote object stores and any non-local production route."],
      safeDefault: "Enabled for remote S3-compatible storage.",
    },
    path_prefix: {
      label: "Path prefix",
      hint: "Namespace inside the bucket or storage root.",
      details: ["Use prefixes to separate environments, sites, or tenants in one bucket."],
    },
    access_key: {
      label: "Access key",
      hint: "Write-only access credential for object storage.",
      details: ["Saved keys are shown as stored and never redisplayed."],
    },
    secret_key: {
      label: "Secret key",
      hint: "Write-only secret credential for object storage.",
      details: ["Saved secrets are shown as stored and never redisplayed."],
    },
  },
  stream_delivery: {
    delivery_mode: {
      label: "Transport mode",
      hint: "How the browser connects to live video.",
      details: [
        "Native/direct keeps clean passthrough when available.",
        "WebRTC is low latency but requires reachable WebRTC hosts and UDP.",
        "HLS is resilient and easier across networks, with higher latency.",
        "MJPEG is a compatibility fallback and can use more bandwidth.",
      ],
      safeDefault: "Native/direct for normal appliance testing.",
    },
    public_base_url: {
      label: "Public base URL",
      hint: "Browser-facing stream base URL when a direct route is required.",
      details: ["Do not use localhost when operators connect from another machine."],
    },
    edge_override_url: {
      label: "Edge override URL",
      hint: "Edge-specific stream host override for remote or routed edge nodes.",
      details: [
        "Use when an edge node publishes streams through a dedicated IP, DNS name, or forwarded port.",
      ],
    },
  },
  runtime_selection: {
    preferred_backend: {
      label: "Preferred backend",
      hint: "Runtime backend workers should try first.",
      details: ["Auto lets the worker pick the best compatible backend."],
      safeDefault: "Auto until validated artifacts exist.",
    },
    artifact_preference: {
      label: "Artifact preference",
      hint: "Order for compiled and portable model artifacts.",
      details: [
        "TensorRT first is fastest on compatible NVIDIA targets when a valid engine exists.",
      ],
      safeDefault:
        "TensorRT first on Jetson after artifact validation; ONNX first for portability.",
    },
    fallback_allowed: {
      label: "Allow fallback",
      hint: "Permit a compatible slower runtime if the preferred runtime is unavailable.",
      details: ["Disable only when you want startup to fail instead of silently degrading."],
      safeDefault: "Enabled during setup and validation.",
    },
  },
  privacy_policy: {
    retention_days: {
      label: "Retention days",
      hint: "How long evidence remains eligible for storage.",
      details: ["Set this longer than the expected review and export window."],
      safeDefault: "30 days for test builds.",
    },
    storage_quota_bytes: {
      label: "Storage quota",
      hint: "Maximum evidence storage budget.",
      details: ["Reason about the value in GB or TB before saving the byte count."],
      safeDefault: "10 GB for a small test build.",
    },
    plaintext_plate_storage: {
      label: "Plaintext plate posture",
      hint: "Whether unredacted license plate text may be stored.",
      details: [
        "Blocked is safest unless a site has explicit permission to retain plaintext plate data.",
      ],
      safeDefault: "Blocked.",
    },
    residency: {
      label: "Residency guardrail",
      hint: "Where sensitive evidence is allowed to live.",
      details: ["Choose edge or local-first when privacy or bandwidth requires local handling."],
      safeDefault: "Central for controlled local tests; edge/local-first for sensitive sites.",
    },
  },
  llm_provider: {
    provider: {
      label: "Provider",
      hint: "Service used for policy draft assistance.",
      details: ["This does not change detector inference."],
    },
    model: {
      label: "Model",
      hint: "Provider model used for drafting policy text.",
      details: ["Use a model name that exists at the configured provider."],
    },
    base_url: {
      label: "Base URL",
      hint: "Endpoint for local or custom LLM-compatible providers.",
      details: ["Leave empty only when the provider uses its default hosted endpoint."],
    },
    api_key: {
      label: "API key",
      hint: "Write-only credential for the provider.",
      details: ["Saved keys are shown as stored and never redisplayed."],
    },
  },
  operations_mode: {
    lifecycle_owner: {
      label: "Lifecycle owner",
      hint: "Who owns start, stop, and restart behavior for workers.",
      details: [
        "Manual means OmniSight observes but does not own lifecycle.",
        "Edge supervisor owns local edge workers.",
        "Central supervisor owns central workers.",
      ],
      safeDefault: "Edge supervisor for Jetson-assigned cameras; manual for debugging.",
    },
    supervisor_mode: {
      label: "Supervisor mode",
      hint: "How lifecycle intent reaches the supervisor.",
      details: [
        "Disabled blocks automated lifecycle actions.",
        "Polling lets the supervisor periodically reconcile desired state.",
        "Push dispatches lifecycle requests immediately when the service is available.",
      ],
      safeDefault: "Polling for appliance tests.",
    },
    restart_policy: {
      label: "Restart policy",
      hint: "Recovery behavior after worker exit or failure.",
      details: [
        "Never leaves stopped workers stopped.",
        "On failure restarts after crashes or unhealthy exits.",
        "Always restarts even after intentional exits.",
      ],
      safeDefault: "On failure.",
    },
  },
};
