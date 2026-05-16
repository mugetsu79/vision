export type SignalColorFamily =
  | "human"
  | "vehicle"
  | "safety"
  | "alert"
  | "other";

export type SignalColor = {
  family: SignalColorFamily;
  stroke: string;
  fill: string;
  text: string;
};

const HUMAN_CLASSES = new Set(["person", "worker", "hi_vis_worker"]);
const VEHICLE_CLASSES = new Set([
  "car",
  "truck",
  "bus",
  "motorcycle",
  "bicycle",
]);
const SAFETY_CLASSES = new Set(["helmet", "vest", "ppe", "hard_hat"]);
const ALERT_CLASSES = new Set(["violation", "alert", "intrusion"]);

const FALLBACK_COLORS: SignalColor[] = [
  {
    family: "other",
    stroke: "#4dd7ff",
    fill: "rgba(77, 215, 255, 0.12)",
    text: "#d9f7ff",
  },
  {
    family: "other",
    stroke: "#a98bff",
    fill: "rgba(169, 139, 255, 0.13)",
    text: "#eee8ff",
  },
  {
    family: "other",
    stroke: "#f7c56b",
    fill: "rgba(247, 197, 107, 0.12)",
    text: "#fff1ca",
  },
];

export function colorForClass(className: string): SignalColor {
  const normalized = className.toLowerCase();
  if (HUMAN_CLASSES.has(normalized)) {
    return {
      family: "human",
      stroke: "#61e6a6",
      fill: "rgba(97, 230, 166, 0.12)",
      text: "#e8fff4",
    };
  }
  if (VEHICLE_CLASSES.has(normalized)) {
    return {
      family: "vehicle",
      stroke: "#62a6ff",
      fill: "rgba(98, 166, 255, 0.12)",
      text: "#e9f3ff",
    };
  }
  if (SAFETY_CLASSES.has(normalized)) {
    return {
      family: "safety",
      stroke: "#f7c56b",
      fill: "rgba(247, 197, 107, 0.13)",
      text: "#fff2cf",
    };
  }
  if (ALERT_CLASSES.has(normalized)) {
    return {
      family: "alert",
      stroke: "#ff6f9d",
      fill: "rgba(255, 111, 157, 0.13)",
      text: "#ffe7ef",
    };
  }

  return FALLBACK_COLORS[hashClassName(normalized) % FALLBACK_COLORS.length];
}

function hashClassName(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
}
