import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";

export function TenantSwitcher() {
  const user = useAuthStore((state) => state.user);

  if (!user?.isSuperadmin) {
    return null;
  }

  return (
    <div className="rounded-[1.15rem] border border-white/[0.06] bg-white/[0.03] px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8fa2be]">
        Tenant
      </p>
      <Badge className="mt-2 border-[#38507a] bg-[#10192a] text-[#d6e2f4]">
        Platform admin switcher
      </Badge>
    </div>
  );
}
