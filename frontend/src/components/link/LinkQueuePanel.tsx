import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import {
  usePauseLinkQueueItem,
  useResumeLinkQueueItem,
  useRetryLinkQueueItem,
} from "@/hooks/use-link";
import { asRecord, numberValue, textValue } from "@/components/link/types";

type LinkQueuePanelProps = {
  siteId?: string | null;
  queue: unknown[];
};

export function LinkQueuePanel({ siteId, queue }: LinkQueuePanelProps) {
  const retryQueueItem = useRetryLinkQueueItem({ siteId });
  const pauseQueueItem = usePauseLinkQueueItem({ siteId });
  const resumeQueueItem = useResumeLinkQueueItem({ siteId });

  return (
    <WorkspaceSurface className="p-5">
      <h2 className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
        Transfer queue
      </h2>
      <div className="mt-4 grid gap-2">
        {queue.length === 0 ? (
          <p className="text-sm text-[var(--vz-text-secondary)]">
            No queued link work.
          </p>
        ) : (
          queue.map((queueItem, index) => {
            const item = asRecord(queueItem);
            const id = textValue(item.id, `queue-${index}`);
            const lane = textValue(item.priority_lane, "bulk");
            const status = textValue(item.status, "queued").toLowerCase();
            return (
              <div
                key={id}
                className="rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-3 text-sm text-[var(--vz-text-secondary)]"
              >
                <div>
                  <span className="font-medium text-[var(--vz-text-primary)]">
                    {lane}
                  </span>{" "}
                  {status} / {numberValue(item.byte_size).toLocaleString()} bytes
                  / {textValue(item.source_object_type)}
                </div>
                {item.pause_reason ? (
                  <p className="mt-2 text-xs text-[var(--vz-text-muted)]">
                    Pause reason: {textValue(item.pause_reason)}
                  </p>
                ) : null}
                {item.last_successful_transfer_at ? (
                  <p className="mt-2 text-xs text-[var(--vz-text-muted)]">
                    Last transfer: {textValue(item.last_successful_transfer_at)}
                  </p>
                ) : null}
                <div className="mt-3 flex flex-wrap gap-2">
                  {status === "queued" || status === "failed" ? (
                    <Button
                      variant="ghost"
                      onClick={() => void retryQueueItem.mutateAsync(id)}
                      aria-label={`Retry ${lane} queue item`}
                    >
                      Retry
                    </Button>
                  ) : null}
                  {status === "queued" ? (
                    <Button
                      variant="ghost"
                      onClick={() => void pauseQueueItem.mutateAsync(id)}
                      aria-label={`Pause ${lane} queue item`}
                    >
                      Pause
                    </Button>
                  ) : null}
                  {status === "paused" ? (
                    <Button
                      variant="ghost"
                      onClick={() => void resumeQueueItem.mutateAsync(id)}
                      aria-label={`Resume ${lane} queue item`}
                    >
                      Resume
                    </Button>
                  ) : null}
                </div>
              </div>
            );
          })
        )}
      </div>
    </WorkspaceSurface>
  );
}
