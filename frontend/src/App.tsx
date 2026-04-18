import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

const navItems = ["Dashboard", "Live", "History", "Incidents", "Settings"];

export default function App() {
  return (
    <main className="min-h-screen px-6 py-8 text-slate-950 sm:px-10 lg:px-16">
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-6xl flex-col gap-8">
        <header className="flex flex-col gap-6 rounded-[2rem] border border-white/50 bg-white/55 px-6 py-6 backdrop-blur-xl sm:px-8">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div className="flex flex-col gap-2">
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">
                Prompt 1
              </p>
              <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
                Argus | The OmniSight Platform
              </h1>
              <p className="max-w-2xl text-base text-slate-600 sm:text-lg">
                Prompt 1 scaffold ready for backend, frontend, and infra.
              </p>
            </div>
            <div className="inline-flex items-center rounded-full border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
              Monorepo bootstrap in progress
            </div>
          </div>
          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <span
                key={item}
                className="rounded-full border border-black/10 bg-white/70 px-4 py-2 text-sm text-slate-600"
              >
                {item}
              </span>
            ))}
          </nav>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card>
            <CardHeader>
              <CardTitle>Empty shell</CardTitle>
              <CardDescription>
                The frontend baseline is live with Vite, React 19, Tailwind v4, and shadcn-style
                composition so the next prompts can build on a stable shell.
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 text-sm text-slate-700">
              <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/80 p-4">
                Dashboard grid, auth boundary, CRUD pages, and live telemetry tiles land in later
                prompts.
              </div>
              <div className="grid gap-3 sm:grid-cols-3">
                {["Backend", "Frontend", "Infra"].map((item) => (
                  <div
                    key={item}
                    className="rounded-2xl border border-black/5 bg-white/80 px-4 py-4 text-center font-medium"
                  >
                    {item}
                  </div>
                ))}
              </div>
            </CardContent>
            <CardFooter>
              <span className="text-sm text-slate-500">Ready for Prompt 2 after review</span>
            </CardFooter>
          </Card>

          <Card className="bg-slate-950 text-white">
            <CardHeader>
              <CardTitle className="text-white">Current scaffold snapshot</CardTitle>
              <CardDescription className="text-slate-300">
                Prompt 1 focuses on structure, tooling, schema, and local dev infrastructure.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-slate-200">
              <p>Backend package and Alembic wiring</p>
              <p>Strict TypeScript + Vitest frontend harness</p>
              <p>Docker Compose baseline for local services</p>
            </CardContent>
            <CardFooter>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.2em] text-slate-200">
                Scaffold only
              </span>
            </CardFooter>
          </Card>
        </section>
      </div>
    </main>
  );
}
