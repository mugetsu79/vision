import type { ComponentProps, ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

// eslint-disable-next-line react-refresh/only-export-components
export const routerFuture = {
  v7_relativeSplatPath: true,
  v7_startTransition: true,
} as const;

type TestMemoryRouterProps = Omit<
  ComponentProps<typeof MemoryRouter>,
  "future"
> & {
  children?: ReactNode;
};

export function TestMemoryRouter({
  children,
  ...props
}: TestMemoryRouterProps) {
  return (
    <MemoryRouter future={routerFuture} {...props}>
      {children}
    </MemoryRouter>
  );
}
