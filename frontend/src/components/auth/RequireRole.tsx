import type { PropsWithChildren } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ArgusRole } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth-store";

const roleRank: Record<ArgusRole, number> = {
  viewer: 10,
  operator: 20,
  admin: 30,
  superadmin: 40,
};

export function RequireRole({
  role,
  children,
}: PropsWithChildren<{ role: ArgusRole }>) {
  const user = useAuthStore((state) => state.user);

  if (!user || roleRank[user.role] < roleRank[role]) {
    return (
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Access denied</CardTitle>
          <CardDescription>You do not have access to this page.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-600">
          Ask an administrator for the required role if this is unexpected.
        </CardContent>
      </Card>
    );
  }

  return <>{children}</>;
}
