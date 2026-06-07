import { useEffect, useState, type FormEvent } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";

import {
  asRecord,
  buildLinkPolicy,
  laneLabel,
  linkPriorityLanes,
  normalizeLinkPolicy,
  numberValue,
  type LinkPolicyFormState,
  type LinkPriorityLane,
} from "@/components/link/types";
import { WorkspaceSurface } from "@/components/layout/workspace-surfaces";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUpdateLinkBudget, useUpdateLinkPolicies } from "@/hooks/use-link";

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
  const updateBudget = useUpdateLinkBudget({ siteId });
  const updatePolicies = useUpdateLinkPolicies({ siteId });
  const [monthlyBytes, setMonthlyBytes] = useState("0");
  const [bulkDailyBytes, setBulkDailyBytes] = useState("0");
  const [policyForm, setPolicyForm] = useState<LinkPolicyFormState>(() =>
    normalizeLinkPolicy(policies),
  );

  useEffect(() => {
    setMonthlyBytes(String(numberValue(budgetRecord.monthly_bytes)));
    setBulkDailyBytes(String(numberValue(budgetRecord.bulk_daily_bytes)));
  }, [budgetRecord.bulk_daily_bytes, budgetRecord.monthly_bytes]);

  useEffect(() => {
    setPolicyForm(normalizeLinkPolicy(policies));
  }, [policies]);

  async function handleBudgetSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await updateBudget.mutateAsync({
      monthly_bytes: numericValue(monthlyBytes),
      bulk_daily_bytes: numericValue(bulkDailyBytes),
    });
  }

  async function handlePolicySubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await updatePolicies.mutateAsync({ policy: buildLinkPolicy(policyForm) });
  }

  function moveLane(lane: LinkPriorityLane, direction: -1 | 1) {
    setPolicyForm((current) => {
      const lanes = [...current.priorityOrder];
      const index = lanes.indexOf(lane);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= lanes.length) {
        return current;
      }
      const nextLane = lanes[nextIndex];
      lanes[nextIndex] = lane;
      lanes[index] = nextLane;
      return { ...current, priorityOrder: lanes };
    });
  }

  function toggleLaneList(
    field: "degradedPauses" | "darkAllows",
    lane: LinkPriorityLane,
  ) {
    setPolicyForm((current) => {
      const exists = current[field].includes(lane);
      const lanes = exists
        ? current[field].filter((candidate) => candidate !== lane)
        : [...current[field], lane];
      return { ...current, [field]: lanes };
    });
  }

  function updatePolicyFlag(
    field:
      | "pauseBulkWhenDailyBudgetExhausted"
      | "avoidMeteredForBulkWhenBudgetExhausted",
    value: boolean,
  ) {
    setPolicyForm((current) => ({ ...current, [field]: value }));
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
      <form className="mt-5 space-y-4" onSubmit={(event) => void handlePolicySubmit(event)}>
        <section className="space-y-2">
          <h3 className="font-[family-name:var(--vz-font-display)] text-sm font-semibold text-[var(--vz-text-primary)]">
            Lane priority
          </h3>
          <div className="grid gap-2">
            {policyForm.priorityOrder.map((lane, index) => (
              <div
                key={lane}
                className="flex items-center justify-between gap-3 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] px-3 py-2"
              >
                <span className="text-sm text-[var(--vz-text-secondary)]">
                  {index + 1}. {laneLabel(lane)}
                </span>
                <span className="flex gap-2">
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={index === 0}
                    aria-label={`Move ${lane} up`}
                    onClick={() => moveLane(lane, -1)}
                  >
                    <ArrowUp className="size-4" aria-hidden="true" />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={index === policyForm.priorityOrder.length - 1}
                    aria-label={`Move ${lane} down`}
                    onClick={() => moveLane(lane, 1)}
                  >
                    <ArrowDown className="size-4" aria-hidden="true" />
                  </Button>
                </span>
              </div>
            ))}
          </div>
        </section>
        <div className="grid gap-3 md:grid-cols-2">
          <fieldset className="space-y-2 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] p-3">
            <legend className="px-1 text-sm font-medium text-[var(--vz-text-primary)]">
              Degraded path behavior
            </legend>
            {linkPriorityLanes.map((lane) => (
              <PolicyCheckbox
                key={lane}
                checked={policyForm.degradedPauses.includes(lane)}
                label={`Pause ${laneLabel(lane)} when degraded`}
                onChange={() => toggleLaneList("degradedPauses", lane)}
              />
            ))}
          </fieldset>
          <fieldset className="space-y-2 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] p-3">
            <legend className="px-1 text-sm font-medium text-[var(--vz-text-primary)]">
              Dark path behavior
            </legend>
            {linkPriorityLanes.map((lane) => (
              <PolicyCheckbox
                key={lane}
                checked={policyForm.darkAllows.includes(lane)}
                label={`Allow ${laneLabel(lane)} when dark`}
                onChange={() => toggleLaneList("darkAllows", lane)}
              />
            ))}
          </fieldset>
        </div>
        <fieldset className="space-y-2 rounded-[var(--vz-r-md)] border border-[color:var(--vz-hair)] bg-white/[0.025] p-3">
          <legend className="px-1 text-sm font-medium text-[var(--vz-text-primary)]">
            Budget behavior
          </legend>
          <PolicyCheckbox
            checked={policyForm.pauseBulkWhenDailyBudgetExhausted}
            label="Pause bulk when daily budget is exhausted"
            onChange={() =>
              updatePolicyFlag(
                "pauseBulkWhenDailyBudgetExhausted",
                !policyForm.pauseBulkWhenDailyBudgetExhausted,
              )
            }
          />
          <PolicyCheckbox
            checked={policyForm.avoidMeteredForBulkWhenBudgetExhausted}
            label="Avoid metered paths for bulk when budget is exhausted"
            onChange={() =>
              updatePolicyFlag(
                "avoidMeteredForBulkWhenBudgetExhausted",
                !policyForm.avoidMeteredForBulkWhenBudgetExhausted,
              )
            }
          />
        </fieldset>
        <Button type="submit" disabled={!siteId || updatePolicies.isPending}>
          {updatePolicies.isPending ? "Saving..." : "Save policy"}
        </Button>
      </form>
    </WorkspaceSurface>
  );
}

function PolicyCheckbox({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: () => void;
}) {
  return (
    <label className="flex items-center gap-3 text-sm text-[var(--vz-text-secondary)]">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span>{label}</span>
    </label>
  );
}

function numericValue(value: string) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}
