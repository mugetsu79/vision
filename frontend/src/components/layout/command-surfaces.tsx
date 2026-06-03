import type {
  DetailsHTMLAttributes,
  HTMLAttributes,
  PropsWithChildren,
  ReactNode,
} from "react";

import { cn } from "@/lib/utils";

type CommandBandProps = HTMLAttributes<HTMLElement> & {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
};

export function CommandBand({
  eyebrow,
  title,
  description,
  actions,
  className,
  children,
  ...props
}: CommandBandProps) {
  return (
    <section className={cn("command-band", className)} {...props}>
      <div>
        <p className="command-eyebrow">{eyebrow}</p>
        <h1 className="command-title">{title}</h1>
        <p className="command-description">{description}</p>
      </div>
      {actions ? <div className="command-actions">{actions}</div> : null}
      {children}
    </section>
  );
}

type OperationalSectionProps = HTMLAttributes<HTMLElement> & {
  id: string;
  label: string;
  eyebrow?: string;
};

export function OperationalSection({
  id,
  label,
  eyebrow,
  children,
  className,
  ...props
}: PropsWithChildren<OperationalSectionProps>) {
  return (
    <section {...props} id={id} className={cn("operational-section", className)} aria-labelledby={`${id}-heading`}>
      <div className="operational-section-header">
        {eyebrow ? <p className="command-eyebrow">{eyebrow}</p> : null}
        <h2 id={`${id}-heading`}>{label}</h2>
      </div>
      {children}
    </section>
  );
}

type DetailDrawerProps = DetailsHTMLAttributes<HTMLDetailsElement> & {
  label: string;
};

export function DetailDrawer({
  label,
  children,
  className,
  ...props
}: PropsWithChildren<DetailDrawerProps>) {
  return (
    <details className={cn("detail-drawer", className)} {...props}>
      <summary>{label}</summary>
      <div>{children}</div>
    </details>
  );
}
