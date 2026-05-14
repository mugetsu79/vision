import { type FormEvent, type ReactNode, useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2, ShieldCheck } from "lucide-react";

import { ProductLockup } from "@/components/layout/ProductLockup";
import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useBootstrapStatus, useCompleteBootstrap } from "@/hooks/use-bootstrap";

export function FirstRunPage() {
  const navigate = useNavigate();
  const bootstrapStatus = useBootstrapStatus();
  const completeBootstrap = useCompleteBootstrap();
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [adminEmail, setAdminEmail] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [centralNodeName, setCentralNodeName] = useState("");
  const [centralSupervisorId, setCentralSupervisorId] = useState("");

  const ready = useMemo(
    () =>
      Boolean(
        bootstrapToken.trim() &&
          tenantName.trim() &&
          adminEmail.trim() &&
          adminPassword.trim() &&
          centralNodeName.trim(),
      ),
    [adminEmail, adminPassword, bootstrapToken, centralNodeName, tenantName],
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ready) {
      return;
    }
    await completeBootstrap.mutateAsync({
      bootstrap_token: bootstrapToken.trim(),
      tenant_name: tenantName.trim(),
      tenant_slug: undefined,
      admin_email: adminEmail.trim(),
      admin_password: adminPassword,
      central_node_name: centralNodeName.trim(),
      central_supervisor_id: centralSupervisorId.trim() || undefined,
    });
    navigate("/signin", { replace: true });
  }

  if (bootstrapStatus.isLoading) {
    return (
      <main className="min-h-screen bg-[var(--vz-canvas-obsidian)] p-6 text-[var(--vz-text-primary)]">
        <WorkspaceSurface className="mx-auto mt-16 max-w-xl p-5 text-sm text-[var(--vz-text-secondary)]">
          Checking first-run status...
        </WorkspaceSurface>
      </main>
    );
  }

  if (!bootstrapStatus.data?.first_run_required) {
    return <Navigate to="/signin" replace />;
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,var(--vz-canvas-void)_0%,var(--vz-canvas-obsidian)_100%)] px-5 py-6 text-[var(--vz-text-primary)]">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col gap-6">
        <header className="flex items-center justify-between gap-4">
          <ProductLockup className="h-11 w-auto" />
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
            <ShieldCheck className="size-4" aria-hidden="true" />
            First run
          </div>
        </header>

        <section className="grid flex-1 items-center gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(24rem,1fr)]">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
              Local bootstrap
            </p>
            <h1 className="mt-3 font-[family-name:var(--vz-font-display)] text-3xl font-semibold tracking-normal text-[var(--vz-text-primary)] sm:text-4xl">
              First-run setup
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-[var(--vz-text-secondary)]">
              Create the first tenant, administrator identity, and central
              deployment node for this installed master.
            </p>
          </div>

          <WorkspaceSurface className="p-5 sm:p-6">
            <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
              <Field label="Bootstrap code" htmlFor="bootstrap-token">
                <Input
                  id="bootstrap-token"
                  autoComplete="one-time-code"
                  value={bootstrapToken}
                  onChange={(event) => setBootstrapToken(event.target.value)}
                />
              </Field>
              <Field label="Tenant name" htmlFor="tenant-name">
                <Input
                  id="tenant-name"
                  value={tenantName}
                  onChange={(event) => setTenantName(event.target.value)}
                />
              </Field>
              <Field label="Admin email" htmlFor="admin-email">
                <Input
                  id="admin-email"
                  type="email"
                  autoComplete="email"
                  value={adminEmail}
                  onChange={(event) => setAdminEmail(event.target.value)}
                />
              </Field>
              <Field label="Admin password" htmlFor="admin-password">
                <Input
                  id="admin-password"
                  type="password"
                  autoComplete="new-password"
                  value={adminPassword}
                  onChange={(event) => setAdminPassword(event.target.value)}
                />
              </Field>
              <Field label="Master node name" htmlFor="central-node-name">
                <Input
                  id="central-node-name"
                  value={centralNodeName}
                  onChange={(event) => setCentralNodeName(event.target.value)}
                />
              </Field>
              <Field label="Supervisor id" htmlFor="central-supervisor-id">
                <Input
                  id="central-supervisor-id"
                  value={centralSupervisorId}
                  onChange={(event) => setCentralSupervisorId(event.target.value)}
                />
              </Field>

              {completeBootstrap.isError ? (
                <p className="rounded-[var(--vz-r-md)] border border-red-400/35 bg-red-950/30 px-3 py-2 text-sm text-red-100">
                  {completeBootstrap.error.message}
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
                Complete setup
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
    <label className="block text-sm font-medium text-[var(--vz-text-secondary)]" htmlFor={htmlFor}>
      <span className="mb-2 block">{label}</span>
      {children}
    </label>
  );
}
