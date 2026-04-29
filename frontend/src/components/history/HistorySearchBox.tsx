import { useEffect, useId, useState, type KeyboardEvent } from "react";

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
  const listboxId = useId();
  const [activeIndex, setActiveIndex] = useState(-1);
  const isOpen = Boolean(value.trim() && results.length > 0);
  const activeOptionId =
    isOpen && activeIndex >= 0
      ? `${listboxId}-option-${activeIndex}`
      : undefined;
  const grouped = results.reduce<
    Record<string, Array<{ result: HistorySearchResult; index: number }>>
  >((groups, result, index) => {
    groups[result.group] = [...(groups[result.group] ?? []), { result, index }];
    return groups;
  }, {});

  useEffect(() => {
    setActiveIndex(-1);
  }, [results, value]);

  function selectResult(result: HistorySearchResult) {
    setActiveIndex(-1);
    onSelect(result);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (!isOpen && event.key !== "Escape") return;

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActiveIndex((current) => (current + 1) % results.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setActiveIndex((current) =>
        current <= 0 ? results.length - 1 : current - 1,
      );
      return;
    }
    if (event.key === "Enter" && activeIndex >= 0) {
      event.preventDefault();
      selectResult(results[activeIndex]);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      setActiveIndex(-1);
      onChange("");
    }
  }

  return (
    <div className="relative">
      <Input
        role="combobox"
        aria-label="Search patterns"
        aria-expanded={isOpen}
        aria-controls={isOpen ? listboxId : undefined}
        aria-activedescendant={activeOptionId}
        aria-autocomplete="list"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      {isOpen ? (
        <div
          id={listboxId}
          role="listbox"
          className="absolute left-0 right-0 top-full z-20 mt-2 max-h-80 overflow-auto rounded-lg border border-white/10 bg-[#07101c] p-2 shadow-xl"
        >
          {Object.entries(grouped).map(([group, items]) => (
            <div key={group} className="py-1">
              <p className="px-2 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
                {group}
              </p>
              {items.map(({ result, index }) => (
                <button
                  id={`${listboxId}-option-${index}`}
                  key={result.id}
                  type="button"
                  role="option"
                  aria-selected={index === activeIndex}
                  className={`block w-full rounded-md px-2 py-2 text-left text-sm text-[#dce6f7] hover:bg-white/[0.06] ${
                    index === activeIndex ? "bg-white/[0.08]" : ""
                  }`}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => selectResult(result)}
                >
                  {result.label}
                </button>
              ))}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
