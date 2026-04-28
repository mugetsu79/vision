import { startTransition, type FormEvent, useMemo, useState } from "react";

import { apiClient, toApiError } from "@/lib/api";
import type { components } from "@/lib/api.generated";
import { productBrand } from "@/brand/product";
import { useAuthStore } from "@/stores/auth-store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";

type QueryResponse = components["schemas"]["QueryResponse"];

export type LiveQueryScope =
  | { scope: "all" }
  | { scope: "camera"; cameraId: string };

export function AgentInput({
  cameras,
  onResolved,
}: {
  cameras: Array<{ id: string; name: string }>;
  onResolved: (response: QueryResponse, scope: LiveQueryScope) => void;
}) {
  const brandName = productBrand.name;
  const user = useAuthStore((state) => state.user);
  const [prompt, setPrompt] = useState("");
  const [scopeValue, setScopeValue] = useState("all");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [resolution, setResolution] = useState<QueryResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const selectedScope = useMemo<LiveQueryScope>(() => {
    if (scopeValue === "all") {
      return { scope: "all" };
    }
    return { scope: "camera", cameraId: scopeValue };
  }, [scopeValue]);

  const selectedCameraIds = useMemo(() => {
    if (selectedScope.scope === "all") {
      return cameras.map((camera) => camera.id);
    }
    return [selectedScope.cameraId];
  }, [cameras, selectedScope]);

  const queryDisabled =
    user?.role === "viewer" ||
    prompt.trim().length === 0 ||
    cameras.length === 0 ||
    isSubmitting;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (queryDisabled) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const { data, error } = await apiClient.POST("/api/v1/query", {
        body: {
          prompt: prompt.trim(),
          camera_ids: selectedCameraIds,
        },
      });

      if (error || !data) {
        throw toApiError(error, "Failed to resolve the query.");
      }

      startTransition(() => {
        setResolution(data);
      });
      onResolved(data, selectedScope);
    } catch (error) {
      setErrorMessage(toApiError(error, "Failed to resolve the query.").message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="overflow-hidden rounded-[1.75rem] border border-white/10 bg-[linear-gradient(180deg,rgba(11,17,27,0.98),rgba(5,9,16,0.96))] shadow-[0_24px_64px_-46px_rgba(84,136,255,0.45)]">
      <div className="border-b border-white/8 px-5 py-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[#9fb7da]">
          Command query
        </p>
        <h3 className="mt-2 text-lg font-semibold text-[#f3f7ff]">
          Shape the live wall with natural language.
        </h3>
        <p className="mt-2 text-sm text-[#8ca2c5]">
          Resolve classes once, then let {brandName} trim the operator view while the backend
          applies the same intent to the running pipeline.
        </p>
      </div>

      <form className="space-y-4 px-5 py-5" onSubmit={(event) => void handleSubmit(event)}>
        <div className="grid gap-3 xl:grid-cols-[180px_minmax(0,1fr)_auto]">
          <label className="space-y-2 text-sm text-[#d9e5f7]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
              Query scope
            </span>
            <Select
              aria-label="Query scope"
              value={scopeValue}
              onChange={(event) => setScopeValue(event.target.value)}
            >
              <option value="all">All live cameras</option>
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name}
                </option>
              ))}
            </Select>
          </label>

          <label className="space-y-2 text-sm text-[#d9e5f7]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8ea8cf]">
              Query {brandName}
            </span>
            <Input
              aria-label={`Query ${brandName}`}
              placeholder="only show cars"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
            />
          </label>

          <div className="flex items-end">
            <Button className="w-full xl:w-auto" disabled={queryDisabled} type="submit">
              {isSubmitting ? "Resolving..." : "Apply query"}
            </Button>
          </div>
        </div>

        {user?.role === "viewer" ? (
          <p className="text-sm text-[#f0b7c1]">
            Query controls require operator role or higher.
          </p>
        ) : null}

        {errorMessage ? <p className="text-sm text-[#f0b7c1]">{errorMessage}</p> : null}

        {resolution ? (
          <div className="flex flex-wrap items-center gap-2 border-t border-white/8 pt-4">
            <Badge className="border-[#31538b] bg-[#101a2a] text-[#dce9ff]">
              {resolution.resolution_mode === "open_vocab"
                ? (resolution.resolved_vocabulary ?? []).join(", ")
                : resolution.resolved_classes.join(", ")}
            </Badge>
            <span className="text-sm text-[#b8c9e2]">
              {resolution.resolution_mode === "open_vocab"
                ? "Applied detector vocabulary"
                : "Resolved classes"}
            </span>
            <span className="text-sm text-[#8095b6]">
              {resolution.model}
            </span>
            <span className="text-sm text-[#8095b6]">{resolution.latency_ms} ms</span>
          </div>
        ) : null}
      </form>
    </section>
  );
}
