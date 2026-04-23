import type {
  ButtonHTMLAttributes,
  HTMLAttributes,
  PropsWithChildren,
} from "react";

import { cn } from "@/lib/utils";

interface DialogProps extends PropsWithChildren {
  open: boolean;
  title: string;
  description?: string;
}

export function Dialog({ open, title, description, children }: DialogProps) {
  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(2,5,10,0.8)] p-6 backdrop-blur-md">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        className="w-full max-w-3xl overflow-hidden rounded-[1.9rem] border border-[color:var(--argus-border-strong)] bg-[linear-gradient(180deg,var(--argus-surface),var(--argus-surface-strong))] shadow-[0_42px_120px_-54px_rgba(0,0,0,0.95)]"
      >
        <div className="border-b border-[color:var(--argus-border)] px-6 py-5">
          <h2 id="dialog-title" className="text-2xl font-semibold text-[var(--argus-text)]">
            {title}
          </h2>
          {description ? (
            <p className="mt-2 text-sm text-[var(--argus-text-muted)]">{description}</p>
          ) : null}
        </div>
        <div className="px-6 py-6">{children}</div>
      </div>
    </div>
  );
}

export function DialogFooter({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("mt-6 flex justify-end gap-3", className)} {...props} />;
}

export function DialogCloseButton({
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(
        "rounded-full border border-[color:var(--argus-border)] bg-[color:var(--argus-surface-soft)] px-4 py-2 text-sm font-medium text-[var(--argus-text)] transition hover:border-[color:var(--argus-border-strong)] hover:bg-white/[0.06]",
        className,
      )}
      type="button"
      {...props}
    />
  );
}
