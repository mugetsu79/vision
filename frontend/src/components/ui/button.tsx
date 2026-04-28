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
        "inline-flex items-center justify-center rounded-[0.95rem] border border-[color:var(--argus-border-strong)] bg-[linear-gradient(180deg,rgba(29,43,65,0.98),rgba(15,22,35,0.98))] px-4 py-2.5 text-sm font-medium text-[var(--argus-text)] shadow-[0_16px_32px_-24px_rgba(63,121,255,0.58)] transition duration-200 hover:border-[color:var(--argus-border-highlight)] hover:bg-[linear-gradient(180deg,rgba(39,57,84,0.98),rgba(19,29,45,0.98))] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--argus-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--argus-canvas)] disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
