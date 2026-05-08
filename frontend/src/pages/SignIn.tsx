import { Camera, Cpu, ScanEye } from "lucide-react";

import { productBrand } from "@/brand/product";
import { OmniSightLens } from "@/components/brand/OmniSightLens";
import { ProductLockup } from "@/components/layout/ProductLockup";
import { WorkspaceHero } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

const proofSignals = [
  { icon: Camera, label: "Scenes", caption: "Live spatial canvas" },
  { icon: ScanEye, label: "Evidence", caption: "Reviewed in seconds" },
  { icon: Cpu, label: "Operations", caption: "Edge-aware fleet" },
] as const;

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);
  const brandName = productBrand.name;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(60%_60%_at_75%_30%,rgba(126,83,255,0.18),transparent_60%),linear-gradient(180deg,var(--vz-canvas-void)_0%,var(--vz-canvas-obsidian)_100%)] px-6 py-8 text-[var(--vz-text-primary)]">
      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl grid-rows-[auto_1fr_auto] gap-8">
        <header className="flex items-center justify-between">
          <ProductLockup className="h-12 w-auto" />
          <p className="hidden text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)] sm:block">
            Spatial intelligence layer
          </p>
        </header>

        <WorkspaceHero
          eyebrow={productBrand.descriptor}
          title="OmniSight for every live environment."
          description={`${brandName} connects scenes, models, events, evidence, and edge operations into one spatial intelligence layer.`}
          tone="violet"
          lens={<OmniSightLens variant="signin" />}
          body={
            <ul className="grid max-w-xl grid-cols-3 gap-3 text-sm">
              {proofSignals.map(({ icon: Icon, label, caption }) => (
                <li
                  key={label}
                  className="flex items-start gap-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite-up)] px-3 py-2.5"
                >
                  <Icon
                    className="mt-0.5 size-4 text-[var(--vz-lens-cerulean)]"
                    aria-hidden="true"
                  />
                  <span className="flex flex-col">
                    <span className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-secondary)]">
                      {label}
                    </span>
                    <span className="text-[12px] text-[var(--vz-text-muted)]">
                      {caption}
                    </span>
                  </span>
                </li>
              ))}
            </ul>
          }
        />

        <section
          data-testid="signin-auth-panel"
          className="ml-auto w-full max-w-[25rem] rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair-strong)] bg-[linear-gradient(180deg,rgba(10,15,25,0.94),rgba(5,8,14,0.92))] p-6 text-[var(--vz-text-primary)] shadow-[var(--vz-elev-glow-violet)] backdrop-blur-xl sm:p-7"
        >
          <p className="text-xs font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
            Secure entry
          </p>
          <h2 className="mt-4 font-[family-name:var(--vz-font-display)] text-2xl font-semibold text-[var(--vz-text-primary)]">
            Sign in
          </h2>
          <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
            Use your {brandName} identity provider account to continue.
          </p>
          <Button
            variant="primary"
            className="mt-6 w-full"
            onClick={() => void signIn()}
          >
            Sign in
          </Button>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-[var(--vz-text-muted)]">
          <span>Secure, private, and compliant.</span>
          <span>Your data stays protected.</span>
        </footer>
      </div>
    </main>
  );
}
