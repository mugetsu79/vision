export const omniLabels = {
  liveTitle: "Live Intelligence",
  historyTitle: "History & Patterns",
  evidenceTitle: "Evidence Desk",
  sceneSetupTitle: "Scene Setup",
  operationsTitle: "Operations",
  askVezorTitle: "Ask Vezor",
  resolvedIntentTitle: "Resolved Intent",
  signalsInViewTitle: "Signals in View",
  streamDiagnosticsTitle: "Stream diagnostics",
  reviewQueueTitle: "Review Queue",
  evidenceMediaTitle: "Evidence",
  factsTitle: "Facts",
} as const;

export const omniEmptyStates = {
  noScenes: "No scenes are connected yet.",
  noSignals: "Live telemetry has not produced visible signals yet.",
  noEvidence: "No evidence records match the current filters.",
  noSites: "No sites are configured yet.",
} as const;

export const omniPlaceExamples = {
  askVezor: "show people near restricted zones",
  runtimeVocabulary: "person, forklift, safety vest",
  eventClasses: "person, vehicle",
  siteName: "HQ",
  siteDescription: "Main campus or operating zone",
  timezone: "Europe/Zurich",
  edgeHostname: "edge-kit-01",
  rtspUrl: "rtsp://camera.local/live",
} as const;

export const omniNavGroups = [
  {
    label: "Intelligence",
    items: [
      { label: "Live", to: "/live" },
      { label: "Patterns", to: "/history" },
      { label: "Evidence", to: "/incidents" },
    ],
  },
  {
    label: "Control",
    items: [
      { label: "Sites", to: "/sites" },
      { label: "Scenes", to: "/cameras" },
      { label: "Operations", to: "/settings" },
    ],
  },
] as const;
