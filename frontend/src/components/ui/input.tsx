import type { InputHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "w-full rounded-[0.85rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-4 py-3 text-sm text-[var(--argus-text)] outline-none placeholder:text-[var(--argus-text-subtle)] transition duration-200 focus:border-[color:var(--argus-border-highlight)] focus:shadow-[0_0_0_4px_var(--argus-accent-soft)]",
        className,
      )}
      {...props}
    />
  );
}
