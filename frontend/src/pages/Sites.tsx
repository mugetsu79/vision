import { useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { Button } from "@/components/ui/button";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { useCreateSite, useSites } from "@/hooks/use-sites";

export function SitesPage() {
  return (
    <RequireRole role="admin">
      <SitesContent />
    </RequireRole>
  );
}

function SitesContent() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: sites = [], isLoading } = useSites();
  const createSite = useCreateSite();

  return (
    <>
      <section className="overflow-hidden rounded-[2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(13,18,29,0.95),rgba(8,11,18,0.92))] shadow-[0_24px_72px_-54px_rgba(0,0,0,0.9)]">
        <div className="border-b border-white/8 px-6 py-5">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9db3d3]">
                Sites
              </p>
              <h2 className="mt-3 text-3xl font-semibold tracking-[0.01em] text-[#f4f8ff]">
                Manage deployment locations.
              </h2>
              <p className="mt-3 max-w-3xl text-sm text-[#93a7c5]">
                Sites anchor camera placement, time zones, and the fleet context used
                throughout Vezor operations.
              </p>
            </div>
            <Button onClick={() => setDialogOpen(true)}>Add site</Button>
          </div>
        </div>

        <div className="px-6 py-6">
          <div className="overflow-hidden rounded-[1.5rem] border border-white/8 bg-[#0b1320]">
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
                      No sites yet.
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
          </div>
        </div>
      </section>

      <SiteDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={async (payload) => {
          await createSite.mutateAsync(payload);
          setDialogOpen(false);
        }}
      />
    </>
  );
}
