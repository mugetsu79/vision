import { productBrand } from "@/brand/product";
import { cn } from "@/lib/utils";

type OmniSightFieldVariant =
  | "entry"
  | "stage"
  | "dashboard"
  | "overview"
  | "shell"
  | "quiet";

type OmniSightFieldProps = {
  variant?: OmniSightFieldVariant;
  className?: string;
};

const orbitalNodes = [
  {
    label: "Live Intelligence",
    status: "active now",
    className: "left-[61%] top-[18%]",
  },
  {
    label: "Scenes",
    status: "connected",
    className: "left-[30%] top-[32%]",
  },
  {
    label: "Evidence",
    status: "review queue",
    className: "left-[34%] bottom-[20%]",
  },
  {
    label: "Operations",
    status: "all systems go",
    className: "right-[11%] top-[42%]",
  },
];

const markLayers = ["back", "middle", "front"] as const;

export function OmniSightField({
  variant = "shell",
  className,
}: OmniSightFieldProps) {
  const showNodes =
    variant === "overview" || variant === "dashboard" || variant === "shell";

  return (
    <div
      aria-hidden="true"
      data-testid="omnisight-field"
      className={cn(
        "omnisight-field",
        `omnisight-field--${variant}`,
        className,
      )}
    >
      <div className="omnisight-field__orbital-map" />
      <div className="omnisight-field__ring omnisight-field__ring--primary" />
      <div className="omnisight-field__ring omnisight-field__ring--secondary" />
      <div className="omnisight-field__mark-stack">
        {markLayers.map((layer) => (
          <img
            key={layer}
            alt=""
            className={cn(
              "omnisight-field__mark-layer",
              `omnisight-field__mark-layer--${layer}`,
            )}
            draggable={false}
            src={productBrand.runtimeAssets.logo3d}
          />
        ))}
      </div>
      {showNodes
        ? orbitalNodes.map((node) => (
            <div
              key={node.label}
              className={cn("omnisight-field__node", node.className)}
            >
              <span className="omnisight-field__node-dot" />
              <span className="omnisight-field__node-copy">
                <span>{node.label}</span>
                <span>{node.status}</span>
              </span>
            </div>
          ))
        : null}
    </div>
  );
}
