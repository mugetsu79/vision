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
        "inline-flex items-center justify-center rounded-full border border-[color:var(--vezor-border-neutral)] bg-[linear-gradient(180deg,rgba(22,28,38,0.98),rgba(12,17,25,0.98))] px-4 py-2.5 text-sm font-medium text-[var(--argus-text)] shadow-[0_12px_28px_-24px_rgba(0,0,0,0.88)] transition duration-200 hover:border-[color:var(--vezor-border-focus)] hover:bg-[rgba(20,28,39,0.98)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--argus-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--argus-canvas)] disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
