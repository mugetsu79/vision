import type {
  FieldGuidance,
  SectionGuidance,
} from "@/components/guidance/guidance-types";

export const SCENE_STEP_GUIDANCE: Record<string, SectionGuidance> = {
  Identity: {
    eyebrow: "Scene setup",
    title: "Identify where this camera runs",
    summary:
      "Name the camera, choose the site, and decide whether inference runs centrally, at the edge, or through a hybrid path.",
    concepts: [
      {
        term: "Camera source",
        definition:
          "The RTSP stream or USB device that provides frames to the analytics pipeline.",
      },
      {
        term: "Processing mode",
        definition: "Where the worker performs inference for this camera.",
      },
    ],
    examples: [
      {
        label: "Central",
        description: "Start here when the master can reliably pull the RTSP stream.",
      },
      {
        label: "Edge",
        description: "Use for USB capture, weak uplink, or privacy-sensitive sites.",
      },
      {
        label: "Hybrid",
        description:
          "Use when an edge node runs local inference and central services may also consume results.",
      },
    ],
  },
  "Models & Tracking": {
    eyebrow: "Detection",
    title: "Choose what this camera observes",
    summary:
      "The primary model drives persistent detections, optional secondary models refine results, and tracker type affects continuity across frames.",
    concepts: [
      {
        term: "Active class scope",
        definition:
          "A fixed-vocabulary filter that narrows which model classes emit detections for this camera.",
      },
      {
        term: "Runtime vocabulary",
        definition:
          "Open-vocabulary terms used by compatible models; changing them can make compiled artifacts stale.",
      },
    ],
    commonMistakes: [
      "Selecting a TensorRT artifact as a scene model instead of the canonical model row.",
      "Expecting tracker type to change which classes are detected.",
    ],
  },
  "Privacy, Processing & Delivery": {
    eyebrow: "Delivery",
    title: "Separate privacy, processing, evidence, and live view",
    summary:
      "Privacy controls redaction, processing controls inference load, evidence recording stores event clips, and live rendition chooses the visual stream operators watch.",
    concepts: [
      {
        term: "Transport profile",
        definition: "How browsers reach a stream through native, WebRTC, HLS, or MJPEG routes.",
      },
      {
        term: "Live rendition",
        definition: "The clean, annotated, or reduced stream variant selected for this camera.",
      },
    ],
    examples: [
      {
        label: "Weak network",
        description: "Use HLS or a reduced processed rendition.",
      },
      {
        label: "Low latency",
        description: "Use WebRTC when the WebRTC host and UDP path are reachable.",
      },
      {
        label: "Privacy-heavy site",
        description: "Blur faces and plates, then prefer edge or local-first evidence storage.",
      },
    ],
  },
  Calibration: {
    eyebrow: "Geometry",
    title: "Map the camera image to operational space",
    summary:
      "Use source and destination points to calibrate perspective, then draw event boundaries and detection masks on the same analytics frame.",
    concepts: [
      {
        term: "Source points",
        definition: "Reference marks placed on the camera image.",
      },
      {
        term: "Destination points",
        definition: "Matching marks on an abstract top-down world plane.",
      },
      {
        term: "Detection region",
        definition: "An include or exclusion mask applied before event rules are evaluated.",
      },
    ],
    steps: [
      "Confirm the analytics still matches the camera view.",
      "Place four source points on stable ground-plane reference marks in the camera image.",
      "Place four destination points in the same order on the top-down plane.",
      "Enter a known reference distance in meters.",
      "Draw line boundaries or polygon zones for events.",
      "Add include or exclusion regions only when detector attention needs masking.",
    ],
    commonMistakes: [
      "Mixing source and destination point order.",
      "Using moving objects, shadows, or vertical surfaces as reference marks.",
      "Adding detection masks when event boundaries alone are enough.",
    ],
  },
  Review: {
    eyebrow: "Readiness",
    title: "Check what happens after save",
    summary:
      "Review should confirm source reachability, runtime posture, privacy settings, delivery, geometry, evidence recording, and the next runtime action.",
  },
};

export const SCENE_FIELD_GUIDANCE: Record<string, FieldGuidance> = {
  sourcePoints: {
    label: "Source points",
    hint: "Points on the camera image that identify the real-world reference plane.",
    details: [
      "Use four stable points on the floor, ground, lane, doorway, or loading bay.",
      "Avoid shadows, moving objects, vertical walls, and temporary equipment.",
      "Use the same point order as destination points.",
    ],
    safeDefault: "Four corners of a visible rectangular ground-plane area.",
    runtimeEffect:
      "Completed source and destination points allow distance, direction, and speed features to trust the camera perspective.",
    required: true,
  },
  destinationPoints: {
    label: "Destination points",
    hint: "Matching points on an abstract top-down world plane.",
    details: [
      "They represent the same real-world marks as the source points.",
      "They do not need to be GPS coordinates.",
      "Keep the point order identical to source points.",
    ],
    safeDefault: "A simple rectangle with the same corner order as the source plane.",
    required: true,
  },
  referenceDistance: {
    label: "Reference distance",
    hint: "A known real-world distance in meters between reference marks.",
    details: [
      "Measure a visible lane width, doorway width, floor marking, or loading-bay span.",
      "Use meters so downstream distance and speed logic uses consistent units.",
    ],
    safeDefault:
      "Use a measured distance, not an estimate, whenever speed or distance matters.",
    runtimeEffect:
      "Speed and distance logic should not be trusted until a measured reference distance is set.",
  },
  eventBoundaries: {
    label: "Event boundaries",
    hint: "Lines emit crossing events; polygon zones emit enter and exit events.",
    details: [
      "Use line boundaries for directional counts through doors, lanes, gates, and thresholds.",
      "Use polygon zones for restricted areas, occupancy areas, staging areas, and dwell regions.",
      "Class scope on line boundaries narrows which tracked classes emit events.",
    ],
    examples: [
      {
        label: "Doorway crossing",
        description: "Draw a line across the threshold to count direction changes.",
      },
      {
        label: "Restricted zone",
        description: "Draw a polygon around the area to emit enter and exit events.",
      },
    ],
  },
  detectionRegions: {
    label: "Detection regions",
    hint: "Include regions keep detections inside; exclusion regions suppress detections inside.",
    details: [
      "Use include regions to focus detection on the operational area.",
      "Use exclusion regions to ignore reflections, screens, public roads, or background motion.",
      "Detection regions are applied before event boundaries are evaluated.",
    ],
    examples: [
      {
        label: "Loading bay include",
        description: "Keep detections inside the working bay and ignore adjacent background.",
      },
      {
        label: "Road exclusion",
        description: "Mask a public road that creates irrelevant vehicle detections.",
      },
    ],
  },
};
