import { Network } from "lucide-react";
import { Link } from "react-router-dom";

import { cn } from "@/lib/utils";

type FleetOpsLinkPerformanceLinkProps = {
  siteId?: string | null;
  className?: string;
};

export function FleetOpsLinkPerformanceLink({
  siteId,
  className,
}: FleetOpsLinkPerformanceLinkProps) {
  if (!siteId) {
    return null;
  }

  return (
    <Link
      className={cn(
        "inline-flex w-fit items-center justify-center rounded-full border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] px-4 py-2.5 text-sm font-medium text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] transition duration-200 hover:border-[color:var(--vz-hair-focus)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--vz-hair-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--vz-canvas-obsidian)]",
        className,
      )}
      to={linkPerformancePath(siteId)}
    >
      <Network className="mr-2 size-4" aria-hidden="true" />
      Open Link Performance
    </Link>
  );
}

function linkPerformancePath(siteId?: string | null) {
  return siteId ? `/links?site=${encodeURIComponent(siteId)}` : "/links";
}
