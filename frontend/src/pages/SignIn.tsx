import { useAuthStore } from "@/stores/auth-store";

export function SignInPage() {
  const signIn = useAuthStore((state) => state.signIn);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(43,117,255,0.18),_transparent_32%),radial-gradient(circle_at_85%_15%,_rgba(136,92,255,0.18),_transparent_28%),linear-gradient(180deg,#05070c_0%,#0b1018_46%,#121927_100%)] px-6 py-10 text-[#eef4ff]">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-6xl items-center justify-between gap-8 rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,20,31,0.94),rgba(8,11,18,0.9))] p-8 shadow-[0_36px_120px_-48px_rgba(31,111,255,0.55)] backdrop-blur-xl">
        <section className="max-w-2xl space-y-5">
          <p className="text-xs font-semibold uppercase tracking-[0.34em] text-[#b7c8e6]">
            Argus | The OmniSight Platform
          </p>
          <h1 className="text-5xl font-semibold tracking-[0.01em] text-[#f7f9ff]">
            Vigilant intelligence, fleet-wide.
          </h1>
          <p className="text-lg text-[#a8b5cc]">
            Monitor cameras, manage configuration, and operate Argus from a premium
            command center built for continuous observation.
          </p>
        </section>
        <section className="w-full max-w-sm rounded-[1.75rem] border border-[#1f2d46] bg-[linear-gradient(180deg,rgba(10,15,24,0.98),rgba(19,26,40,0.96))] p-6 text-[#eef4ff] shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
          <h2 className="text-2xl font-semibold text-[#f7f9ff]">Sign in</h2>
          <p className="mt-2 text-sm text-[#96a7c2]">
            Use your Argus identity provider account to continue.
          </p>
          <button
            type="button"
            className="mt-6 w-full rounded-full bg-[linear-gradient(135deg,#3b82f6_0%,#8b5cf6_100%)] px-4 py-3 text-sm font-medium text-white shadow-[0_18px_42px_-22px_rgba(92,111,255,0.95)] transition hover:brightness-110"
            onClick={() => void signIn()}
          >
            Sign in
          </button>
        </section>
      </div>
    </main>
  );
}
