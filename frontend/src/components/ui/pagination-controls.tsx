import { cn } from "@/lib/utils";
import {
  getPaginationRange,
  paginationPageSizeOptions,
  type PaginationPageSize,
} from "@/components/ui/pagination";

type PaginationControlsProps = {
  className?: string;
  itemLabel: string;
  onPageIndexChange: (pageIndex: number) => void;
  onPageSizeChange: (pageSize: PaginationPageSize) => void;
  pageIndex: number;
  pageSize: PaginationPageSize;
  pageSizeLabel: string;
  totalCount: number;
};

export function PaginationControls({
  className,
  itemLabel,
  onPageIndexChange,
  onPageSizeChange,
  pageIndex,
  pageSize,
  pageSizeLabel,
  totalCount,
}: PaginationControlsProps) {
  if (totalCount <= paginationPageSizeOptions[0]) {
    return null;
  }

  const range = getPaginationRange(totalCount, pageSize, pageIndex);
  const rangeLabel =
    totalCount === 0
      ? `0 ${itemLabel}`
      : `${range.startIndex + 1}-${range.endIndex} of ${totalCount} ${itemLabel}`;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center justify-end gap-2 text-sm text-[var(--vz-text-secondary)]",
        className,
      )}
    >
      <label className="flex items-center gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--vz-text-muted)]">
          Per page
        </span>
        <select
          aria-label={pageSizeLabel}
          className="rounded-[0.5rem] border border-[color:var(--vz-hair)] bg-[color:var(--vz-canvas-obsidian)] px-2.5 py-1.5 text-sm text-[var(--vz-text-primary)] outline-none transition focus:border-[color:var(--vz-hair-focus)] focus:ring-2 focus:ring-[color:var(--vz-hair-focus)]/25"
          value={pageSize}
          onChange={(event) => {
            onPageSizeChange(
              Number(event.currentTarget.value) as PaginationPageSize,
            );
          }}
        >
          {paginationPageSizeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </label>
      <span className="rounded-full border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-1.5 font-medium">
        {rangeLabel}
      </span>
      <button
        className="rounded-full border border-[color:var(--vz-hair)] px-3 py-1.5 transition hover:text-[var(--vz-text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
        disabled={range.currentPageIndex === 0}
        type="button"
        onClick={() => onPageIndexChange(range.currentPageIndex - 1)}
      >
        Previous
      </button>
      <span>
        Page {range.currentPageIndex + 1} of {range.pageCount}
      </span>
      <button
        className="rounded-full border border-[color:var(--vz-hair)] px-3 py-1.5 transition hover:text-[var(--vz-text-primary)] disabled:cursor-not-allowed disabled:opacity-50"
        disabled={range.currentPageIndex >= range.pageCount - 1}
        type="button"
        onClick={() => onPageIndexChange(range.currentPageIndex + 1)}
      >
        Next
      </button>
    </div>
  );
}
