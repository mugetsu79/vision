import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type ButtonVariant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const baseClasses =
  "inline-flex items-center justify-center rounded-full px-4 py-2.5 text-sm font-medium transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--vz-hair-focus)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--vz-canvas-obsidian)] disabled:cursor-not-allowed disabled:opacity-60";

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "border-0 bg-[linear-gradient(135deg,var(--vz-lens-cerulean)_0%,var(--vz-lens-cerulean-deep)_100%)] from-[var(--vz-lens-cerulean)] to-[var(--vz-lens-cerulean-deep)] text-[#04101b] shadow-[0_14px_30px_-18px_rgba(110,189,255,0.6)] hover:brightness-110",
  secondary:
    "border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,#161c26,#0d121a)] text-[var(--vz-text-primary)] shadow-[var(--vz-elev-1)] hover:border-[color:var(--vz-hair-focus)]",
  ghost:
    "border border-[color:var(--vz-hair)] bg-transparent text-[var(--vz-text-secondary)] hover:border-[color:var(--vz-hair-strong)] hover:text-[var(--vz-text-primary)]",
};

export function Button({
  className,
  type = "button",
  variant = "secondary",
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(baseClasses, variantClasses[variant], className)}
      {...props}
    />
  );
}
