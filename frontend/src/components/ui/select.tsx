import type { SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Select({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "w-full rounded-2xl border border-[#22324b] bg-[#09111b] px-4 py-3 text-sm text-[#eef4ff] outline-none transition focus:border-[#4f86ff] focus:shadow-[0_0_0_4px_rgba(79,134,255,0.12)]",
        className,
      )}
      {...props}
    />
  );
}
