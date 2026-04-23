import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

export function UserMenu() {
  const user = useAuthStore((state) => state.user);
  const signOut = useAuthStore((state) => state.signOut);

  return (
    <div className="rounded-[1.15rem] border border-white/[0.06] bg-[linear-gradient(180deg,rgba(9,14,21,0.96),rgba(12,17,25,0.92))] px-3 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8fa2be]">
        Session
      </p>
      <div className="mt-2 space-y-1">
        <p className="text-sm font-medium text-[#eef4ff]">{user?.email ?? "Unknown user"}</p>
        <p className="text-[11px] uppercase tracking-[0.2em] text-[#8ea4c7]">
          {user?.role ?? "anonymous"}
        </p>
      </div>
      <Button
        className="mt-3 h-9 w-full rounded-[0.95rem] border border-white/10 bg-white/[0.04] px-3 text-sm text-[#eef4ff] shadow-none hover:border-[#35598d] hover:bg-white/[0.07]"
        onClick={() => void signOut()}
      >
        Sign out
      </Button>
    </div>
  );
}
