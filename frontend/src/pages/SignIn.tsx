import { OmniSightField } from "@/components/brand/OmniSightField";
import { ProductLockup } from "@/components/layout/ProductLockup";
import { Button } from "@/components/ui/button";
import { productBrand } from "@/brand/product";
import { useAuthStore } from "@/stores/auth-store";

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);
  const brandName = productBrand.name;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_74%_42%,rgba(110,189,255,0.18),transparent_28%),linear-gradient(180deg,var(--vezor-canvas-obsidian)_0%,#080d15_52%,#10141d_100%)] px-6 py-8 text-[var(--argus-text)]">
      <div
        className="absolute inset-0"
        data-testid="signin-lens-stage"
      >
        <OmniSightField variant="stage" className="opacity-95" />
        <div className="signin-lens-glint pointer-events-none absolute right-[18%] top-[38%] h-28 w-28 rounded-full" />
      </div>

      <div
        className="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-7xl grid-rows-[auto_1fr_auto] gap-8"
      >
        <header className="flex items-center justify-between">
          <ProductLockup className="h-12 w-auto" />
          <p className="hidden text-[11px] font-semibold uppercase tracking-[0.24em] text-[#7f94b5] sm:block">
            Spatial intelligence layer
          </p>
        </header>

        <section className="grid items-center gap-8 pt-32 sm:pt-40 lg:grid-cols-[minmax(0,0.84fr)_minmax(360px,0.72fr)] lg:pt-0">
          <div className="max-w-2xl space-y-6 lg:pb-20">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--argus-text-muted)]">
              {productBrand.descriptor}
            </p>
            <h1 className="max-w-3xl text-4xl font-semibold tracking-normal text-[var(--argus-text)] sm:text-6xl lg:text-7xl">
              OmniSight for every live environment.
            </h1>
            <p className="max-w-xl text-lg leading-8 text-[var(--argus-text-muted)]">
              {brandName} connects scenes, models, events, evidence, and edge
              operations into one spatial intelligence layer.
            </p>
            <ul className="grid max-w-xl gap-3 text-sm text-[#dbe8fb] sm:grid-cols-3">
              {["Scenes", "Evidence", "Operations"].map((label) => (
                <li key={label} className="flex items-center gap-3">
                  <span className="h-2 w-2 rounded-full bg-[var(--vezor-lens-aqua)] shadow-[0_0_18px_rgba(118,224,255,0.62)]" />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#9db7dc]">
                    {label}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <section
            data-testid="signin-auth-panel"
            className="ml-auto w-full max-w-[25rem] rounded-[0.95rem] border border-white/[0.12] bg-[linear-gradient(180deg,rgba(10,15,25,0.94),rgba(5,8,14,0.92))] p-6 text-[var(--argus-text)] shadow-[0_32px_90px_-62px_rgba(73,126,255,0.72)] backdrop-blur-xl sm:p-7 lg:mt-64"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--argus-text-muted)]">
              Secure entry
            </p>
            <h2 className="mt-4 text-2xl font-semibold text-[var(--argus-text)]">
              Sign in
            </h2>
            <p className="mt-2 text-sm text-[var(--argus-text-muted)]">
              Use your {brandName} identity provider account to continue.
            </p>
            <Button
              className="mt-6 w-full border-transparent bg-[linear-gradient(135deg,var(--vezor-lens-cerulean)_0%,#79a7ff_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:border-transparent hover:brightness-110"
              onClick={() => void signIn()}
            >
              Sign in
            </Button>
          </section>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-4 text-sm text-[#8397b8]">
          <span>Secure, private, and compliant.</span>
          <span>Your data stays protected.</span>
        </footer>
      </div>
    </main>
  );
}
