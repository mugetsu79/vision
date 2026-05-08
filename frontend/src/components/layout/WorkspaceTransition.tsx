import { type PropsWithChildren } from "react";
import { useLocation } from "react-router-dom";

export function WorkspaceTransition({ children }: PropsWithChildren) {
  const location = useLocation();

  return (
    <div
      key={location.pathname}
      data-route={location.pathname}
      data-testid="workspace-transition"
      className="animate-[workspace-enter_var(--vz-dur-base)_var(--vz-ease-product)_both] motion-reduce:animate-none"
    >
      {children}
    </div>
  );
}
