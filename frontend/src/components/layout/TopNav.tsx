import { NavLink } from "react-router-dom";

import { cn } from "@/lib/utils";

const primaryNav = [
  { label: "Dashboard", to: "/dashboard" },
  { label: "Live", to: "/live" },
  { label: "History", to: "/history" },
  { label: "Incidents", to: "/incidents" },
  { label: "Settings", to: "/settings" },
] as const;

export function TopNav() {
  return (
    <nav className="flex flex-wrap items-center gap-2" aria-label="Primary">
      {primaryNav.map((item) => (
        <NavLink
          key={item.label}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "rounded-full px-4 py-2 text-sm font-medium transition duration-200",
              isActive
                ? "bg-[linear-gradient(135deg,rgba(47,124,255,0.95),rgba(128,92,255,0.95))] text-white shadow-[0_14px_32px_-18px_rgba(84,109,255,0.95)]"
                : "border border-white/10 bg-white/[0.04] text-[#a8bbd7] hover:border-[#37507a] hover:bg-[#0f1826] hover:text-[#eef4ff]",
            )
          }
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
