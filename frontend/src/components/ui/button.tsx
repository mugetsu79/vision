import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Button({
  className,
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center rounded-full border border-[color:var(--argus-border-strong)] bg-[linear-gradient(180deg,rgba(26,36,53,0.98),rgba(15,22,35,0.98))] px-4 py-2.5 text-sm font-medium text-[var(--argus-text)] shadow-[0_12px_28px_-22px_rgba(0,0,0,0.85)] transition duration-200 hover:border-[color:var(--argus-border-highlight)] hover:bg-[linear-gradient(180deg,rgba(34,46,68,0.98),rgba(18,26,40,0.98))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--argus-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--argus-canvas)] disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
