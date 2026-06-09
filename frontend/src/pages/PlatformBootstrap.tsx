import { type FormEvent, type ReactNode, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";

import { ProductLockup } from "@/components/layout/ProductLockup";
import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  useCompletePlatformBootstrap,
  usePlatformBootstrapStatus,
} from "@/hooks/use-platform-bootstrap";

export function PlatformBootstrapPage() {
  const navigate = useNavigate();
  const bootstrapStatus = usePlatformBootstrapStatus();
  const completeBootstrap = useCompletePlatformBootstrap();
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [email, setEmail] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [password, setPassword] = useState("");

  const ready = useMemo(
    () =>
      Boolean(
        bootstrapToken.trim() &&
        email.trim() &&
        firstName.trim() &&
        lastName.trim() &&
        password,
      ),
    [bootstrapToken, email, firstName, lastName, password],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) {
      return;
    }

    await completeBootstrap.mutateAsync({
      bootstrap_token: bootstrapToken.trim(),
      email: email.trim(),
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      password,
    });
    navigate("/signin", { replace: true });
  }

  if (bootstrapStatus.isLoading) {
    return (
      <main className="min-h-screen bg-[var(--vz-canvas-obsidian)] p-6 text-[var(--vz-text-primary)]">
        <WorkspaceSurface className="mx-auto mt-16 max-w-xl p-5 text-sm text-[var(--vz-text-secondary)]">
          Checking platform bootstrap status...
        </WorkspaceSurface>
      </main>
    );
  }

  if (bootstrapStatus.data && !bootstrapStatus.data.available) {
    return <Navigate to="/signin" replace />;
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,var(--vz-canvas-void)_0%,var(--vz-canvas-obsidian)_100%)] px-5 py-6 text-[var(--vz-text-primary)]">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col gap-6">
        <header className="flex items-center justify-between gap-4">
          <ProductLockup className="h-11 w-auto" />
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
            <ShieldCheck className="size-4" aria-hidden="true" />
            Platform bootstrap
          </div>
        </header>

        <section className="grid flex-1 items-center gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(24rem,1fr)]">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
              Platform identity
            </p>
            <h1 className="mt-3 font-[family-name:var(--vz-font-display)] text-3xl font-semibold tracking-normal text-[var(--vz-text-primary)] sm:text-4xl">
              Create platform admin
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-[var(--vz-text-secondary)]">
              Use the local bootstrap token to create the first platform
              superadmin account.
            </p>
          </div>

          <WorkspaceSurface className="p-5 sm:p-6">
            <form
              className="space-y-4"
              onSubmit={(event) => void handleSubmit(event)}
            >
              <Field label="Bootstrap token" htmlFor="platform-bootstrap-token">
                <Input
                  id="platform-bootstrap-token"
                  type="password"
                  autoComplete="one-time-code"
                  value={bootstrapToken}
                  onChange={(event) => setBootstrapToken(event.target.value)}
                />
              </Field>
              <Field label="Email" htmlFor="platform-admin-email">
                <Input
                  id="platform-admin-email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="First name" htmlFor="platform-admin-first-name">
                  <Input
                    id="platform-admin-first-name"
                    autoComplete="given-name"
                    value={firstName}
                    onChange={(event) => setFirstName(event.target.value)}
                  />
                </Field>
                <Field label="Last name" htmlFor="platform-admin-last-name">
                  <Input
                    id="platform-admin-last-name"
                    autoComplete="family-name"
                    value={lastName}
                    onChange={(event) => setLastName(event.target.value)}
                  />
                </Field>
              </div>
              <Field label="Password" htmlFor="platform-admin-password">
                <Input
                  id="platform-admin-password"
                  type="password"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </Field>

              {completeBootstrap.isError ? (
                <p className="rounded-[var(--vz-r-md)] border border-red-400/35 bg-red-950/30 px-3 py-2 text-sm text-red-100">
                  Could not create platform admin. Check the bootstrap token and
                  account fields, then try again.
                </p>
              ) : null}

              <Button
                type="submit"
                variant="primary"
                className="w-full"
                disabled={!ready || completeBootstrap.isPending}
              >
                {completeBootstrap.isPending ? (
                  <Loader2 className="mr-2 size-4 animate-spin" />
                ) : (
                  <CheckCircle2 className="mr-2 size-4" />
                )}
                Create platform admin
              </Button>
            </form>
          </WorkspaceSurface>
        </section>
      </div>
    </main>
  );
}

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: ReactNode;
}) {
  return (
    <label
      className="block text-sm font-medium text-[var(--vz-text-secondary)]"
      htmlFor={htmlFor}
    >
      <span className="mb-2 block">{label}</span>
      {children}
    </label>
  );
}
