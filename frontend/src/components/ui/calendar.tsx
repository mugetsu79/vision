import { ChevronLeft, ChevronRight } from "lucide-react";
import { DayPicker, type DayPickerProps } from "react-day-picker";

import { cn } from "@/lib/utils";

export function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: DayPickerProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        months: "flex flex-col gap-6 sm:flex-row sm:gap-8",
        month: "space-y-4",
        month_caption: "flex items-center justify-center gap-3 pt-1",
        caption_label: "text-sm font-semibold tracking-[0.04em] text-[#eef4ff]",
        nav: "flex items-center gap-2",
        button_previous:
          "inline-flex size-9 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[#d7e4ff] transition hover:border-[#44699e] hover:bg-[#111c2d]",
        button_next:
          "inline-flex size-9 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[#d7e4ff] transition hover:border-[#44699e] hover:bg-[#111c2d]",
        month_grid: "w-full border-collapse",
        weekdays: "flex",
        weekday:
          "w-10 text-center text-[11px] font-semibold uppercase tracking-[0.22em] text-[#6f84a6]",
        week: "mt-2 flex w-full",
        day: "size-10 p-0 text-center text-sm",
        day_button:
          "size-10 rounded-full border border-transparent text-sm text-[#dce7f7] transition hover:border-[#365683] hover:bg-[#0f1725] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5a95ff]/50",
        outside: "text-[#4e6284]/40",
        disabled: "opacity-30",
        hidden: "invisible",
        today:
          "rounded-full border border-[#31538b] bg-[#101b2d] text-[#eef4ff] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.03)]",
        selected:
          "rounded-full bg-[linear-gradient(135deg,#2f7cff_0%,#805cff_100%)] text-white shadow-[0_14px_28px_-18px_rgba(84,109,255,0.95)]",
        range_start:
          "rounded-full bg-[linear-gradient(135deg,#2f7cff_0%,#805cff_100%)] text-white shadow-[0_14px_28px_-18px_rgba(84,109,255,0.95)]",
        range_end:
          "rounded-full bg-[linear-gradient(135deg,#2f7cff_0%,#805cff_100%)] text-white shadow-[0_14px_28px_-18px_rgba(84,109,255,0.95)]",
        range_middle: "rounded-none bg-[#15253e] text-[#dbe7ff]",
        ...classNames,
      }}
      components={{
        Chevron: ({ className: iconClassName, orientation, ...iconProps }) =>
          orientation === "left" ? (
            <ChevronLeft className={cn("size-4", iconClassName)} {...iconProps} />
          ) : (
            <ChevronRight className={cn("size-4", iconClassName)} {...iconProps} />
          ),
      }}
      {...props}
    />
  );
}
