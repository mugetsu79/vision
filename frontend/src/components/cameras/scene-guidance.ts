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
    title: "Calibrate the floor plane for events and speed",
    summary:
      "Pick four fixed floor marks in the camera view, draw the same marks from above, then add a measured distance so motion can be mapped to real space.",
    concepts: [
      {
        term: "Camera image points",
        definition: "The four fixed floor marks you click in the camera view. These are also called source points.",
      },
      {
        term: "Top-down points",
        definition: "The same four marks drawn as if you were looking straight down from above. These are also called destination points.",
      },
      {
        term: "Measured distance",
        definition: "A real distance in meters between visible marks on the same floor plane.",
      },
    ],
    steps: [
      "If this is a new camera, use the temporary plane now and refresh the still after saving.",
      "Click four fixed floor marks in the camera image.",
      "Draw those same four marks from above in the same order.",
      "Enter a real measured distance in meters.",
      "Draw line boundaries or polygon zones for events after calibration lines up.",
      "Add include or exclusion regions only when the detector needs masking.",
    ],
    commonMistakes: [
      "Mixing the point order between the camera image and top-down drawing.",
      "Using shadows, people, vehicles, wall corners, or moved objects as reference marks.",
      "Measuring a distance on a different floor level from where objects move.",
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
    label: "Camera image points",
    hint: "Click four fixed floor marks in the camera view. These are the source points.",
    details: [
      "Use marks that will not move: floor paint, lane marks, doorway floor corners, or loading-bay corners.",
      "Avoid shadows, people, vehicles, wall corners above the floor, and temporary equipment.",
      "Click the points in the same order you will draw them in the top-down view.",
    ],
    safeDefault: "Four corners of a visible rectangle on the floor or ground.",
    runtimeEffect:
      "Completed camera image points and top-down points let speed and direction use the camera perspective.",
    required: true,
  },
  destinationPoints: {
    label: "Top-down points",
    hint: "Draw the same four real-world marks as if looking straight down from above.",
    details: [
      "These points represent the same marks you clicked in the camera image.",
      "They do not need to be GPS coordinates or perfectly scaled.",
      "Keep the point order identical to the camera image points.",
    ],
    safeDefault: "A simple rectangle with the same corner order as the camera image points.",
    required: true,
  },
  referenceDistance: {
    label: "Measured distance",
    hint: "Enter a real distance in meters between two visible floor marks.",
    details: [
      "Measure a lane width, doorway width, floor stripe, parking bay, or loading-bay span.",
      "Use a longer measured span when possible; it usually gives better speed estimates than a short guessed distance.",
      "The measured distance should be on the same flat plane where feet or wheels move.",
    ],
    safeDefault:
      "Use a tape-measured distance, not an estimate, whenever speed matters.",
    runtimeEffect:
      "Speed should not be trusted until the measured distance is set and verified with known movement.",
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

export const SPEED_CALIBRATION_CHECKLIST = [
  "Camera is fixed and not zooming.",
  "The four camera image points sit on the same flat floor plane where people or vehicles move.",
  "Top-down points match the same four marks in the same order.",
  "Measured distance is real, in meters, and on that same floor plane.",
  "Objects used for speed testing move through the calibrated area.",
  "A known walk, cart, or vehicle pass has been checked against the reported speed.",
];

export const SPEED_CALIBRATION_WARNING =
  "Speed is only as accurate as the calibrated floor plane. If objects move on a ramp, stairs, raised platform, or outside the marked area, treat speed as an estimate.";
