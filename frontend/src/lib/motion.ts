import { useReducedMotion } from "framer-motion";

export const easings = {
  product: [0.22, 1, 0.36, 1] as const,
  out: [0.16, 1, 0.3, 1] as const,
  inOut: [0.65, 0, 0.35, 1] as const,
  spring: [0.34, 1.56, 0.64, 1] as const,
};

export const durations = {
  instant: 0.09,
  quick: 0.18,
  base: 0.24,
  soft: 0.32,
};

export const motionPresets = {
  rise: {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: durations.base, ease: easings.product },
  },
  lensSnap: {
    initial: { opacity: 0, scale: 0.97 },
    animate: { opacity: 1, scale: 1 },
    transition: { duration: durations.soft, ease: easings.product },
  },
  evidenceSwap: {
    initial: { x: 24, opacity: 0 },
    animate: { x: 0, opacity: 1 },
    exit: { x: -16, opacity: 0 },
    transition: { duration: durations.base, ease: easings.product },
  },
} as const;

export type MotionPresetName = keyof typeof motionPresets;

export function useReducedMotionSafe(preset: MotionPresetName) {
  const reduce = useReducedMotion();
  if (reduce) {
    return {
      initial: false as const,
      animate: { opacity: 1 },
      exit: { opacity: 0 },
      transition: { duration: 0 },
    };
  }
  return motionPresets[preset];
}
