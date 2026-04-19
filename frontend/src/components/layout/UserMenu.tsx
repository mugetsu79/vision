import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

export function UserMenu() {
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);

  return (
    <div className="flex items-center gap-3 rounded-full border border-white/10 bg-[rgba(9,15,24,0.76)] px-3 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.03)] backdrop-blur-xl">
      <div className="text-right">
        <p className="text-sm font-medium text-[#eef4ff]">{user?.email ?? "Unknown user"}</p>
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#8ea4c7]">
          {user?.role ?? "anonymous"}
        </p>
      </div>
      <Button
        className="bg-[#121b29] px-3 py-2 text-[#eef4ff] shadow-none ring-1 ring-white/10 hover:bg-[#172235]"
        onClick={() => void signOut()}
      >
        Logout
      </Button>
    </div>
  );
}
