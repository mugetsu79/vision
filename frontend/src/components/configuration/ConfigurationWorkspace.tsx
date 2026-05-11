import { useMemo, useState } from "react";
import {
  Brain,
  Cpu,
  Database,
  Radio,
  ShieldCheck,
  Workflow,
} from "lucide-react";

import { ProfileBindingPanel } from "@/components/configuration/ProfileBindingPanel";
import { ProfileEditor } from "@/components/configuration/ProfileEditor";
import {
  CONFIGURATION_KINDS,
  labelForKind,
} from "@/components/configuration/configuration-copy";
import {
  useConfigurationCatalog,
  useConfigurationProfiles,
  useCreateConfigurationProfile,
  useDeleteConfigurationProfile,
  useTestConfigurationProfile,
  useUpdateConfigurationProfile,
  useUpsertConfigurationBinding,
  type OperatorConfigKind,
  type OperatorConfigProfile,
  type OperatorConfigProfileCreate,
} from "@/hooks/use-configuration";
import { Button } from "@/components/ui/button";
import { WorkspaceSurface, StatusToneBadge } from "@/components/layout/workspace-surfaces";

type NamedTarget = {
  id: string;
  name?: string;
  hostname?: string | null;
};

type ConfigurationWorkspaceProps = {
  cameras?: NamedTarget[];
  sites?: NamedTarget[];
  edgeNodes?: NamedTarget[];
};

const KIND_ICONS: Record<OperatorConfigKind, typeof Database> = {
  evidence_storage: Database,
  stream_delivery: Radio,
  runtime_selection: Cpu,
  privacy_policy: ShieldCheck,
  llm_provider: Brain,
  operations_mode: Workflow,
};

export function ConfigurationWorkspace({
  cameras = [],
  sites = [],
  edgeNodes = [],
}: ConfigurationWorkspaceProps) {
  const catalog = useConfigurationCatalog();
  const [activeKind, setActiveKind] = useState<OperatorConfigKind>("evidence_storage");
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);
  const profilesQuery = useConfigurationProfiles(activeKind);
  const createProfile = useCreateConfigurationProfile();
  const updateProfile = useUpdateConfigurationProfile();
  const deleteProfile = useDeleteConfigurationProfile();
  const testProfile = useTestConfigurationProfile();
  const upsertBinding = useUpsertConfigurationBinding();

  const profiles = useMemo(
    () => (profilesQuery.data ?? []).filter((profile) => profile.kind === activeKind),
    [activeKind, profilesQuery.data],
  );
  const selectedProfile =
    profiles.find((profile) => profile.id === selectedProfileId) ?? profiles[0] ?? null;
  const catalogLabels = new Map(
    (catalog.data?.kinds ?? []).map((item) => [item.kind, item.label]),
  );

  async function handleSave(payload: OperatorConfigProfileCreate) {
    if (selectedProfile && !isCreating) {
      await updateProfile.mutateAsync({
        profileId: selectedProfile.id,
        payload: {
          name: payload.name,
          slug: payload.slug,
          enabled: payload.enabled,
          is_default: payload.is_default,
          config: payload.config,
          secrets: payload.secrets,
        },
      });
      return;
    }
    await createProfile.mutateAsync(payload);
    setIsCreating(false);
  }

  async function handleTest(profile: OperatorConfigProfile) {
    const result = await testProfile.mutateAsync(profile.id);
    setTestResult(`${result.status}${result.message ? ` - ${result.message}` : ""}`);
  }

  return (
    <WorkspaceSurface
      data-testid="configuration-workspace"
      className="space-y-4 px-5 py-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--vz-text-muted)]">
            Control plane
          </p>
          <h2 className="mt-2 text-lg font-semibold text-[var(--vz-text-primary)]">
            Configuration
          </h2>
        </div>
        <Button
          type="button"
          onClick={() => {
            setIsCreating(true);
            setSelectedProfileId(null);
            setTestResult(null);
          }}
        >
          New profile
        </Button>
      </div>

      <div role="tablist" aria-label="Configuration categories" className="flex flex-wrap gap-2">
        {CONFIGURATION_KINDS.map((kind) => {
          const Icon = KIND_ICONS[kind];
          const selected = activeKind === kind;
          return (
            <button
              key={kind}
              type="button"
              role="tab"
              aria-selected={selected}
              className={[
                "inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold transition",
                selected
                  ? "border-[#8fd3ff] bg-[#123042] text-[#d8f2ff]"
                  : "border-white/10 bg-black/20 text-[#93a7c5] hover:text-[#f4f8ff]",
              ].join(" ")}
              onClick={() => {
                setActiveKind(kind);
                setSelectedProfileId(null);
                setIsCreating(false);
                setTestResult(null);
              }}
            >
              <Icon className="size-3.5" />
              {catalogLabels.get(kind) ?? labelForKind(kind)}
            </button>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(220px,0.8fr)_minmax(0,1.8fr)]">
        <div className="space-y-2">
          {profiles.length === 0 ? (
            <p className="rounded-[0.75rem] border border-white/10 px-3 py-3 text-sm text-[#93a7c5]">
              No profiles yet.
            </p>
          ) : (
            profiles.map((profile) => (
              <div
                key={profile.id}
                className="rounded-[0.75rem] border border-white/10 bg-black/15 p-3"
              >
                <button
                  type="button"
                  className="block w-full text-left"
                  onClick={() => {
                    setIsCreating(false);
                    setSelectedProfileId(profile.id);
                    setTestResult(null);
                  }}
                >
                  <span className="block text-sm font-semibold text-[#f4f8ff]">
                    {profile.name}
                  </span>
                  <span className="mt-1 block text-xs text-[#93a7c5]">
                    {profile.slug}
                  </span>
                </button>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {profile.is_default ? (
                    <StatusToneBadge tone="accent">Default</StatusToneBadge>
                  ) : (
                    <Button
                      type="button"
                      variant="ghost"
                      className="px-3 py-1.5 text-xs"
                      onClick={() => {
                        void updateProfile.mutateAsync({
                          profileId: profile.id,
                          payload: { is_default: true },
                        });
                      }}
                    >
                      Set default
                    </Button>
                  )}
                  {selectedProfile?.id === profile.id && !isCreating ? (
                    <StatusToneBadge
                      tone={profile.validation_status === "valid" ? "healthy" : "muted"}
                    >
                      {profile.validation_status === "unvalidated"
                        ? "not tested"
                        : profile.validation_status}
                    </StatusToneBadge>
                  ) : null}
                </div>
              </div>
            ))
          )}
        </div>

        <div className="space-y-4">
          <ProfileEditor
            kind={activeKind}
            selectedProfile={isCreating ? null : selectedProfile}
            onKindChange={(kind) => {
              setActiveKind(kind);
              setSelectedProfileId(null);
              setIsCreating(false);
              setTestResult(null);
            }}
            onSave={handleSave}
          />
          {selectedProfile && !isCreating ? (
            <div className="flex flex-wrap items-center gap-2">
              <Button type="button" onClick={() => void handleTest(selectedProfile)}>
                Test profile
              </Button>
              <Button
                type="button"
                variant="ghost"
                onClick={() => void deleteProfile.mutateAsync(selectedProfile.id)}
              >
                Delete
              </Button>
              {testResult ? (
                <StatusToneBadge tone={testResult.startsWith("valid") ? "healthy" : "danger"}>
                  {testResult}
                </StatusToneBadge>
              ) : null}
            </div>
          ) : null}
          <ProfileBindingPanel
            kind={activeKind}
            profiles={profiles}
            cameras={cameras.map((camera) => ({
              id: camera.id,
              label: camera.name ?? camera.id,
            }))}
            sites={sites.map((site) => ({ id: site.id, label: site.name ?? site.id }))}
            edgeNodes={edgeNodes.map((node) => ({
              id: node.id,
              label: node.hostname ?? node.id,
            }))}
            onBind={async (payload) => {
              await upsertBinding.mutateAsync(payload);
            }}
          />
        </div>
      </div>
    </WorkspaceSurface>
  );
}
