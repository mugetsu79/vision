import { useRef } from "react";

import { productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

import { useLensTilt } from "./use-lens-tilt";

type OmniSightLensVariant = "signin" | "dashboard";

type OmniSightLensProps = {
  variant?: OmniSightLensVariant;
  className?: string;
};

const variantSizes: Record<OmniSightLensVariant, string> = {
  signin: "w-[clamp(18rem,32vw,28rem)] aspect-square",
  dashboard: "w-[clamp(10rem,18vw,16rem)] aspect-square",
};

const energyFragments = [
  "right-[3%] top-[24%] h-px w-[38%] rotate-[-18deg]",
  "bottom-[27%] left-[5%] h-px w-[30%] rotate-[-18deg]",
  "left-[22%] top-[15%] h-px w-[21%] rotate-[42deg] opacity-55",
] as const;

export function OmniSightLens({
  variant = "signin",
  className,
}: OmniSightLensProps) {
  const stageRef = useRef<HTMLDivElement>(null);
  useLensTilt(stageRef);

  return (
    <div
      ref={stageRef}
      data-testid="omnisight-lens"
      data-variant={variant}
      aria-hidden="true"
      className={cn(
        "lens-stage relative grid place-items-center",
        variantSizes[variant],
        className,
      )}
    >
      <span data-lens-halo className="lens-halo" />
      {energyFragments.map((fragmentClassName, index) => (
        <span
          // The fragments imply lens energy without restoring full orbital guide lines.
          data-lens-energy
          key={fragmentClassName}
          className={cn(
            "pointer-events-none absolute z-[1] rounded-full bg-gradient-to-r",
            "from-transparent via-[rgba(118,224,255,0.82)] to-transparent",
            "shadow-[0_0_18px_rgba(118,224,255,0.42)] motion-safe:animate-pulse",
            fragmentClassName,
          )}
          style={{ animationDelay: `${index * -1.6}s` }}
        />
      ))}
      <img
        alt=""
        draggable={false}
        src={productBrand.runtimeAssets.logo3d}
        className="lens-mark relative z-[2] w-[78%] object-contain"
      />
    </div>
  );
}
