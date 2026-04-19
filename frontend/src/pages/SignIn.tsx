import { ProductLockup } from "@/components/layout/ProductLockup";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(43,117,255,0.18),_transparent_32%),radial-gradient(circle_at_85%_15%,_rgba(136,92,255,0.16),_transparent_28%),linear-gradient(180deg,var(--argus-canvas)_0%,var(--argus-canvas-raise)_48%,#121927_100%)] px-6 py-10 text-[var(--argus-text)]">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-10 rounded-[2rem] border border-[color:var(--argus-border)] bg-[linear-gradient(180deg,var(--argus-surface),rgba(8,12,20,0.94))] p-8 shadow-[0_36px_120px_-54px_rgba(0,0,0,0.88)] backdrop-blur-xl lg:grid-cols-[minmax(0,1.1fr)_minmax(340px,408px)] lg:p-10">
        <section className="max-w-2xl space-y-6">
          <ProductLockup className="h-14 w-auto" />
          <div className="space-y-5">
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--argus-text-muted)]">
              Unified observability workspace
            </p>
            <h1 className="text-4xl font-semibold tracking-[0.01em] text-[var(--argus-text)] sm:text-5xl">
              Vigilant intelligence, fleet-wide.
            </h1>
            <p className="max-w-xl text-lg text-[var(--argus-text-muted)]">
              Monitor cameras, manage configuration, and operate Argus from a premium
              command center built for continuous observation.
            </p>
          </div>
        </section>
        <section className="w-full rounded-[1.75rem] border border-[color:var(--argus-border-strong)] bg-[linear-gradient(180deg,rgba(13,18,28,0.98),rgba(20,27,41,0.96))] p-6 text-[var(--argus-text)] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] sm:p-7">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-[var(--argus-text-muted)]">
            Secure entry
          </p>
          <h2 className="mt-4 text-2xl font-semibold text-[var(--argus-text)]">Sign in</h2>
          <p className="mt-2 text-sm text-[var(--argus-text-muted)]">
            Use your Argus identity provider account to continue.
          </p>
          <Button
            className="mt-6 w-full border-transparent bg-[linear-gradient(135deg,#35b8ff_0%,#6d84ff_100%)] text-[#06111a] shadow-[0_18px_38px_-24px_rgba(53,184,255,0.55)] hover:border-transparent hover:brightness-110"
            onClick={() => void signIn()}
          >
            Sign in
          </Button>
        </section>
      </div>
    </main>
  );
}
