import { Input } from "@/components/ui/input";
import type { HistorySearchResult } from "@/lib/history-search";

export function HistorySearchBox({
  value,
  results,
  onChange,
  onSelect,
}: {
  value: string;
  results: HistorySearchResult[];
  onChange: (value: string) => void;
  onSelect: (result: HistorySearchResult) => void;
}) {
  const grouped = results.reduce<Record<string, HistorySearchResult[]>>((groups, result) => {
    groups[result.group] = [...(groups[result.group] ?? []), result];
    return groups;
  }, {});

  return (
    <div className="relative">
      <Input
        aria-label="Search history"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      {value.trim() && results.length > 0 ? (
        <div className="absolute left-0 right-0 top-full z-20 mt-2 max-h-80 overflow-auto rounded-lg border border-white/10 bg-[#07101c] p-2 shadow-xl">
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="py-1">
              <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                {group}
              </p>
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="block w-full rounded-md px-2 py-2 text-left text-sm text-[#dce6f7] hover:bg-white/[0.06]"
                  onClick={() => onSelect(item)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
