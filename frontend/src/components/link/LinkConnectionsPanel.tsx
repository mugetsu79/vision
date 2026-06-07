import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";

import { LinkConnectionDialog } from "@/components/link/LinkActionDialogs";
import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  useCreateLinkConnection,
  useDeleteLinkConnection,
  useUpdateLinkConnection,
  type LinkConnectionCreateInput,
  type LinkConnectionPatchInput,
} from "@/hooks/use-link";
import {
  asRecord,
  linkModelLabel,
  linkPathMetadata,
  linkVisibilityLabel,
  textValue,
  type LinkTargetSiteOption,
} from "@/components/link/types";

type LinkConnectionsPanelProps = {
  siteId?: string | null;
  connections: unknown[];
  targetSiteOptions?: LinkTargetSiteOption[];
};

type ConnectionDialogState =
  | { mode: "create"; connection?: undefined }
  | { mode: "edit"; connection: unknown };

export function LinkConnectionsPanel({
  siteId,
  connections,
  targetSiteOptions = [],
}: LinkConnectionsPanelProps) {
  const [dialog, setDialog] = useState<ConnectionDialogState | null>(null);
  const createConnection = useCreateLinkConnection({ siteId });
  const updateConnection = useUpdateLinkConnection({ siteId });
  const deleteConnection = useDeleteLinkConnection({ siteId });

  async function handleSubmit(
    payload: LinkConnectionCreateInput | LinkConnectionPatchInput,
  ) {
    if (dialog?.mode === "edit") {
      const connectionId = textValue(asRecord(dialog.connection).id, "");
      if (connectionId) {
        await updateConnection.mutateAsync({
          connectionId,
          payload,
        });
      }
      return;
    }
    await createConnection.mutateAsync(payload as LinkConnectionCreateInput);
  }

  async function handleDelete(connection: unknown) {
    const connectionId = textValue(asRecord(connection).id, "");
    if (connectionId) {
      await deleteConnection.mutateAsync(connectionId);
    }
  }

  return (
    <WorkspaceSurface className="p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
          Link paths
        </h2>
        <Button
          onClick={() => setDialog({ mode: "create" })}
          disabled={!siteId}
        >
          <Plus className="mr-2 size-4" aria-hidden="true" />
          Add link path
        </Button>
      </div>
      <div className="mt-4 grid gap-2">
        {connections.length === 0 ? (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            No link paths recorded.
          </p>
        ) : (
          connections.map((connection, index) => {
            const item = asRecord(connection);
            const id = textValue(item.id, `connection-${index}`);
            const metadata = linkPathMetadata(item.metadata);
            const externalReference = textValue(metadata.external_reference, "");
            const provider = textValue(item.provider, "");
            const targetCount = metadata.monitoring_targets.length;
            return (
              <div
                key={id}
                className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3"
              >
                <p className="font-medium text-[var(--vz-text-primary)]">
                  {textValue(item.label)}
                </p>
                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
                  {linkModelLabel(metadata.link_model)} /{" "}
                  {linkVisibilityLabel(metadata.visibility)} /{" "}
                  {textValue(item.status, "unknown")} /{" "}
                  {item.metered === true ? "metered" : "unmetered"}
                </p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-[var(--vz-text-secondary)]">
                  <span>{textValue(item.transport_kind, "unknown")}</span>
                  {provider ? <span>{provider}</span> : null}
                  {externalReference ? <span>{externalReference}</span> : null}
                  <span>
                    {targetCount} monitoring{" "}
                    {targetCount === 1 ? "target" : "targets"}
                  </span>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    variant="ghost"
                    onClick={() =>
                      setDialog({ mode: "edit", connection })
                    }
                    aria-label={`Edit ${textValue(item.label, id)}`}
                  >
                    <Pencil className="mr-2 size-4" aria-hidden="true" />
                    Edit
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => void handleDelete(connection)}
                    aria-label={`Delete ${textValue(item.label, id)}`}
                  >
                    <Trash2 className="mr-2 size-4" aria-hidden="true" />
                    Delete
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>
      <LinkConnectionDialog
        open={dialog !== null}
        mode={dialog?.mode ?? "create"}
        connection={dialog?.connection}
        targetSiteOptions={targetSiteOptions}
        isSubmitting={createConnection.isPending || updateConnection.isPending}
        onClose={() => setDialog(null)}
        onSubmit={handleSubmit}
      />
    </WorkspaceSurface>
  );
}
