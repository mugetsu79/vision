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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(2,5,10,0.76)] p-6 backdrop-blur-sm">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="dialog-title"
        className="w-full max-w-3xl overflow-hidden rounded-[1.9rem] border border-white/10 bg-[linear-gradient(180deg,rgba(10,15,24,0.98),rgba(17,24,37,0.96))] shadow-[0_42px_120px_-54px_rgba(0,0,0,0.95)]"
      >
        <div className="border-b border-white/8 px-6 py-5">
          <h2 id="dialog-title" className="text-2xl font-semibold text-[#f4f8ff]">
            {title}
          </h2>
          {description ? (
            <p className="mt-2 text-sm text-[#8ea4c7]">{description}</p>
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
        "rounded-full border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]",
        className,
      )}
      type="button"
      {...props}
    />
  );
}
