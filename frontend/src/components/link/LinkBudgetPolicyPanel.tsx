import { useEffect, useState, type FormEvent } from "react";

import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUpdateLinkBudget, useUpdateLinkPolicies } from "@/hooks/use-link";
import { asRecord, numberValue } from "@/components/link/types";

type LinkBudgetPolicyPanelProps = {
  siteId?: string | null;
  budget: unknown;
  policies: unknown;
};

export function LinkBudgetPolicyPanel({
  siteId,
  budget,
  policies,
}: LinkBudgetPolicyPanelProps) {
  const budgetRecord = asRecord(budget);
  const policyRecord = asRecord(policies);
  const updateBudget = useUpdateLinkBudget({ siteId });
  const updatePolicies = useUpdateLinkPolicies({ siteId });
  const [monthlyBytes, setMonthlyBytes] = useState("0");
  const [bulkDailyBytes, setBulkDailyBytes] = useState("0");
  const [policyJson, setPolicyJson] = useState("{}");
  const [policyError, setPolicyError] = useState<string | null>(null);

  useEffect(() => {
    setMonthlyBytes(String(numberValue(budgetRecord.monthly_bytes)));
    setBulkDailyBytes(String(numberValue(budgetRecord.bulk_daily_bytes)));
  }, [budgetRecord.bulk_daily_bytes, budgetRecord.monthly_bytes]);

  useEffect(() => {
    setPolicyJson(JSON.stringify(policyRecord.policy ?? policyRecord, null, 2));
    setPolicyError(null);
  }, [policyRecord, policyRecord.policy]);

  async function handleBudgetSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await updateBudget.mutateAsync({
      monthly_bytes: numericValue(monthlyBytes),
      bulk_daily_bytes: numericValue(bulkDailyBytes),
    });
  }

  async function handlePolicySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPolicyError(null);

    try {
      const parsed = JSON.parse(policyJson) as unknown;
      if (!isJsonObject(parsed)) {
        setPolicyError("Policy must be valid JSON.");
        return;
      }
      await updatePolicies.mutateAsync({ policy: parsed });
    } catch {
      setPolicyError("Policy must be valid JSON.");
    }
  }

  return (
    <WorkspaceSurface className="p-5">
      <h2 className="font-[family-name:var(--vz-font-display)] text-xl font-semibold text-[var(--vz-text-primary)]">
        Budget and policy
      </h2>
      <form className="mt-4 space-y-4" onSubmit={(event) => void handleBudgetSubmit(event)}>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
            <span>Monthly bytes</span>
            <Input
              aria-label="Monthly bytes"
              type="number"
              min="0"
              value={monthlyBytes}
              onChange={(event) => setMonthlyBytes(event.target.value)}
            />
          </label>
          <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
            <span>Bulk daily bytes</span>
            <Input
              aria-label="Bulk daily bytes"
              type="number"
              min="0"
              value={bulkDailyBytes}
              onChange={(event) => setBulkDailyBytes(event.target.value)}
            />
          </label>
        </div>
        <Button type="submit" disabled={!siteId || updateBudget.isPending}>
          {updateBudget.isPending ? "Saving..." : "Save budget"}
        </Button>
      </form>
      <form className="mt-5 space-y-3" onSubmit={(event) => void handlePolicySubmit(event)}>
        <label className="grid gap-2 text-sm text-[var(--vz-text-secondary)]">
          <span>Policy JSON</span>
          <textarea
            aria-label="Policy JSON"
            className="min-h-40 w-full rounded-[0.85rem] border border-[color:var(--argus-border)] bg-[color:var(--argus-surface)] px-4 py-3 font-mono text-xs text-[var(--argus-text)] outline-none transition duration-200 focus:border-[color:var(--argus-border-highlight)] focus:shadow-[0_0_0_4px_var(--argus-accent-soft)]"
            value={policyJson}
            onChange={(event) => setPolicyJson(event.target.value)}
          />
        </label>
        {policyError ? (
          <p role="alert" className="text-sm font-medium text-[#ff9ca6]">
            {policyError}
          </p>
        ) : null}
        <Button type="submit" disabled={!siteId || updatePolicies.isPending}>
          {updatePolicies.isPending ? "Saving..." : "Save policy"}
        </Button>
      </form>
    </WorkspaceSurface>
  );
}

function numericValue(value: string) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function isJsonObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
