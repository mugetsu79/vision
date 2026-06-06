import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  filterSceneFocusItems,
  type SceneFocusItem,
} from "@/components/scenes/scene-focus";

interface SceneFocusPickerProps {
  defaultSummary: string;
  emptyLabel?: string;
  items: SceneFocusItem[];
  onClearSelection: () => void;
  onSearchChange: (value: string) => void;
  onToggleScene: (sceneId: string) => void;
  searchLabel: string;
  searchPlaceholder: string;
  searchValue: string;
  selectedSceneIds: Set<string>;
  testId?: string;
  title: string;
}

export function SceneFocusPicker({
  defaultSummary,
  emptyLabel = "No scenes match this search.",
  items,
  onClearSelection,
  onSearchChange,
  onToggleScene,
  searchLabel,
  searchPlaceholder,
  searchValue,
  selectedSceneIds,
  testId,
  title,
}: SceneFocusPickerProps) {
  const visibleItems = filterSceneFocusItems(items, searchValue);
  const hasSearch = searchValue.trim().length > 0;
  const statusLabel =
    selectedSceneIds.size > 0
      ? `${selectedSceneIds.size} selected`
      : hasSearch
        ? `${visibleItems.length} matching`
        : defaultSummary;

  return (
    <section
      data-testid={testId}
      className="rounded-[0.5rem] border border-slate-800 bg-slate-950/45 p-4 shadow-inner shadow-black/20"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Scene focus</p>
          <h3 className="mt-1 text-xl font-semibold text-white">{title}</h3>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <span className="rounded-full border border-sky-500/35 bg-sky-500/10 px-3 py-1 text-sm font-semibold text-sky-100">
            {statusLabel}
          </span>
          {selectedSceneIds.size > 0 ? (
            <Button variant="ghost" type="button" onClick={onClearSelection}>
              Clear
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-4">
        <Input
          aria-label={searchLabel}
          value={searchValue}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          className="max-w-xl border-slate-700 bg-slate-950/80 text-white placeholder:text-slate-500"
        />
      </div>

      <div className="mt-4 flex gap-3 overflow-x-auto pb-1">
        {visibleItems.length === 0 ? (
          <div className="w-full rounded-[0.5rem] border border-dashed border-slate-700 bg-slate-950/55 px-4 py-5 text-sm text-slate-400">
            {emptyLabel}
          </div>
        ) : (
          visibleItems.map((item) => {
            const checked = selectedSceneIds.has(item.id);
            return (
              <label
                key={item.id}
                className={cn(
                  "flex min-w-[14rem] cursor-pointer items-start gap-3 rounded-[0.5rem] border px-3 py-3 transition",
                  checked
                    ? "border-sky-400 bg-sky-500/15 shadow-[0_0_0_1px_rgba(56,189,248,0.25)]"
                    : "border-slate-800 bg-slate-900/60 hover:border-slate-600",
                )}
              >
                <input
                  aria-label={item.name}
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggleScene(item.id)}
                  className="mt-1 h-4 w-4 rounded border-slate-500 bg-slate-950 text-sky-500 focus:ring-sky-400"
                />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-semibold text-slate-100">{item.name}</span>
                  <span className="mt-1 block truncate text-xs uppercase tracking-[0.2em] text-slate-500">
                    {item.siteName ?? "Unknown site"}
                  </span>
                </span>
              </label>
            );
          })
        )}
      </div>
    </section>
  );
}
