import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

type DivProps = HTMLAttributes<HTMLDivElement>;

export function Card({ className, ...props }: DivProps) {
  return (
    <div
      className={cn(
        "rounded-3xl border border-black/10 bg-white/85 shadow-[0_24px_80px_-32px_rgba(15,23,42,0.45)] backdrop-blur-sm",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: DivProps) {
  return <div className={cn("flex flex-col gap-2 px-6 py-6", className)} {...props} />;
}

export function CardTitle({ className, ...props }: DivProps) {
  return (
    <div
      className={cn("text-2xl font-semibold tracking-tight text-slate-950", className)}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: DivProps) {
  return <div className={cn("text-sm text-slate-600", className)} {...props} />;
}

export function CardContent({ className, ...props }: DivProps) {
  return <div className={cn("px-6 pb-6", className)} {...props} />;
}

export function CardFooter({ className, ...props }: DivProps) {
  return (
    <div
      className={cn("flex items-center justify-between gap-3 border-t border-black/5 px-6 py-4", className)}
      {...props}
    />
  );
}

export function CardAction({ className, ...props }: DivProps) {
  return <div className={cn("ml-auto", className)} {...props} />;
}

