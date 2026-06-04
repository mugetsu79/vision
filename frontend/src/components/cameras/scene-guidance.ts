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
        description:
          "Start here when the master can reliably pull the RTSP stream.",
      },
      {
        label: "Edge",
        description:
          "Use for USB capture, weak uplink, or privacy-sensitive sites.",
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
        definition:
          "How browsers reach a stream through native, WebRTC, HLS, or MJPEG routes.",
      },
      {
        term: "Live rendition",
        definition:
          "The clean, annotated, or reduced stream variant selected for this camera.",
      },
    ],
    examples: [
      {
        label: "Weak network",
        description: "Use HLS or a reduced processed rendition.",
      },
      {
        label: "Low latency",
        description:
          "Use WebRTC when the WebRTC host and UDP path are reachable.",
      },
      {
        label: "Privacy-heavy site",
        description:
          "Blur faces and plates, then prefer edge or local-first evidence storage.",
      },
    ],
  },
  Calibration: {
    eyebrow: "Geometry",
    title: "Calibrate the movement plane for events and speed",
    summary:
      "Pick four fixed reference marks in the camera view, draw the same marks from above, then enter the real D1 to D2 distance so motion can be mapped to real space.",
    concepts: [
      {
        term: "Camera image points",
        definition:
          "The four fixed reference marks you click in the camera view. These are also called source points.",
      },
      {
        term: "Top-down points",
        definition:
          "The same four marks drawn by the operator as if looking straight down from above. These are also called destination points, and they are not captured from a second camera still.",
      },
      {
        term: "Measured distance",
        definition:
          "The real distance in meters between destination points D1 and D2. In the camera still, these are the same physical marks as S1 and S2.",
      },
    ],
    steps: [
      "If this is a new camera, use the temporary plane now and refresh the still after saving.",
      "Click four fixed reference marks in the camera image.",
      "Draw those same four marks from above in the same order.",
      "Enter the real D1 to D2 measured distance in meters.",
      "Draw line boundaries or polygon zones for events after calibration lines up.",
      "Add include or exclusion regions only when the detector needs masking.",
    ],
    commonMistakes: [
      "Mixing the point order between the camera image and top-down drawing.",
      "Using shadows, moving subjects, wall corners off the movement plane, or temporary equipment as reference marks.",
      "Measuring a distance on a different plane from where tracked anchors move.",
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
    hint: "Click four fixed reference marks in the camera view. These are the source points.",
    details: [
      "Use marks that will not move and that sit on the same calibrated movement plane.",
      "Avoid shadows, moving subjects, wall corners off the movement plane, and temporary equipment.",
      "Click the points in the same order you will draw them in the top-down view.",
    ],
    safeDefault: "Four corners of a visible fixed rectangle on the movement plane.",
    runtimeEffect:
      "Completed camera image points and top-down points let speed and direction use the camera perspective.",
    required: true,
  },
  destinationPoints: {
    label: "Top-down points",
    hint: "Draw the same four real-world marks as if looking straight down from above.",
    details: [
      "These points represent the same marks you clicked in the camera image.",
      "Destination points are hand-drawn top-down coordinates, not another still captured from the camera.",
      "They do not need to be GPS coordinates or perfectly scaled.",
      "Keep the point order identical to the camera image points.",
    ],
    safeDefault:
      "A simple rectangle with the same corner order as the camera image points.",
    required: true,
  },
  referenceDistance: {
    label: "Measured distance",
    hint: "Enter the real D1 to D2 distance in meters.",
    details: [
      "The runtime uses D1 to D2, the first two top-down destination points, as the scale segment.",
      "S1 and S2 must be the same two physical marks in the camera still; their pixel coordinates will usually differ from the D1 and D2 world-plane coordinates.",
      "D1 and D2 are drawn on the destination plane; the destination plane is not another camera capture.",
      "No third still capture is needed; refresh the analytics still after saving only to verify the points still line up with the real video frame.",
      "Measure a known mark-to-mark span on the same movement plane, then make that measured span points 1 and 2.",
      "Use a longer measured span when possible; it usually gives better speed estimates than a short guessed distance.",
      "The measured distance should be on the same calibrated plane where tracked anchors move.",
    ],
    examples: [
      {
        label: "Known reference span",
        description:
          "If two fixed marks are 2.5 m apart, click those marks as S1 and S2, draw the same marks as D1 and D2, then enter 2.5.",
      },
      {
        label: "Alternate measured side",
        description:
          "If another side of the four-mark shape is the known span, make that side points 1 and 2 before saving.",
      },
    ],
    safeDefault:
      "Use a tape-measured D1 to D2 distance, not an estimate, whenever speed matters.",
    runtimeEffect:
      "Speed should not be trusted until the measured distance is set and verified with known movement.",
  },
  eventBoundaries: {
    label: "Event boundaries",
    hint: "Draw lines or zones on the analytics still where tracked anchors move.",
    details: [
      "Line boundaries emit crossing events when a tracked anchor changes sides.",
      "Polygon zones emit enter and exit events when a tracked anchor moves into or out of the marked area.",
      "Draw both shapes on the camera analytics still, not on the destination point sketch.",
      "Use line boundaries for any transition path where crossing matters.",
      "Use polygon zones for bounded areas where enter and exit matters.",
      "Class scope on line boundaries narrows which tracked classes emit events.",
    ],
    examples: [
      {
        label: "Transition crossing",
        description:
          "Draw a line across the path where crossing direction should become an event.",
      },
      {
        label: "Controlled zone",
        description:
          "Draw a polygon around any bounded area that should emit enter and exit events.",
      },
    ],
  },
  detectionRegions: {
    label: "Detection regions",
    hint: "Include polygons keep detections eligible; exclusion polygons suppress detections.",
    details: [
      "Draw detection regions on the camera analytics still, not on the destination point sketch.",
      "Use include regions to focus detection on the observation area; if any include region exists, detections outside include regions are ignored.",
      "Use exclusion regions to ignore reflections, screens, repeated background motion, or irrelevant scene areas.",
      "Detection regions are applied before event boundaries are evaluated, so masked detections cannot create line or zone events.",
    ],
    examples: [
      {
        label: "Observation area include",
        description:
          "Keep detections inside the useful part of the scene and ignore adjacent background.",
      },
      {
        label: "Noise pocket exclusion",
        description:
          "Mask a repeated reflection, display, surface, or background area that creates irrelevant detections.",
      },
    ],
  },
};

export const SPEED_CALIBRATION_CHECKLIST = [
  "Camera is fixed and not zooming.",
  "The four camera image points sit on the same calibrated plane where tracked anchors move.",
  "Top-down points match the same four marks in the same order.",
  "Measured distance is real, in meters, and on that same calibrated plane.",
  "Objects used for speed testing move through the calibrated area.",
  "A known test pass has been checked against the reported speed.",
];

export const SPEED_CALIBRATION_WARNING =
  "Speed is only as accurate as the calibrated movement plane. If objects move on a different plane or outside the marked area, treat speed as an estimate.";
