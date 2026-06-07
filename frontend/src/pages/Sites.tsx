import { useEffect, useMemo, useState } from "react";

import { RequireRole } from "@/components/auth/RequireRole";
import {
  WorkspaceBand,
  WorkspaceSurface,
} from "@/components/layout/workspace-surfaces";
import { SiteDialog } from "@/components/sites/SiteDialog";
import { Button } from "@/components/ui/button";
import { productBrand } from "@/brand/product";
import { useCameras } from "@/hooks/use-cameras";
import {
  useCreateSite,
  useDeleteSite,
  useSites,
  useUpdateSite,
  type Site,
} from "@/hooks/use-sites";

const sitePageSizeOptions = [10, 25, 50] as const;
type SitePageSize = (typeof sitePageSizeOptions)[number];
type SiteDialogState =
  | { mode: "create"; site: null }
  | { mode: "edit"; site: Site };

export function SitesPage() {
  return (
    <RequireRole role="admin">
      <SitesContent />
    </RequireRole>
  );
}

function SitesContent() {
  const brandName = productBrand.name;
  const [dialogState, setDialogState] = useState<SiteDialogState | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [siteSearch, setSiteSearch] = useState("");
  const [pageSize, setPageSize] = useState<SitePageSize>(10);
  const [pageIndex, setPageIndex] = useState(0);
  const { data: sites = [], isLoading } = useSites();
  const { data: cameras = [] } = useCameras();
  const createSite = useCreateSite();
  const updateSite = useUpdateSite();
  const deleteSite = useDeleteSite();
  const sceneCountBySite = useMemo(() => {
    const counts = new Map<string, number>();
    for (const camera of cameras) {
      counts.set(camera.site_id, (counts.get(camera.site_id) ?? 0) + 1);
    }
    return counts;
  }, [cameras]);
  const filteredSites = useMemo(
    () => filterSites(sites, siteSearch),
    [siteSearch, sites],
  );
  const pageCount = Math.max(1, Math.ceil(filteredSites.length / pageSize));
  const currentPageIndex = Math.min(pageIndex, pageCount - 1);
  const visibleSites = filteredSites.slice(
    currentPageIndex * pageSize,
    currentPageIndex * pageSize + pageSize,
  );

  useEffect(() => {
    setPageIndex(0);
  }, [pageSize, siteSearch]);

  async function handleDeleteSite(site: Site) {
    if (!window.confirm(`Delete ${site.name}? This cannot be undone.`)) {
      return;
    }

    setDeleteError(null);
    try {
      await deleteSite.mutateAsync(site.id);
    } catch (error) {
      setDeleteError(
        error instanceof Error ? error.message : "Unable to delete site.",
      );
    }
  }

  return (
    <div data-testid="sites-workspace" className="space-y-5 p-4 sm:p-6">
      <WorkspaceBand
        eyebrow="Sites"
        title="Deployment Sites"
        description={`Sites anchor deployment locations, time zones, scene context, and edge fleet planning across ${brandName}.`}
        actions={
          <Button
            onClick={() => setDialogState({ mode: "create", site: null })}
          >
            Add site
          </Button>
        }
      />

      {deleteError ? (
        <WorkspaceSurface className="border-[#5a2330] bg-[#241118] px-4 py-3 text-sm text-[#ffc2cd]">
          {deleteError}
        </WorkspaceSurface>
      ) : null}

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
            onClick={() => setDialogState({ mode: "create", site: null })}
          >
            Add site
          </Button>
        </section>
      ) : (
        <section data-testid="site-context-grid" className="space-y-4">
          <WorkspaceSurface className="p-4">
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto_auto] md:items-end">
              <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
                  Search
                </span>
                <input
                  aria-label="Search sites"
                  className="w-full rounded-[0.5rem] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-obsidian)] px-3 py-2.5 text-sm text-[var(--vz-text-primary)] outline-none transition placeholder:text-[var(--vz-text-muted)] focus:border-[color:var(--vz-hair-focus)] focus:ring-2 focus:ring-[color:var(--vz-hair-focus)]/25"
                  placeholder="Search site, timezone, or description"
                  value={siteSearch}
                  onChange={(event) => setSiteSearch(event.target.value)}
                />
              </label>
              <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
                  Page size
                </span>
                <select
                  aria-label="Sites per page"
                  className="rounded-[0.5rem] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-obsidian)] px-3 py-2.5 text-sm text-[var(--vz-text-primary)] outline-none transition focus:border-[color:var(--vz-hair-focus)] focus:ring-2 focus:ring-[color:var(--vz-hair-focus)]/25"
                  value={pageSize}
                  onChange={(event) =>
                    setPageSize(Number(event.target.value) as SitePageSize)
                  }
                >
                  {sitePageSizeOptions.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <p className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-2 text-sm font-medium text-[var(--vz-text-secondary)]">
                {filteredSites.length === 0
                  ? "0 sites"
                  : `${currentPageIndex * pageSize + 1}-${Math.min(
                      (currentPageIndex + 1) * pageSize,
                      filteredSites.length,
                    )} of ${filteredSites.length} sites`}
              </p>
            </div>
          </WorkspaceSurface>
          <WorkspaceSurface className="hidden overflow-hidden md:block">
            <table className="min-w-full text-sm">
              <thead className="border-b border-[color:var(--vz-hair)] text-left text-[11px] uppercase tracking-[0.18em] text-[var(--vz-text-muted)]">
                <tr>
                  <th className="px-4 py-3 font-semibold">Site</th>
                  <th className="px-4 py-3 font-semibold">Timezone</th>
                  <th className="px-4 py-3 font-semibold">Scenes</th>
                  <th className="px-4 py-3 font-semibold">Description</th>
                  <th className="px-4 py-3 text-right font-semibold">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--vz-hair)]">
                {visibleSites.length === 0 ? (
                  <tr>
                    <td
                      colSpan={5}
                      className="px-4 py-6 text-[var(--vz-text-secondary)]"
                    >
                      No sites match this search.
                    </td>
                  </tr>
                ) : (
                  visibleSites.map((site) => {
                    const sceneCount = sceneCountBySite.get(site.id) ?? 0;
                    return (
                      <tr
                        key={site.id}
                        className="transition hover:bg-white/[0.03]"
                      >
                        <th
                          scope="row"
                          className="px-4 py-4 text-left font-[family-name:var(--vz-font-display)] text-lg font-semibold text-[var(--vz-text-primary)]"
                        >
                          {site.name}
                        </th>
                        <td className="px-4 py-4 text-[var(--vz-text-secondary)]">
                          {site.tz}
                        </td>
                        <td className="px-4 py-4 text-[var(--vz-text-primary)]">
                          {sceneCount} {sceneCount === 1 ? "scene" : "scenes"}
                        </td>
                        <td className="px-4 py-4 text-[var(--vz-text-muted)]">
                          {site.description ?? "No description"}
                        </td>
                        <td className="px-4 py-4 text-right">
                          <div className="flex justify-end gap-2">
                            <button
                              aria-label={`Edit ${site.name}`}
                              className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                              type="button"
                              onClick={() =>
                                setDialogState({ mode: "edit", site })
                              }
                            >
                              Edit
                            </button>
                            <button
                              className="rounded-full border border-[#5a2330] bg-[#241118] px-3 py-1.5 text-xs font-medium text-[#ffc2cd] transition hover:bg-[#311722] disabled:cursor-not-allowed disabled:opacity-60"
                              disabled={deleteSite.isPending}
                              type="button"
                              onClick={() => void handleDeleteSite(site)}
                            >
                              Delete site
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </WorkspaceSurface>

          <div className="grid gap-4 md:hidden">
            {visibleSites.length === 0 ? (
              <WorkspaceSurface className="p-4 text-sm text-[var(--vz-text-secondary)]">
                No sites match this search.
              </WorkspaceSurface>
            ) : (
              visibleSites.map((site) => {
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
                    <div className="mt-4 flex justify-end gap-2">
                      <button
                        aria-label={`Edit ${site.name}`}
                        className="rounded-full border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-medium text-[#d8e2f2] transition hover:bg-white/[0.08]"
                        type="button"
                        onClick={() => setDialogState({ mode: "edit", site })}
                      >
                        Edit
                      </button>
                      <button
                        className="rounded-full border border-[#5a2330] bg-[#241118] px-3 py-1.5 text-xs font-medium text-[#ffc2cd] transition hover:bg-[#311722] disabled:cursor-not-allowed disabled:opacity-60"
                        disabled={deleteSite.isPending}
                        type="button"
                        onClick={() => void handleDeleteSite(site)}
                      >
                        Delete site
                      </button>
                    </div>
                  </WorkspaceSurface>
                );
              })
            )}
          </div>
          {filteredSites.length > pageSize ? (
            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                className="rounded-full border border-[color:var(--vz-hair)] px-3 py-1.5 text-sm text-[var(--vz-text-secondary)] transition hover:text-[var(--vz-text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={currentPageIndex === 0}
                type="button"
                onClick={() =>
                  setPageIndex((current) => Math.max(0, current - 1))
                }
              >
                Previous
              </button>
              <span className="text-sm text-[var(--vz-text-secondary)]">
                Page {currentPageIndex + 1} of {pageCount}
              </span>
              <button
                className="rounded-full border border-[color:var(--vz-hair)] px-3 py-1.5 text-sm text-[var(--vz-text-secondary)] transition hover:text-[var(--vz-text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
                disabled={currentPageIndex >= pageCount - 1}
                type="button"
                onClick={() =>
                  setPageIndex((current) =>
                    Math.min(pageCount - 1, current + 1),
                  )
                }
              >
                Next
              </button>
            </div>
          ) : null}
        </section>
      )}

      <SiteDialog
        mode={dialogState?.mode ?? "create"}
        open={dialogState !== null}
        site={dialogState?.site ?? null}
        onClose={() => setDialogState(null)}
        onSubmit={async (payload) => {
          if (dialogState?.mode === "edit") {
            await updateSite.mutateAsync({
              siteId: dialogState.site.id,
              payload,
            });
          } else {
            await createSite.mutateAsync(payload);
          }
          setDialogState(null);
        }}
      />
    </div>
  );
}

function filterSites(sites: Site[], searchValue: string) {
  const query = searchValue.trim().toLowerCase();
  if (!query) {
    return sites;
  }
  const tokens = query.split(/\s+/);

  return sites.filter((site) => {
    const haystack = [site.name, site.tz, site.description ?? ""]
      .join(" ")
      .toLowerCase();
    return tokens.every((token) => haystack.includes(token));
  });
}
