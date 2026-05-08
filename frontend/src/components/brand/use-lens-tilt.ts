import { useEffect, type RefObject } from "react";

const MAX_TILT_DEG = 8;

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) {
    return false;
  }

  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function useLensTilt(ref: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el || prefersReducedMotion()) {
      return;
    }

    let frame = 0;
    let nextX = 0;
    let nextY = 0;

    const flush = () => {
      frame = 0;
      el.style.setProperty("--lens-rx", `${-nextY * MAX_TILT_DEG}deg`);
      el.style.setProperty("--lens-ry", `${nextX * MAX_TILT_DEG}deg`);
    };

    const onMove = (event: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      nextX = (event.clientX - rect.left) / rect.width - 0.5;
      nextY = (event.clientY - rect.top) / rect.height - 0.5;

      if (frame === 0) {
        frame = window.requestAnimationFrame(flush);
      }
    };

    const onLeave = () => {
      if (frame !== 0) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }

      el.style.setProperty("--lens-rx", "0deg");
      el.style.setProperty("--lens-ry", "0deg");
    };

    el.addEventListener("pointermove", onMove);
    el.addEventListener("pointerleave", onLeave);

    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      if (frame !== 0) {
        window.cancelAnimationFrame(frame);
      }
    };
  }, [ref]);
}
