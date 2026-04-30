import { useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { productBrand } from "@/brand/product";
import { omniEmptyStates } from "@/copy/omnisight";
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

      <section data-testid="site-context-grid" className="grid gap-4 lg:grid-cols-3">
        {sites.map((site) => {
          const sceneCount = sceneCountBySite.get(site.id) ?? 0;
          return (
            <WorkspaceSurface key={site.id} className="p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8ea8cf]">
                Deployment location
              </p>
              <h2 className="mt-2 text-xl font-semibold text-[#f4f8ff]">
                {site.name}
              </h2>
              <p className="mt-2 text-sm text-[#9eb0cb]">{site.tz}</p>
              <p className="mt-3 text-sm font-medium text-[#dce6f7]">
                {sceneCount} {sceneCount === 1 ? "scene" : "scenes"}
              </p>
              {site.description ? (
                <p className="mt-2 text-sm text-[#8fa4c4]">
                  {site.description}
                </p>
              ) : null}
            </WorkspaceSurface>
          );
        })}
      </section>

      <section className="overflow-hidden rounded-[0.9rem] border border-white/8 bg-[#0b1320]">
        <Table>
          <THead>
            <TR>
              <TH>Name</TH>
              <TH>Time zone</TH>
              <TH>Description</TH>
            </TR>
          </THead>
          <TBody>
            {isLoading ? (
              <TR>
                <TD colSpan={3} className="text-[#9eb2cf]">
                  Loading sites...
                </TD>
              </TR>
            ) : sites.length === 0 ? (
              <TR>
                <TD colSpan={3} className="text-[#9eb2cf]">
                  {omniEmptyStates.noSites}
                </TD>
              </TR>
            ) : (
              sites.map((site) => (
                <TR key={site.id}>
                  <TD className="font-medium text-[#eef4ff]">{site.name}</TD>
                  <TD>{site.tz}</TD>
                  <TD>{site.description ?? "—"}</TD>
                </TR>
              ))
            )}
          </TBody>
        </Table>
      </section>

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
