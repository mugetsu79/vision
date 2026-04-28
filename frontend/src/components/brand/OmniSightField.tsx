import { cn } from "@/lib/utils";

type OmniSightFieldVariant = "entry" | "overview" | "shell" | "quiet";

type OmniSightFieldProps = {
  variant?: OmniSightFieldVariant;
  className?: string;
};

const overviewSurfaces = [
  {
    label: "Live Scenes",
    className: "left-[9%] top-[16%] h-16 w-36 rounded-[1rem]",
  },
  {
    label: "Evidence",
    className: "right-[7%] top-[18%] h-20 w-40 rounded-[1rem]",
  },
  {
    label: "Patterns",
    className: "left-[18%] bottom-[16%] h-20 w-44 rounded-[1rem]",
  },
  {
    label: "Edge Fleet",
    className: "right-[13%] bottom-[18%] h-16 w-36 rounded-[1rem]",
  },
];

export function OmniSightField({
  variant = "shell",
  className,
}: OmniSightFieldProps) {
  const showSurfaces = variant === "entry" || variant === "overview";

  return (
    <div
      aria-hidden="true"
      data-testid="omnisight-field"
      className={cn("omnisight-field", `omnisight-field--${variant}`, className)}
    >
      <div className="omnisight-field__ring left-[calc(50%_-_11rem)] top-[18%] h-40 w-[22rem]" />
      <div className="omnisight-field__ring left-[calc(50%_-_10rem)] top-[22%] h-36 w-80 rotate-[25deg] opacity-60" />
      <div className="omnisight-field__lens" />
      {showSurfaces
        ? overviewSurfaces.map((surface) => (
            <div
              key={surface.label}
              className={cn("omnisight-field__surface", surface.className)}
            >
              <span className="sr-only">{surface.label}</span>
            </div>
          ))
        : null}
    </div>
  );
}
