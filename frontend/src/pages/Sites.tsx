import { useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { Button } from "@/components/ui/button";
import { productBrand } from "@/brand/product";
import { useCameras } from "@/hooks/use-cameras";
import { useCreateSite, useSites } from "@/hooks/use-sites";

export function SitesPage() {
  return (
    <RequireRole role="admin">
      <SitesContent />
    </RequireRole>
  );
}

function SitesContent() {
  const brandName = productBrand.name;
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: sites = [], isLoading } = useSites();
  const { data: cameras = [] } = useCameras();
  const createSite = useCreateSite();
  const sceneCountBySite = new Map<string, number>();
  for (const camera of cameras) {
    sceneCountBySite.set(
      camera.site_id,
      (sceneCountBySite.get(camera.site_id) ?? 0) + 1,
    );
  }

  return (
    <div data-testid="sites-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Sites"
        title="Deployment Sites"
        description={`Sites anchor deployment locations, time zones, scene context, and edge fleet planning across ${brandName}.`}
        actions={<Button onClick={() => setDialogOpen(true)}>Add site</Button>}
      />

      {isLoading ? (
        <p className="text-sm text-[var(--vz-text-secondary)]">
          Loading sites...
        </p>
      ) : sites.length === 0 ? (
        <section
          data-testid="sites-empty-state"
          className="rounded-[var(--vz-r-lg)] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-graphite)] px-6 py-10 text-center shadow-[var(--vz-elev-1)]"
        >
          <p className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
            No deployment sites yet
          </p>
          <p className="mx-auto mt-2 max-w-md text-sm text-[var(--vz-text-secondary)]">
            Sites anchor scenes, time zones, and edge fleet planning across{" "}
            {brandName}. Add your first deployment location to start.
          </p>
          <Button
            variant="primary"
            className="mt-5"
            onClick={() => setDialogOpen(true)}
          >
            Add site
          </Button>
        </section>
      ) : (
        <section
          data-testid="site-context-grid"
          className="grid gap-4 lg:grid-cols-3"
        >
          {sites.map((site) => {
            const sceneCount = sceneCountBySite.get(site.id) ?? 0;
            return (
              <WorkspaceSurface
                key={site.id}
                className="p-4 transition duration-200 hover:border-[color:var(--vz-hair-focus)] hover:shadow-[var(--vz-elev-2)]"
              >
                <p className="text-[11px] font-semibold uppercase tracking-normal text-[var(--vz-text-muted)]">
                  Deployment location
                </p>
                <h2 className="mt-2 font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
                  {site.name}
                </h2>
                <p className="mt-2 text-sm text-[var(--vz-text-secondary)]">
                  {site.tz}
                </p>
                <p className="mt-3 text-sm font-medium text-[var(--vz-text-primary)]">
                  {sceneCount} {sceneCount === 1 ? "scene" : "scenes"}
                </p>
                {site.description ? (
                  <p className="mt-2 text-sm text-[var(--vz-text-muted)]">
                    {site.description}
                  </p>
                ) : null}
              </WorkspaceSurface>
            );
          })}
        </section>
      )}

      <SiteDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={async (payload) => {
          await createSite.mutateAsync(payload);
          setDialogOpen(false);
        }}
      />
    </div>
  );
}
