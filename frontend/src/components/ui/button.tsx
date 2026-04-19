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
        "inline-flex items-center justify-center rounded-full bg-[linear-gradient(135deg,#2f7cff_0%,#805cff_100%)] px-4 py-2.5 text-sm font-medium text-white shadow-[0_16px_40px_-22px_rgba(76,108,255,0.88)] transition duration-200 hover:brightness-110 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#74a8ff]/70 focus-visible:ring-offset-2 focus-visible:ring-offset-[#08101a] disabled:cursor-not-allowed disabled:opacity-60",
        className,
      )}
      {...props}
    />
  );
}
