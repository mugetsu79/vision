import { useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { OmniSightField } from "@/components/brand/OmniSightField";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { productBrand } from "@/brand/product";
import { omniEmptyStates } from "@/copy/omnisight";
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
  const createSite = useCreateSite();

  return (
    <div data-testid="sites-workspace" className="space-y-5 p-4 sm:p-6">
      <section className="relative overflow-hidden rounded-[1rem] border border-white/10 bg-[color:var(--vezor-surface-depth)] px-5 py-5 shadow-[var(--vezor-shadow-depth)]">
        <OmniSightField variant="quiet" className="opacity-50" />
        <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
              Sites
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-normal text-[#f4f8ff]">
              Sites
            </h2>
            <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
              Sites anchor scenes, time zones, and edge fleet context across{" "}
              {brandName} operations.
            </p>
          </div>
          <Button onClick={() => setDialogOpen(true)}>Add site</Button>
        </div>
      </section>

      <section className="overflow-hidden rounded-[1rem] border border-white/8 bg-[#0b1320]">
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
