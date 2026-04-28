import { OmniSightField } from "@/components/brand/OmniSightField";
import { ProductLockup } from "@/components/layout/ProductLockup";
import { Button } from "@/components/ui/button";
import { productBrand } from "@/brand/product";
import { useAuthStore } from "@/stores/auth-store";

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);
  const brandName = productBrand.name;

  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_50%_20%,rgba(110,189,255,0.22),transparent_28%),linear-gradient(180deg,var(--argus-canvas)_0%,var(--argus-canvas-raise)_48%,#121927_100%)] px-6 py-10 text-[var(--argus-text)]">
      <OmniSightField variant="entry" className="opacity-95" />
      <div className="relative z-10 mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-10 lg:grid-cols-[minmax(0,1.08fr)_minmax(340px,408px)]">
        <section className="max-w-2xl space-y-7">
          <ProductLockup className="h-14 w-auto" />
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--argus-text-muted)]">
              {productBrand.descriptor}
            </p>
            <h1 className="text-4xl font-semibold tracking-[0.01em] text-[var(--argus-text)] sm:text-6xl">
              OmniSight for every live environment.
            </h1>
            <p className="max-w-xl text-lg leading-8 text-[var(--argus-text-muted)]">
              {brandName} connects scenes, models, events, evidence, and edge operations
              into one spatial intelligence layer.
            </p>
          </div>
        </section>
        <section className="w-full rounded-[1.35rem] border border-[color:var(--argus-border-strong)] bg-[color:var(--vezor-surface-depth)] p-6 text-[var(--argus-text)] shadow-[var(--vezor-shadow-depth)] backdrop-blur-xl sm:p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--argus-text-muted)]">
            Secure entry
          </p>
          <h2 className="mt-4 text-2xl font-semibold text-[var(--argus-text)]">Sign in</h2>
          <p className="mt-2 text-sm text-[var(--argus-text-muted)]">
            Use your {brandName} identity provider account to continue.
          </p>
          <Button
            className="mt-6 w-full border-transparent bg-[linear-gradient(135deg,var(--vezor-lens-cerulean)_0%,var(--vezor-lens-violet)_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:border-transparent hover:brightness-110"
            onClick={() => void signIn()}
          >
            Sign in
          </Button>
        </section>
      </div>
    </main>
  );
}
