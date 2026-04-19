import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";

export function TenantSwitcher() {
  const user = useAuthStore((state) => state.user);

  if (!user?.isSuperadmin) {
    return null;
  }

  return (
    <Badge className="border-[#38507a] bg-[#10192a] text-[#d6e2f4]">
      Tenant switcher reserved for platform-admin
    </Badge>
  );
}
